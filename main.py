import argparse
import getpass
from datetime import datetime
from auth import TwitterAuth
from scraper import TwitterScraper
from database import TweetDatabase
import config
import time
from multiprocessing import Process, Queue

def scraper_worker(job_config, db_queue, worker_id):
    """
    Function to be executed by each scraper process.
    Instantiates and runs the TwitterScraper for a given job.
    """
    print(f"[Worker {worker_id}] Starting...")
    try:
        scraper = TwitterScraper(job_config, db_queue, worker_id)
        scraper.scrape()
    except Exception as e:
        print(f"[Worker {worker_id}] Fatal error in worker process: {e}")

def db_writer_process(db_queue):
    """
    A dedicated process to handle all database writes.
    It listens on a queue for batches of tweets and inserts them.
    This avoids SQLite concurrency issues.
    """
    print("[DB Writer] Process started.")
    db = TweetDatabase()
    
    # Get the starting serial number once
    current_sno = db.get_latest_serial_no()
    
    while True:
        try:
            tweet_batch = db_queue.get()
            
            # Sentinel value to signal termination
            if tweet_batch is None:
                print("[DB Writer] Sentinel received. Shutting down.")
                break
            
            # Assign serial numbers sequentially
            for tweet in tweet_batch:
                current_sno += 1
                tweet['serial_no'] = current_sno
            
            inserted_count = db.insert_tweets_batch(tweet_batch)
            print(f"[DB Writer] ✅ Successfully inserted a batch of {inserted_count} tweets.")

        except Exception as e:
            print(f"[DB Writer] ❌ Error writing to database: {e}")

    print("[DB Writer] Process finished.")


def handle_login():
    """Handle the login action."""
    username = input("Enter your X.com username or email: ")
    password = getpass.getpass("Enter your X.com password: ")
    if username and password:
        auth = TwitterAuth(username, password)
        auth.login()
    else:
        print("❌ Username and password cannot be empty. Aborting.")

def handle_parallel_scrape():
    """
    Handles the entire parallel scraping process.
    - Sets up the database writer process and the queue.
    - Creates and manages a pool of scraper worker processes.
    """
    db_queue = Queue()

    # Start the dedicated database writer process
    writer_process = Process(target=db_writer_process, args=(db_queue,))
    writer_process.start()

    # Create and start a scraper process for each job defined in config
    scraper_processes = []
    for i, job_config in enumerate(config.SCRAPE_JOBS):
        worker_id = i + 1
        process = Process(target=scraper_worker, args=(job_config, db_queue, worker_id))
        scraper_processes.append(process)
        process.start()
        # Optional: stagger the start of browsers to avoid resource spikes
        time.sleep(5) 

    # Wait for all scraper processes to complete
    for process in scraper_processes:
        process.join()

    # All scrapers are done, send sentinel to the writer and wait for it to finish
    db_queue.put(None)
    writer_process.join()

    print("\n\n🎉 All scraping jobs completed.")
    handle_stats() # Show final stats

def handle_stats():
    """Handle displaying database statistics."""
    db = TweetDatabase()
    stats = db.get_stats()
    
    print(f"\n📊 Database Statistics:")
    print(f"   Database file: {config.DATABASE_FILENAME}")
    print(f"   Total tweets: {stats.get('total_tweets', 0)}")
    print(f"   Unique creators: {stats.get('unique_creators', 0)}")
    print(f"   First scraped: {stats.get('first_scraped', 'N/A')}")
    print(f"   Last scraped: {stats.get('last_scraped', 'N/A')}")

def handle_export(args):
    """Handle exporting tweets to JSON."""
    db = TweetDatabase()
    output_file = args.output or f"exported_tweets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    if db.export_to_json(output_file):
        print(f"✅ Successfully exported tweets to '{output_file}'")
    else:
        print("❌ Failed to export tweets")

def main():
    parser = argparse.ArgumentParser(description="Twitter Scraper Tool")
    parser.add_argument('action', choices=['login', 'scrape', 'stats', 'export'], 
                       help="Action to perform: 'login' to save cookies, 'scrape' to start parallel scraping, 'stats' to show database statistics, 'export' to export tweets to JSON.")
    
    # Optional arguments for export command (scrape args are now in config)
    parser.add_argument('--output', '-o', help='Output filename for export (optional)')
    
    args = parser.parse_args()

    if args.action == 'login':
        handle_login()
    elif args.action == 'scrape':
        handle_parallel_scrape()
    elif args.action == 'stats':
        handle_stats()
    elif args.action == 'export':
        handle_export(args)

if __name__ == "__main__":
    # Ensure the main block is protected for multiprocessing
    main()
