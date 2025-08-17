import argparse
from auth import TwitterAuth
from scraper import TwitterScraper
import getpass

def main():
    parser = argparse.ArgumentParser(description="Twitter Scraper Tool")
    parser.add_argument('action', choices=['login', 'scrape'], help="Action to perform: 'login' to save cookies, 'scrape' to start scraping.")
    
    args = parser.parse_args()

    if args.action == 'login':
        username = input("Enter your X.com username or email: ")
        password = getpass.getpass("Enter your X.com password: ")
        if username and password:
            auth = TwitterAuth(username, password)
            auth.login()
        else:
            print("❌ Username and password cannot be empty. Aborting.")
    
    elif args.action == 'scrape':
        scraper = TwitterScraper()
        scraper.scrape()

if __name__ == "__main__":
    main()
