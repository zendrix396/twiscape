import argparse
import getpass
from datetime import datetime
from auth import TwitterAuth
from scraper import TwitterScraper
from database import TweetDatabase
import config

def handle_login():
    """Handle the login action."""
    username = input("Enter your X.com username or email: ")
    password = getpass.getpass("Enter your X.com password: ")
    if username and password:
        auth = TwitterAuth(username, password)
        auth.login()
    else:
        print("❌ Username and password cannot be empty. Aborting.")

def handle_scrape(args):
    """Handle the scrape action with parameters."""
    # Update config based on arguments
    if args.search_string:
        config.SEARCH_QUERY = args.search_string
    
    if args.by:
        config.FROM_ACCOUNTS = args.by
    
    if args.timeline:
        # Parse timeline format: start_date to end_date
        timeline_parts = args.timeline.split(' to ')
        if len(timeline_parts) == 2:
            config.SINCE_DATE = timeline_parts[0].strip()
            config.UNTIL_DATE = timeline_parts[1].strip()
        else:
            print("❌ Timeline format should be: 'YYYY-MM-DD to YYYY-MM-DD'")
            return
    
    # Initialize and run scraper
    scraper = TwitterScraper()
    scraper.scrape()

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
                       help="Action to perform: 'login' to save cookies, 'scrape' to start scraping, 'stats' to show database statistics, 'export' to export tweets to JSON.")
    
    # Optional arguments for scrape command
    parser.add_argument('search_string', nargs='?', help='Search string for scraping (optional)')
    parser.add_argument('--by', nargs='+', help='Array of author usernames to search by')
    parser.add_argument('--timeline', help='Timeline in format "start_date to end_date" (e.g., "2024-01-01 to 2024-12-31")')
    parser.add_argument('--output', '-o', help='Output filename for export (optional)')
    
    args = parser.parse_args()

    if args.action == 'login':
        handle_login()
    elif args.action == 'scrape':
        handle_scrape(args)
    elif args.action == 'stats':
        handle_stats()
    elif args.action == 'export':
        handle_export(args)

if __name__ == "__main__":
    main()
