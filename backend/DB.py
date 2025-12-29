import psycopg2
from psycopg2.pool import SimpleConnectionPool
import os

DB_POOL = SimpleConnectionPool(
    minconn=1,
    maxconn=5,
    host=os.getenv("DB_HOST", "localhost"),
    database=os.getenv("DB_NAME", "mydb"),
    user=os.getenv("DB_USER", "app_user"),
    password=os.getenv("DB_PASS", "secret"),
    port=5432
)

def fetch_all(query, params=None):
    conn = DB_POOL.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    finally:
        DB_POOL.putconn(conn)
