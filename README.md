# Twitter Scraper

A powerful Twitter scraping tool that extracts tweets and stores them in a SQLite database using Selenium WebDriver.

## Features

- Search tweets by query string
- Filter by specific accounts  
- Date range filtering (since/until)
- Language filtering
- Infinite scroll automation
- SQLite database storage with deduplication
- Session management with cookie persistence
- Export functionality to JSON
- Database statistics and analytics
- Enhanced engagement metrics capture

## File Structure

```
twitter_scraper/
├── data/                    # JSON data files
│   ├── cookies.json        # Login session cookies
│   └── data.json          # Raw API responses (temporary)
├── database/               # Database files
│   └── tweets.db          # SQLite database with scraped tweets
├── auth.py                # Authentication module
├── config.py              # Configuration settings
├── database.py            # Database operations module
├── main.py                # Main CLI interface
├── scraper.py             # Core scraping functionality
├── utils.py               # Utility functions
└── requirements.txt       # Python dependencies
```

## Setup

### Install Requirements
```bash
pip install -r requirements.txt
```

### Configure Browser
You can go to `auth.py` and `scraper.py` and replace the `.Firefox` instance with your required browser like `Edge` or `Chrome`

### Login to Your Account
```bash
python main.py login
```

> It will ask for username and password, add the correct information and a new `cookies.json` file will be created in the `data/` folder that will help with persistence sessions.
> 
> It might throw some error sometimes when using headless settings, to fix it you can comment out these 3 lines and it will work just fine:

```python
# auth.py
# options.add_argument("--headless")
# options.add_argument("--disable-gpu")  
# options.add_argument("--no-sandbox")
```

## Configuration

Edit `config.py` to customize default settings:

```python
# config.py
SEARCH_QUERY = "open source"
FROM_ACCOUNTS = ["dhh", "fireship_dev"]
SINCE_DATE = "2024-01-01"
UNTIL_DATE = None
LANGUAGE = "en"
RAW_DATA_FILENAME = "data/data.json"        # Raw API responses
DATABASE_FILENAME = "database/tweets.db"    # SQLite database file
COOKIES_FILENAME = "data/cookies.json"      # Login cookies
LOGIN_URL = "https://x.com/login"
MAX_TWEETS = 55
MAX_EMPTY_SCROLLS = 3
```

## Database Schema

The SQLite database stores tweets with the following fields:
- `id`: Auto-incrementing primary key
- `tweet_id`: Unique Twitter ID
- `serial_no`: Sequential number
- `creator_name`: Display name of the author
- `creator_username`: Username (@handle)
- `content`: Tweet text content
- `media_url`: URL to attached media (photos/videos)
- `created_at`: Original tweet timestamp
- `scraped_at`: When the tweet was scraped
- `retweet_count`, `like_count`, `reply_count`, `view_count`: Engagement metrics

## CLI Usage

### Authentication
```bash
# Login and save cookies
python main.py login
```

### Scraping
```bash
# Basic scraping with current config
python main.py scrape

# Search for specific terms
python main.py scrape "artificial intelligence"

# Search by specific authors
python main.py scrape --by elonmusk openai

# Search with date range
python main.py scrape "AI" --timeline "2024-01-01 to 2024-12-31"

# Combined parameters
python main.py scrape "machine learning" --by andrewng --timeline "2024-06-01 to 2024-12-31"
```

### Database Management
```bash
# Show database statistics
python main.py stats

# Export tweets to JSON
python main.py export

# Export to specific file
python main.py export --output my_tweets.json
```

## Output Files

The tool creates:
- `database/tweets.db`: SQLite database with all scraped tweets
- `data/data.json`: Raw API responses (temporary)
- `data/cookies.json`: Login session cookies

## Database Operations

You can also interact with the database programmatically:

```python
from database import TweetDatabase

db = TweetDatabase()

# Get statistics
stats = db.get_stats()

# Get recent tweets
recent_tweets = db.get_tweets(limit=100)

# Export to JSON
db.export_to_json("backup.json")

# Import from JSON (migration helper)
db.import_from_json("old_tweets.json")
```

## Migration from JSON

If you have existing `cleaned_tweets.json` files, you can import them into the database:

```bash
python -c "
from database import TweetDatabase
db = TweetDatabase()
db.import_from_json('cleaned_tweets.json')
"
```