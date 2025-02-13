from app import app, db, Post
import logging
import psycopg2
import os
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def init_db(force=False):
    """Initialize the database and create all tables."""
    try:
        with app.app_context():
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')
            logger.info(f"Attempting to connect to database: {db_url}")
            
            if force:
                db.drop_all()
            db.create_all()
            logger.info("Database tables created successfully")
        return True
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemy error initializing database: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error initializing database: {e}")
        return False

def add_selftext_column():
    """Add the selftext column to the post table if it doesn't exist."""
    with app.app_context():
        try:
            # Check if the column already exists
            Post.__table__.create(db.engine, checkfirst=True)
            if 'selftext' not in Post.__table__.columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE post ADD COLUMN IF NOT EXISTS selftext TEXT'))
                logger.info("Successfully added selftext column")
            else:
                logger.info("Selftext column already exists")
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemy error adding selftext column: {e}")
        except Exception as e:
            logger.error(f"Unexpected error adding selftext column: {e}")

if __name__ == "__main__":
    try:
        if init_db(force=True):
            logger.info("Database initialized successfully")
            add_selftext_column()
        else:
            logger.error("Failed to initialize database")
    except Exception as e:
        logger.error(f"Exception occurred during database initialization: {e}")
