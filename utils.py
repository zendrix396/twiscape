import json
from urllib.parse import quote
import config

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

def process_and_append_tweets(raw_data_filename, cleaned_output_filename):
    """
    Processes the raw data and appends cleaned tweets to the output file.
    """
    try:
        with open(cleaned_output_filename, 'r', encoding='utf-8') as f:
            existing_cleaned_tweets = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing_cleaned_tweets = []
    start_sno = len(existing_cleaned_tweets) + 1

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

            creator_name = tweet_result['core']['user_results']['result']['core']['name']

            if 'note_tweet' in tweet_result and tweet_result.get('note_tweet', {}).get('is_expandable'):
                content_text = tweet_result['note_tweet']['note_tweet_results']['result']['text']
            else:
                content_text = tweet_result['legacy']['full_text']

            media_url = None
            if 'extended_entities' in tweet_result['legacy'] and 'media' in tweet_result['legacy']['extended_entities']:
                media_item = tweet_result['legacy']['extended_entities']['media'][0]
                if media_item.get('type') == 'photo':
                    media_url = media_item.get('media_url_https')
                elif media_item.get('type') == 'video':
                    variants = media_item.get('video_info', {}).get('variants', [])
                    best_variant = max((v for v in variants if 'bitrate' in v), key=lambda v: v['bitrate'], default=None)
                    if best_variant: media_url = best_variant.get('url')

            newly_cleaned_tweets.append({
                "serial_no": start_sno + len(newly_cleaned_tweets),
                "creator_name": creator_name,
                "content": content_text.strip(),
                "media_url": media_url
            })
        except (KeyError, IndexError, TypeError):
            continue

    if newly_cleaned_tweets:
        all_cleaned_tweets = existing_cleaned_tweets + newly_cleaned_tweets
        with open(cleaned_output_filename, 'w', encoding='utf-8') as f:
            json.dump(all_cleaned_tweets, f, indent=4, ensure_ascii=False)
        print(f"✅ Processed and appended {len(newly_cleaned_tweets)} new tweets -> '{cleaned_output_filename}'")
        return len(newly_cleaned_tweets)
    else:
        print("✅ No new tweets to append in this batch.")
        return 0
