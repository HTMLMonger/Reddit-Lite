from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from script import scrape_reddit
import logging
import os
import sys

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.update(
    SQLALCHEMY_DATABASE_URI='sqlite:///posts.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
)

db = SQLAlchemy(app)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300))
    url = db.Column(db.String(500))
    author = db.Column(db.String(100))
    subreddit = db.Column(db.String(100))
    score = db.Column(db.Integer)
    num_comments = db.Column(db.Integer)
    created_utc = db.Column(db.Float)
    selftext = db.Column(db.Text)
    __table_args__ = (
        db.Index('idx_created_utc', 'created_utc'),
        db.Index('idx_subreddit', 'subreddit'),
    )

def init_db(force=False):
    """Initialize the database and create all tables."""
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'posts.db')
    
    if force and os.path.exists(db_path):
        try:
            os.remove(db_path)
            logger.info(f"Removed existing database: {db_path}")
        except Exception as e:
            logger.error(f"Error removing database: {e}")
            return False

    try:
        # Ensure the instance folder exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

@app.route('/')
def index():
    # Initialize with empty list if no posts yet
    posts = []  # or fetch from your database/storage
    return render_template('index.html', posts=posts, now=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        subreddit = data.get('subreddit', '').strip()
        max_pages = int(data.get('max_pages', 3))
        
        logger.debug(f"Attempting to scrape subreddit: {subreddit}, max_pages: {max_pages}")
        posts = scrape_reddit(max_pages=max_pages, subreddit=subreddit if subreddit else None)
        
        if not posts:
            logger.warning("No posts returned from scrape_reddit")
            return jsonify({'error': 'No posts found'}), 404
            
        # Clear existing posts
        Post.query.delete()
        
        # Add new posts
        for post_data in posts:
            post = Post(
                title=post_data['title'],
                url=post_data['url'],
                author=post_data['author'],
                subreddit=post_data['subreddit'],
                score=post_data['score'],
                num_comments=post_data['num_comments'],
                created_utc=post_data['created_utc'],
                selftext=post_data.get('selftext')
            )
            db.session.add(post)
        
        db.session.commit()
        return jsonify({'message': 'Posts updated successfully'})
        
    except ValueError as ve:
        logger.error(f"Value error in scrape route: {str(ve)}")
        return jsonify({'error': f'Invalid input: {str(ve)}'}), 400
    except Exception as e:
        logger.error(f"Error in scrape route: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/get_posts')
def get_posts():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        posts = Post.query.order_by(Post.created_utc.desc())\
                         .paginate(page=page, per_page=per_page, error_out=False)
        
        if not posts.items:
            return jsonify({'message': 'No posts found'}), 404
            
        posts_data = [{
            'title': post.title,
            'url': post.url,
            'subreddit': post.subreddit,
            'author': post.author,
            'score': post.score,
            'created_utc': post.created_utc,
            'num_comments': post.num_comments,
            'selftext': post.selftext
        } for post in posts.items]
        
        return jsonify({
            'posts': posts_data,
            'total': posts.total,
            'pages': posts.pages,
            'current_page': posts.page
        })
    except Exception as e:
        logger.error(f"Error in get_posts route: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/search')
def search():
    try:
        query = request.args.get('query', '').strip()
        subreddit = request.args.get('subreddit', '').strip()
        pages = min(int(request.args.get('pages', 1)), 10)  # Limit to max 10 pages
        
        if not query and not subreddit:
            return jsonify({'error': 'No search query or subreddit provided'}), 400

        logger.debug(f"Searching with query: {query}, subreddit: {subreddit}, pages: {pages}")
        posts = scrape_reddit(query=query, max_pages=pages, subreddit=subreddit)
        
        if not posts:
            return jsonify({'posts': [], 'message': 'No posts found'})

        # Store posts in database
        Post.query.delete()
        for post_data in posts:
            post = Post(**post_data)
            db.session.add(post)
        db.session.commit()
        
        return jsonify({
            'posts': posts,
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        logger.error(f"Error in search route: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Force database reinitialization to add the new column
    if init_db(force=True):
        print("Database reinitialized successfully")
    else:
        print("Failed to reinitialize database")
    
    app.run(debug=True)
