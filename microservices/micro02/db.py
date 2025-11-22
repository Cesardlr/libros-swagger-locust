import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    """Create and return a database connection using environment variables."""
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", ""),
        database=os.getenv("DB_NAME", "Libros"),
        port=int(os.getenv("DB_PORT", "3306")),
        charset=os.getenv("DB_CHARSET", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor
    )


