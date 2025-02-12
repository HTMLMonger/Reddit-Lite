import requests
import logging
from datetime import datetime
import time
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def truncate_text(text, max_length=100):
    return text[:max_length] + '...' if len(text) > max_length else text

def scrape_reddit(max_pages=3, subreddit=None, query=None):
    posts = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # Construct base URL based on whether it's a search or subreddit listing
    if query:
        if subreddit:
            base_url = f'https://www.reddit.com/r/{subreddit}/search.json'
            params = {'q': query, 'restrict_sr': 1, 'sort': 'new', 'limit': 100}
        else:
            base_url = 'https://www.reddit.com/search.json'
            params = {'q': query, 'sort': 'new', 'limit': 100}
    else:
        if subreddit:
            base_url = f'https://www.reddit.com/r/{subreddit}/hot.json'
            params = {'limit': 100}
        else:
            base_url = 'https://www.reddit.com/hot.json'
            params = {'limit': 100}
    
    after = None
    page_count = 0
    
    while page_count < max_pages:
        try:
            if after:
                params['after'] = after
                
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            after = data.get('data', {}).get('after')
            
            for post in data.get('data', {}).get('children', []):
                post_data = post.get('data', {})
                posts.append({
                    'title': post_data.get('title', ''),
                    'url': post_data.get('url', ''),
                    'author': post_data.get('author', ''),
                    'subreddit': post_data.get('subreddit', ''),
                    'score': post_data.get('score', 0),
                    'num_comments': post_data.get('num_comments', 0),
                    'created_utc': post_data.get('created_utc', 0),
                    'selftext': post_data.get('selftext', '')  # Add selftext to the post data
                })
            
            page_count += 1
            
            if not after:  # No more pages available
                break
                
            time.sleep(2)  # Be nice to Reddit's servers
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            break
    
    return posts
