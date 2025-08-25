## Twiscape
Extract relevant tweets in json format

---
### Configure Browser

You can go to `auth.py` and `scraper.py` and replace the `.Firefox` instance with your required browser like `Edge` or `Chrome`

---
### Install the requirements
```bash
pip install -r requirements.txt
```
---
### Login to your account
```bash
python main.py login
```
>It will ask for username and password, add the correct information and a new `cookie.json` file will be created that will help with persistence sessions.
>It might throw some error sometimes when using headless settings, to fix it you can comment out these 3 lines and it will work just fine.

```python
# auth.py
        comment them
        # options.add_argument("--headless")
        # options.add_argument("--disable-gpu")
        # options.add_argument("--no-sandbox")
```
---
### Customizing your query

* go to `config.py`
* edit the configuration to extract relevant tweets as per your requirement, you can also edit the file name where it is going to be saved, and limit the number of generation as well.
```python
# config.py
SEARCH_QUERY = "open source"
FROM_ACCOUNTS = ["dhh", "fireship_dev"]
SINCE_DATE = "2024-01-01"
UNTIL_DATE = None
LANGUAGE = "en"
RAW_DATA_FILENAME = "data.json"
CLEANED_DATA_FILENAME = "cleaned_tweets.json"
COOKIES_FILENAME = "cookies.json"
LOGIN_URL = "https://x.com/login"
MAX_TWEETS = 100
MAX_EMPTY_SCROLLS = 3
```
---
### Scrape the content
Run this command to start the scraping process
```bash
python main.py scrape
```