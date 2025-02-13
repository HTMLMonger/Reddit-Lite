from app import app, db
import logging

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
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

if __name__ == "__main__":
    if init_db(force=True):
        print("Database initialized successfully")
    else:
        print("Failed to initialize database")
