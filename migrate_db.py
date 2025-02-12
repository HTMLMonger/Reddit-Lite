from app import app, db
import sqlite3

def add_selftext_column():
    with app.app_context():
        try:
            # Connect to the database
            conn = sqlite3.connect('instance/posts.db')
            cursor = conn.cursor()
            
            # Add the new column
            cursor.execute('ALTER TABLE post ADD COLUMN selftext TEXT')
            
            # Commit the changes
            conn.commit()
            print("Successfully added selftext column")
            
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("Column already exists")
            else:
                print(f"Error: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    add_selftext_column()
