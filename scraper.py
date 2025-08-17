import json
import gzip
import time
from seleniumwire import webdriver
from selenium.webdriver.firefox.options import Options
import config
from utils import build_search_url, process_and_append_tweets

class TwitterScraper:
    def __init__(self):
        self.driver = None
        self.processed_urls = set()
        self.total_tweets_collected = 0
        self.consecutive_empty_scrolls = 0

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
        data = json.loads(body.decode("utf-8"))
        with open(config.RAW_DATA_FILENAME, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"📝 Saved raw data to '{config.RAW_DATA_FILENAME}'")
        new_tweets = process_and_append_tweets(config.RAW_DATA_FILENAME, config.CLEANED_DATA_FILENAME)
        self.total_tweets_collected += new_tweets
        self.processed_urls.add(request.url)

    def _handle_infinite_scroll(self):
        """Handles the infinite scroll and data capturing."""
        print("\n🔄 Starting infinite scroll monitoring... Press Ctrl+C to stop.")
        scroll_count = 0
        while True:
            if config.MAX_TWEETS and self.total_tweets_collected >= config.MAX_TWEETS:
                print(f"🏁 Reached tweet limit of {config.MAX_TWEETS}. Stopping script.")
                break
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                scroll_count += 1
                print(f"\n📜 Scrolled down ({scroll_count}). Waiting for new data...")

                new_data_found = False
                for request in reversed(self.driver.requests):
                    if "SearchTimeline" in request.url and request.url not in self.processed_urls:
                        print(f"🆕 New data loaded successfully!")
                        self._process_request(request)
                        new_data_found = True
                        self.consecutive_empty_scrolls = 0
                        break
                if not new_data_found:
                    print("⏳ No new data found on this scroll.")
                    self.consecutive_empty_scrolls += 1
                    if self.consecutive_empty_scrolls >= config.MAX_EMPTY_SCROLLS:
                        print(f"🤷‍♀️ No new data after {config.MAX_EMPTY_SCROLLS} consecutive empty scrolls. Assuming end of results.")
                        break

            except KeyboardInterrupt:
                print("\n🛑 User interruption detected. Stopping script.")
                break
            except Exception as e:
                print(f"❌ An error occurred during the scroll loop: {e}")

    def scrape(self):
        """Main method to run the scraper."""
        search_url = build_search_url()
        self._setup_driver()

        try:
            self.driver.get("https://x.com/robots.txt")
            if not self._load_cookies():
                return

            print(f"🔍 Searching for the query...")
            self.driver.get(search_url)

            if self._capture_initial_data():
                self._handle_infinite_scroll()

        except Exception as e:
            print(f"❌ A fatal error occurred: {e}")
        finally:
            if self.driver:
                print("🔚 Closing browser.")
                self.driver.quit()

if __name__ == "__main__":
    scraper = TwitterScraper()
    scraper.scrape()
