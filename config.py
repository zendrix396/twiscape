UNTIL_DATE = None
LANGUAGE = "en"

# List of scrape jobs to run in parallel
SCRAPE_JOBS = [
    {
        "search_query": "SaaS",
        "from_accounts": [],
        "since_date": "2022-01-01",
        "until_date": None,
        "max_tweets": 500
    },
    {
        "search_query": "AI in marketing",
        "from_accounts": [],
        "since_date": "2023-01-01",
        "until_date": None,
        "max_tweets": 1000
    },
    {
        "search_query": "branding",
        "from_accounts": ["sama"],
        "since_date": "2023-01-01",
        "until_date": None,
        "max_tweets": 250
    }
]

# Keep other global settings
RAW_DATA_FILENAME = "data/data.json"
DATABASE_FILENAME = "database/tweets.db"
COOKIES_FILENAME = "data/cookies.json"
LOGIN_URL = "https://x.com/login"
MAX_EMPTY_SCROLLS = 3