import requests
import logging
from datetime import datetime
import time
import os
from bs4 import BeautifulSoup
import concurrent.futures
from functools import partial

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_reddit_token(client_id, client_secret):
    auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
    data = {'grant_type': 'client_credentials'}
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.post('https://www.reddit.com/api/v1/access_token', auth=auth, data=data, headers=headers)
    response.raise_for_status()
    return response.json()['access_token']

def fetch_page(base_url, headers, params, after=None):
    """Fetch a single page of results"""
    try:
        if after:
            params = {**params, 'after': after}
        response = requests.get(base_url, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching page: {str(e)}")
        return None

def scrape_reddit(max_pages=3, subreddit=None, query=None):
    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    token = get_reddit_token(client_id, client_secret)
    headers = {
        'Authorization': f'bearer {token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # Construct base URL and params
    if query:
        if subreddit:
            base_url = f'https://oauth.reddit.com/r/{subreddit}/search'
            params = {'q': query, 'restrict_sr': 1, 'sort': 'new', 'limit': 100}
        else:
            base_url = 'https://oauth.reddit.com/search'
            params = {'q': query, 'sort': 'new', 'limit': 100}
    else:
        if subreddit:
            base_url = f'https://oauth.reddit.com/r/{subreddit}/hot'
            params = {'limit': 100}
        else:
            base_url = 'https://oauth.reddit.com/hot'
            params = {'limit': 100}

    # Get first page to get 'after' tokens
    first_page = fetch_page(base_url, headers, params)
    if not first_page:
        return []

    posts = []
    after_tokens = []
    current_after = first_page.get('data', {}).get('after')
    
    # Collect all 'after' tokens first
    while current_after and len(after_tokens) < max_pages - 1:
        after_tokens.append(current_after)
        response = fetch_page(base_url, headers, params, current_after)
        if not response:
            break
        current_after = response.get('data', {}).get('after')

    # Process first page results
    for post in first_page.get('data', {}).get('children', []):
        post_data = post.get('data', {})
        posts.append({
            'title': post_data.get('title', ''),
            'url': post_data.get('url', ''),
            'author': post_data.get('author', ''),
            'subreddit': post_data.get('subreddit', ''),
            'score': post_data.get('score', 0),
            'num_comments': post_data.get('num_comments', 0),
            'created_utc': post_data.get('created_utc', 0),
            'selftext': post_data.get('selftext', '')
        })

    # Use ThreadPoolExecutor for concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        fetch_with_params = partial(fetch_page, base_url, headers, params)
        future_to_after = {executor.submit(fetch_with_params, after): after for after in after_tokens}
        
        for future in concurrent.futures.as_completed(future_to_after):
            try:
                data = future.result()
                if data and 'data' in data:
                    for post in data['data'].get('children', []):
                        post_data = post.get('data', {})
                        posts.append({
                            'title': post_data.get('title', ''),
                            'url': post_data.get('url', ''),
                            'author': post_data.get('author', ''),
                            'subreddit': post_data.get('subreddit', ''),
                            'score': post_data.get('score', 0),
                            'num_comments': post_data.get('num_comments', 0),
                            'created_utc': post_data.get('created_utc', 0),
                            'selftext': post_data.get('selftext', '')
                        })
            except Exception as e:
                logger.error(f"Error processing page: {str(e)}")

    return posts
