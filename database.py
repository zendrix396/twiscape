import sqlite3
import json
from typing import List, Dict, Optional
import config

class TweetDatabase:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DATABASE_FILENAME
        self.init_database()
    
    def init_database(self):
        """Initialize the database with the tweets table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if table exists and get its schema
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tweets'")
            table_exists = cursor.fetchone()
            
            if table_exists:
                # Get existing columns
                cursor.execute("PRAGMA table_info(tweets)")
                existing_columns = {row[1] for row in cursor.fetchall()}
                
                # If it's the old schema, migrate it
                if 'author' in existing_columns and 'creator_name' not in existing_columns:
                    print("🔄 Migrating existing database schema...")
                    self._migrate_old_schema(conn)
                else:
                    # Check if we need to add new columns
                    self._add_missing_columns(conn, existing_columns)
            else:
                # Create new table
                cursor.execute('''
                    CREATE TABLE tweets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tweet_id TEXT UNIQUE,
                        serial_no INTEGER,
                        creator_name TEXT NOT NULL,
                        creator_username TEXT,
                        content TEXT NOT NULL,
                        media_url TEXT,
                        created_at TEXT,
                        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        retweet_count INTEGER DEFAULT 0,
                        like_count INTEGER DEFAULT 0,
                        reply_count INTEGER DEFAULT 0,
                        view_count INTEGER DEFAULT 0
                    )
                ''')
            
            # Create indexes for better performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tweet_id ON tweets(tweet_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_creator_username ON tweets(creator_username)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_scraped_at ON tweets(scraped_at)
            ''')
            
            conn.commit()
            print(f"📦 Database initialized at '{self.db_path}'")
    
    def _migrate_old_schema(self, conn):
        """Migrate the old database schema to the new one."""
        cursor = conn.cursor()
        
        # Rename old table
        cursor.execute('ALTER TABLE tweets RENAME TO tweets_old')
        
        # Create new table with updated schema
        cursor.execute('''
            CREATE TABLE tweets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_id TEXT UNIQUE,
                serial_no INTEGER,
                creator_name TEXT NOT NULL,
                creator_username TEXT,
                content TEXT NOT NULL,
                media_url TEXT,
                created_at TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                retweet_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0,
                reply_count INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0
            )
        ''')
        
        # Migrate data from old table to new table
        cursor.execute('''
            INSERT INTO tweets (tweet_id, creator_name, content, created_at, retweet_count, like_count, reply_count, view_count)
            SELECT tweet_id, author, content, posted_on, 
                   COALESCE(retweets, 0), COALESCE(likes, 0), COALESCE(replies, 0), COALESCE(views, 0)
            FROM tweets_old
        ''')
        
        # Drop old table
        cursor.execute('DROP TABLE tweets_old')
        
        print("✅ Successfully migrated database schema")
    
    def _add_missing_columns(self, conn, existing_columns):
        """Add any missing columns to the existing table."""
        cursor = conn.cursor()
        
        required_columns = {
            'serial_no': 'INTEGER',
            'creator_username': 'TEXT',
            'media_url': 'TEXT',
            'scraped_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        
        for column, column_type in required_columns.items():
            if column not in existing_columns:
                try:
                    cursor.execute(f'ALTER TABLE tweets ADD COLUMN {column} {column_type}')
                    print(f"✅ Added column '{column}' to database")
                except sqlite3.OperationalError:
                    # Column might already exist or other error
                    pass
    
    def insert_tweet(self, tweet_data: Dict) -> bool:
        """Insert a single tweet into the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO tweets 
                    (tweet_id, serial_no, creator_name, creator_username, content, media_url, 
                     created_at, retweet_count, like_count, reply_count, view_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tweet_data.get('tweet_id'),
                    tweet_data.get('serial_no'),
                    tweet_data.get('creator_name'),
                    tweet_data.get('creator_username'),
                    tweet_data.get('content'),
                    tweet_data.get('media_url'),
                    tweet_data.get('created_at'),
                    tweet_data.get('retweet_count', 0),
                    tweet_data.get('like_count', 0),
                    tweet_data.get('reply_count', 0),
                    tweet_data.get('view_count', 0)
                ))
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"❌ Error inserting tweet: {e}")
            return False
    
    def insert_tweets_batch(self, tweets: List[Dict]) -> int:
        """Insert multiple tweets in a batch operation."""
        inserted_count = 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for tweet in tweets:
                    try:
                        cursor.execute('''
                            INSERT OR REPLACE INTO tweets 
                            (tweet_id, serial_no, creator_name, creator_username, content, media_url, 
                             created_at, retweet_count, like_count, reply_count, view_count)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            tweet.get('tweet_id'),
                            tweet.get('serial_no'),
                            tweet.get('creator_name'),
                            tweet.get('creator_username'),
                            tweet.get('content'),
                            tweet.get('media_url'),
                            tweet.get('created_at'),
                            tweet.get('retweet_count', 0),
                            tweet.get('like_count', 0),
                            tweet.get('reply_count', 0),
                            tweet.get('view_count', 0)
                        ))
                        inserted_count += 1
                    except sqlite3.IntegrityError:
                        # Tweet already exists, skip
                        continue
                conn.commit()
        except sqlite3.Error as e:
            print(f"❌ Error in batch insert: {e}")
        
        return inserted_count
    
    def get_tweet_count(self) -> int:
        """Get the total number of tweets in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM tweets')
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(f"❌ Error getting tweet count: {e}")
            return 0
    
    def get_tweets(self, limit: int = None, offset: int = 0) -> List[Dict]:
        """Retrieve tweets from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row  # This allows dict-like access
                cursor = conn.cursor()
                
                if limit:
                    cursor.execute('''
                        SELECT * FROM tweets 
                        ORDER BY scraped_at DESC 
                        LIMIT ? OFFSET ?
                    ''', (limit, offset))
                else:
                    cursor.execute('SELECT * FROM tweets ORDER BY scraped_at DESC')
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            print(f"❌ Error retrieving tweets: {e}")
            return []
    
    def get_latest_serial_no(self) -> int:
        """Get the highest serial number in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT MAX(serial_no) FROM tweets')
                result = cursor.fetchone()[0]
                return result if result is not None else 0
        except sqlite3.Error as e:
            print(f"❌ Error getting latest serial number: {e}")
            return 0
    
    def tweet_exists(self, tweet_id: str) -> bool:
        """Check if a tweet with the given ID already exists."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM tweets WHERE tweet_id = ? LIMIT 1', (tweet_id,))
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            print(f"❌ Error checking tweet existence: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total tweets
                cursor.execute('SELECT COUNT(*) FROM tweets')
                total_tweets = cursor.fetchone()[0]
                
                # Unique creators
                cursor.execute('SELECT COUNT(DISTINCT creator_username) FROM tweets')
                unique_creators = cursor.fetchone()[0]
                
                # Date range
                cursor.execute('SELECT MIN(scraped_at), MAX(scraped_at) FROM tweets')
                date_range = cursor.fetchone()
                
                return {
                    'total_tweets': total_tweets,
                    'unique_creators': unique_creators,
                    'first_scraped': date_range[0],
                    'last_scraped': date_range[1]
                }
        except sqlite3.Error as e:
            print(f"❌ Error getting stats: {e}")
            return {}
    
    def export_to_json(self, output_file: str = None) -> bool:
        """Export all tweets to a JSON file."""
        output_file = output_file or 'exported_tweets.json'
        try:
            tweets = self.get_tweets()
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(tweets, f, indent=4, ensure_ascii=False, default=str)
            print(f"✅ Exported {len(tweets)} tweets to '{output_file}'")
            return True
        except Exception as e:
            print(f"❌ Error exporting to JSON: {e}")
            return False
    
    def import_from_json(self, json_file: str) -> int:
        """Import tweets from a JSON file."""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                tweets = json.load(f)
            
            if not isinstance(tweets, list):
                print("❌ JSON file should contain a list of tweets")
                return 0
            
            imported_count = self.insert_tweets_batch(tweets)
            print(f"✅ Imported {imported_count} tweets from '{json_file}'")
            return imported_count
        except Exception as e:
            print(f"❌ Error importing from JSON: {e}")
            return 0
