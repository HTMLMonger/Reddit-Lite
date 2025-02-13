from app import app, db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Post(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    # ...existing code...

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

if __name__ == "__main__":
    if init_db(force=True):
        print("Database initialized successfully")
    else:
        print("Failed to initialize database")
