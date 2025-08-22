import json
from urllib.parse import quote
import config
from database import TweetDatabase

def build_search_url():
    """Builds a valid X.com search URL from the configuration variables."""
    query_parts = []
    
    if config.SEARCH_QUERY:
        query_parts.append(config.SEARCH_QUERY)
    
    if config.FROM_ACCOUNTS:
        from_string = " OR ".join([f"from:{account}" for account in config.FROM_ACCOUNTS])
        query_parts.append(f"({from_string})")
    
    if config.SINCE_DATE:
        query_parts.append(f"since:{config.SINCE_DATE}")
    if config.UNTIL_DATE:
        query_parts.append(f"until:{config.UNTIL_DATE}")
        
    if config.LANGUAGE:
        query_parts.append(f"lang:{config.LANGUAGE}")
        
    raw_query = " ".join(query_parts)
    if not raw_query:
        raise ValueError("Search configuration is empty. Please set SEARCH_QUERY or FROM_ACCOUNTS.")
        
    encoded_query = quote(raw_query)
    
    return f"https://x.com/search?q={encoded_query}&src=typed_query&f=live"

def process_and_append_tweets(raw_data_filename):
    """
    Processes the raw data and stores cleaned tweets in the SQLite database.
    """
    # Initialize database connection
    db = TweetDatabase()
    
    # Get the current highest serial number
    start_sno = db.get_latest_serial_no() + 1

    try:
        with open(raw_data_filename, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Error: Could not read or parse '{raw_data_filename}': {e}")
        return 0

    newly_cleaned_tweets = []
    try:
        instructions = raw_data.get('data', {}).get('search_by_raw_query', {}).get('search_timeline', {}).get('timeline', {}).get('instructions', [])
        entries = []
        for instruction in instructions:
            if instruction.get('type') == 'TimelineAddEntries':
                entries.extend(instruction.get('entries', []))
        if not entries:
            print("⚠️ No tweet entries found in the expected format in the latest data.")
            return 0
    except (KeyError, IndexError, TypeError) as e:
        print(f"❌ Error: Could not find tweet entries in the expected format: {e}")
        return 0

    for entry in entries:
        if "tweet-" not in entry.get('entryId', ''):
            continue
        try:
            tweet_result = entry.get('content', {}).get('itemContent', {}).get('tweet_results', {}).get('result', {})
            if not tweet_result: continue

            # Extract tweet ID from entryId
            tweet_id = entry.get('entryId', '').replace('tweet-', '')
            
            # Skip if tweet already exists in database
            if db.tweet_exists(tweet_id):
                continue

            # Extract user info
            user_result = tweet_result['core']['user_results']['result']
            creator_name = user_result['core']['name']
            creator_username = user_result['core']['screen_name']
            
            # Extract tweet content
            if 'note_tweet' in tweet_result and tweet_result.get('note_tweet', {}).get('is_expandable'):
                content_text = tweet_result['note_tweet']['note_tweet_results']['result']['text']
            else:
                content_text = tweet_result['legacy']['full_text']

            # Extract media URL
            media_url = None
            if 'extended_entities' in tweet_result['legacy'] and 'media' in tweet_result['legacy']['extended_entities']:
                media_item = tweet_result['legacy']['extended_entities']['media'][0]
                if media_item.get('type') == 'photo':
                    media_url = media_item.get('media_url_https')
                elif media_item.get('type') == 'video':
                    variants = media_item.get('video_info', {}).get('variants', [])
                    best_variant = max((v for v in variants if 'bitrate' in v), key=lambda v: v['bitrate'], default=None)
                    if best_variant: media_url = best_variant.get('url')
            
            # Extract engagement metrics
            legacy = tweet_result.get('legacy', {})
            retweet_count = legacy.get('retweet_count', 0)
            like_count = legacy.get('favorite_count', 0)
            reply_count = legacy.get('reply_count', 0)
            
            # Extract view count from views field
            view_count = 0
            if 'views' in tweet_result and 'count' in tweet_result['views']:
                view_count = int(tweet_result['views']['count'])
            
            # Extract created_at timestamp
            created_at = legacy.get('created_at', '')

            newly_cleaned_tweets.append({
                "tweet_id": tweet_id,
                "serial_no": start_sno + len(newly_cleaned_tweets),
                "creator_name": creator_name,
                "creator_username": creator_username,
                "content": content_text.strip(),
                "media_url": media_url,
                "created_at": created_at,
                "retweet_count": retweet_count,
                "like_count": like_count,
                "reply_count": reply_count,
                "view_count": view_count
            })
        except (KeyError, IndexError, TypeError) as e:
            print(f"⚠️ Skipping malformed tweet entry: {e}")
            continue

    if newly_cleaned_tweets:
        inserted_count = db.insert_tweets_batch(newly_cleaned_tweets)
        print(f"✅ Processed and stored {inserted_count} new tweets in database")
        return inserted_count
    else:
        print("✅ No new tweets to store in this batch.")
        return 0
