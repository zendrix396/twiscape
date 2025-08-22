import json
import gzip
import time
from seleniumwire import webdriver
from selenium.webdriver.firefox.options import Options
import config
from utils import build_search_url, process_raw_data
from database import TweetDatabase
import os

class TwitterScraper:
    def __init__(self, job_config, db_queue, worker_id):
        self.job_config = job_config
        self.db_queue = db_queue
        self.worker_id = worker_id
        
        self.driver = None
        self.processed_urls = set()
        self.total_tweets_collected = 0
        self.consecutive_empty_scrolls = 0
        
        # Each worker gets its own temporary raw data file to avoid race conditions
        self.raw_data_filename = f"data/raw_data_worker_{self.worker_id}.json"

    def _setup_driver(self):
        """Sets up the Selenium WebDriver."""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        self.driver = webdriver.Firefox(options=options)

    def _load_cookies(self):
        """Loads cookies from the cookies file."""
        try:
            with open(config.COOKIES_FILENAME, "r") as f:
                cookies = json.load(f)
            for cookie in cookies:
                cookie.pop('sameSite', None)
                self.driver.add_cookie(cookie)
            print("🍪 Cookies loaded successfully.")
            return True
        except FileNotFoundError:
            print(f"❌ Error: '{config.COOKIES_FILENAME}' not found. Please run auth.py to log in first.")
            return False

    def _capture_initial_data(self):
        """Captures the initial data."""
        print("⏳ Waiting for initial data to load...")
        wait_start_time = time.time()
        while time.time() - wait_start_time < 30:
            for request in reversed(self.driver.requests):
                if request.response and "SearchTimeline" in request.url and request.url not in self.processed_urls:
                    print(f"📡 Initial data loaded successfully!")
                    self._process_request(request)
                    return True
        print("❌ Failed to capture initial data within 30 seconds.")
        return False

    def _process_request(self, request):
        """Processes a Selenium request and extracts tweet data."""
        body = gzip.decompress(request.response.body) if request.response.headers.get("Content-Encoding") == "gzip" else request.response.body
        
        try:
            body_text = body.decode("utf-8")
            data = json.loads(body_text)
            with open(self.raw_data_filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Process the raw data and put the cleaned tweets onto the queue
            new_tweets = process_raw_data(self.raw_data_filename)
            if new_tweets:
                self.db_queue.put(new_tweets)
                self.total_tweets_collected += len(new_tweets)
                print(f"Worker {self.worker_id}: 📦 Queued {len(new_tweets)} new tweets for database.")
            
            self.processed_urls.add(request.url)
        except json.JSONDecodeError:
            print(f"Worker {self.worker_id}: ⚠️ Could not decode JSON from response. Saving failed response for debugging.")
            debug_filename = f"data/failed_response_worker_{self.worker_id}.html"
            with open(debug_filename, "w", encoding="utf-8") as f:
                f.write(body_text)
            print(f"Worker {self.worker_id}: 👉 Saved unexpected response to '{debug_filename}'")
        except Exception as e:
            print(f"Worker {self.worker_id}: ❌ Error processing request: {e}")


    def _handle_infinite_scroll(self):
        """Handles the infinite scroll and data capturing."""
        print(f"\nWorker {self.worker_id}: 🔄 Starting infinite scroll for query: '{self.job_config['search_query']}'")
        scroll_count = 0
        
        max_tweets = self.job_config.get("max_tweets", float('inf'))

        while True:
            if self.total_tweets_collected >= max_tweets:
                print(f"Worker {self.worker_id}: 🏁 Reached tweet limit of {max_tweets}. Stopping.")
                break
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                scroll_count += 1
                print(f"\nWorker {self.worker_id}: 📜 Scrolled down ({scroll_count}). Waiting for new data...")
                time.sleep(2)
                new_data_found = False
                for request in reversed(self.driver.requests):
                    if "SearchTimeline" in request.url and request.url not in self.processed_urls:
                        print(f"Worker {self.worker_id}: 🆕 New data loaded successfully!")
                        self._process_request(request)
                        new_data_found = True
                        self.consecutive_empty_scrolls = 0
                        break
                if not new_data_found:
                    print(f"Worker {self.worker_id}: ⏳ No new data found on this scroll.")
                    self.consecutive_empty_scrolls += 1
                    if self.consecutive_empty_scrolls >= config.MAX_EMPTY_SCROLLS:
                        print(f"Worker {self.worker_id}: 🤷‍♀️ No new data after {config.MAX_EMPTY_SCROLLS} consecutive empty scrolls. Assuming end of results.")
                        break

            except KeyboardInterrupt:
                print(f"\nWorker {self.worker_id}: 🛑 User interruption detected. Stopping.")
                break
            except Exception as e:
                print(f"Worker {self.worker_id}: ❌ An error occurred during the scroll loop: {e}")
                # We can add a `break` here if we want the worker to stop on any error
                break

    def _print_database_stats(self):
        """Prints current database statistics."""
        stats = self.db.get_stats()
        print(f"\n📊 Database Statistics:")
        print(f"   Total tweets: {stats.get('total_tweets', 0)}")
        print(f"   Unique creators: {stats.get('unique_creators', 0)}")
        print(f"   First scraped: {stats.get('first_scraped', 'N/A')}")
        print(f"   Last scraped: {stats.get('last_scraped', 'N/A')}")

    def scrape(self):
        """Main method to run the scraper for a single job."""
        search_url = build_search_url(self.job_config)
        self._setup_driver()
        
        print(f"Worker {self.worker_id}: 🚀 Starting job for query: '{self.job_config['search_query']}'")

        try:
            self.driver.get("https://x.com/robots.txt")
            if not self._load_cookies():
                return

            print(f"Worker {self.worker_id}: 🔍 Navigating to search URL...")
            self.driver.get(search_url)

            if self._capture_initial_data():
                self._handle_infinite_scroll()

        except Exception as e:
            print(f"Worker {self.worker_id}: ❌ A fatal error occurred: {e}")
        finally:
            if self.driver:
                print(f"Worker {self.worker_id}: 🔚 Closing browser.")
                self.driver.quit()
            
            # Clean up the temporary raw data file
            if os.path.exists(self.raw_data_filename):
                os.remove(self.raw_data_filename)
                
            print(f"Worker {self.worker_id}: ✨ Job finished. Total tweets collected: {self.total_tweets_collected}")

if __name__ == "__main__":
    scraper = TwitterScraper()
    scraper.scrape()
