from app import app, db
import logging
import psycopg2
import os

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

def add_selftext_column():
    """Add the selftext column to the post table if it doesn't exist."""
    with app.app_context():
        try:
            # Connect to the PostgreSQL database
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cursor = conn.cursor()
            
            # Add the new column
            cursor.execute('ALTER TABLE post ADD COLUMN selftext TEXT')
            
            # Commit the changes
            conn.commit()
            logger.info("Successfully added selftext column")
            
        except psycopg2.Error as e:
            if "duplicate column name" in str(e):
                logger.info("Column already exists")
            else:
                logger.error(f"Error: {e}")
        finally:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    try:
        if init_db(force=True):
            logger.info("Database initialized successfully")
            add_selftext_column()
        else:
            logger.error("Failed to initialize database")
    except Exception as e:
        logger.error(f"Exception occurred during database initialization: {e}")
