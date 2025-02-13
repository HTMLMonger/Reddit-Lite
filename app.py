from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from script import scrape_reddit
import logging
import os
import sys
from flask_caching import Cache
from sqlalchemy import text
import traceback
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.update(
    SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={
        'pool_size': 3,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    },
    SQLALCHEMY_ECHO=False,  # Set to True if you want to see the generated SQL statements
    SQLALCHEMY_POOL_TIMEOUT=30,  # Set a timeout for the database connection pool
    SQLALCHEMY_POOL_SIZE=10,  # Set the size of the database connection pool
    SQLALCHEMY_MAX_OVERFLOW=20,  # Set the maximum overflow size of the connection pool
    SQLALCHEMY_POOL_RECYCLE=3600  # Set the recycle time for the database connections
)

# Configure caching
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

db = SQLAlchemy(app)

class Post(db.Model):
    __tablename__ = 'post'
    __table_args__ = {'extend_existing': True}
    
    id= db.Column(db.String(20), primary_key=True)
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
    try:
        with app.app_context():
            if force:
                db.drop_all()
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
@cache.cached(timeout=60)  # Cache for 1 minute
def get_posts():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Optimize query with joins and limit
        posts = db.session.query(Post).order_by(Post.created_utc.desc())\
            .limit(per_page).offset((page - 1) * per_page).all()
        
        total_count = db.session.query(db.func.count(Post.id)).scalar()
        
        if not posts:
            return jsonify({'message': 'No posts found', 'posts': []}), 404
            
        posts_data = [{
            'id': post.id,
            'title': post.title,
            'url': post.url,
            'subreddit': post.subreddit,
            'author': post.author,
            'score': post.score,
            'created_utc': post.created_utc,
            'num_comments': post.num_comments,
            'selftext': post.selftext or ''
        } for post in posts]
        
        return jsonify({
            'posts': posts_data,
            'total': total_count,
            'pages': (total_count + per_page - 1) // per_page,
            'current_page': page
        })
    except Exception as e:
        logger.error(f"Error in get_posts route: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching posts'}), 500

@app.route('/search')
@cache.cached(timeout=300)
def search():
    try:
        query = request.args.get('query', '').strip()
        subreddit = request.args.get('subreddit', '').strip()
        pages = int(request.args.get('pages', 1))
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))

        logger.debug(f"Search params: query={query}, subreddit={subreddit}, pages={pages}, page={page}, per_page={per_page}")

        # Use database query
        posts_query = Post.query

        if query:
            posts_query = posts_query.filter(Post.title.ilike(f'%{query}%'))
        if subreddit:
            posts_query = posts_query.filter(Post.subreddit == subreddit)

        total_count = posts_query.count()
        logger.debug(f"Total posts found in database: {total_count}")

        if total_count == 0:
            # If no results in database, scrape from Reddit
            logger.debug("No results in database, scraping from Reddit")
            try:
                scraped_posts = scrape_reddit(query=query, max_pages=pages, subreddit=subreddit)
                logger.debug(f"Scraped {len(scraped_posts)} posts from Reddit")
            except Exception as scrape_error:
                logger.error(f"Error scraping Reddit: {str(scrape_error)}")
                raise
            
            # Save scraped posts to database
            for post_data in scraped_posts:
                post = Post(**post_data)
                db.session.add(post)
            try:
                db.session.commit()
                logger.debug("Successfully saved scraped posts to database")
            except Exception as db_error:
                logger.error(f"Error saving posts to database: {str(db_error)}")
                db.session.rollback()
                # Instead of raising an exception, we'll continue with the scraped posts
                posts = scraped_posts
                total_count = len(posts)
            else:
                # Rerun the query only if commit was successful
                posts_query = Post.query
                if query:
                    posts_query = posts_query.filter(Post.title.ilike(f'%{query}%'))
                if subreddit:
                    posts_query = posts_query.filter(Post.subreddit == subreddit)
                total_count = posts_query.count()

        posts = posts_query.order_by(Post.created_utc.desc()) \
                           .offset((page - 1) * per_page) \
                           .limit(per_page) \
                           .all()

        formatted_posts = [{
            'id': post.id,
            'title': post.title,
            'url': post.url,
            'author': post.author,
            'subreddit': post.subreddit,
            'score': post.score,
            'num_comments': post.num_comments,
            'created_utc': post.created_utc,
            'selftext': post.selftext or ''
        } for post in posts]

        logger.debug(f"Returning {len(formatted_posts)} posts")
        return jsonify({
            'posts': formatted_posts,
            'total': total_count,
            'pages': (total_count + per_page - 1) // per_page,
            'current_page': page
        })

    except Exception as e:
        logger.error(f"Error in search route: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': 'An error occurred while searching', 'details': str(e)}), 500

@app.route('/debug_db')
def debug_db():
    try:
        # Try to make a simple query
        result = db.session.query(Post).first()
        return jsonify({'status': 'OK', 'message': 'Database connection successful'})
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return jsonify({'status': 'Error', 'message': str(e)}), 500

@app.route('/debug')
def debug_info():
    try:
        env_vars = {key: value for key, value in os.environ.items() if key.startswith('REDDIT_') or key == 'DATABASE_URL'}
        db_url = app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')
        
        # Test database connection
        db_status = 'Not connected'
        db_error = None
        try:
            db.session.execute(text('SELECT 1'))
            db_status = 'Connected'
        except SQLAlchemyError as e:
            db_error = str(e)

        return jsonify({
            'environment': env_vars,
            'database_url': db_url,
            'database_status': db_status,
            'database_error': db_error,
            'app_config': {key: str(value) for key, value in app.config.items() if key != 'SQLALCHEMY_DATABASE_URI'}
        })
    except Exception as e:
        logger.error(f"Error in debug route: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/static_debug/<path:filename>')
def static_debug(filename):
    return send_from_directory(app.static_folder, filename)

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
