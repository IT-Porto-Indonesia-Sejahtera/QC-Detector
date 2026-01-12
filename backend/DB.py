"""
Database module for QC-Detector backend.
Provides PostgreSQL database connection pool and query functions.
"""
import psycopg2
from psycopg2.pool import SimpleConnectionPool, PoolError
from psycopg2 import sql, OperationalError, DatabaseError, InterfaceError
from psycopg2.extras import RealDictCursor
import os
import logging
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any, Tuple, Union

# Load environment variables from .env file
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Database connection pool (initialized lazily)
_db_pool: Optional[SimpleConnectionPool] = None


class DatabaseError(Exception):
    """Custom exception for database errors."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    pass


class DatabaseQueryError(DatabaseError):
    """Exception raised when a query fails."""
    pass


def init_db() -> SimpleConnectionPool:
    """
    Initialize the database connection pool.
    Reads configuration from environment variables.
    
    Environment variables:
        DB_HOST: Database host (default: localhost)
        DB_NAME: Database name (default: mydb)
        DB_USER: Database user (default: app_user)
        DB_PASS: Database password (default: secret)
        DB_PORT: Database port (default: 5432)
        DB_MIN_CONN: Minimum connections in pool (default: 1)
        DB_MAX_CONN: Maximum connections in pool (default: 5)
    
    Returns:
        SimpleConnectionPool: The initialized connection pool
    
    Raises:
        DatabaseConnectionError: If connection to database fails
    """
    global _db_pool
    
    if _db_pool is not None:
        return _db_pool
    
    try:
        _db_pool = SimpleConnectionPool(
            minconn=int(os.getenv("DB_MIN_CONN", "1")),
            maxconn=int(os.getenv("DB_MAX_CONN", "5")),
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "mydb"),
            user=os.getenv("DB_USER", "app_user"),
            password=os.getenv("DB_PASS") or os.getenv("DB_PASSWORD", "secret"),
            port=int(os.getenv("DB_PORT", "5432")),
            connect_timeout=10,  # 10 second connection timeout
            # TCP keepalive: server detects dead connections in ~30 seconds
            keepalives=1,              # Enable TCP keepalive
            keepalives_idle=10,        # Seconds before sending keepalive probe
            keepalives_interval=5,     # Seconds between keepalive probes
            keepalives_count=3         # Number of failed probes before closing
        )
        logger.info("Database connection pool initialized successfully")
        return _db_pool
    except OperationalError as e:
        logger.error(f"Failed to connect to database: {e}")
        raise DatabaseConnectionError(f"Failed to connect to database: {e}") from e
    except ValueError as e:
        logger.error(f"Invalid database configuration: {e}")
        raise DatabaseConnectionError(f"Invalid database configuration: {e}") from e


def get_pool() -> Optional[SimpleConnectionPool]:
    """
    Get the database connection pool, initializing if necessary.
    
    Returns:
        SimpleConnectionPool: The connection pool, or None if not initialized
    """
    global _db_pool
    if _db_pool is None:
        try:
            init_db()
        except DatabaseConnectionError:
            return None
    return _db_pool


def is_connected() -> bool:
    """
    Check if the database connection pool is initialized and available.
    
    Returns:
        bool: True if connected, False otherwise
    """
    return _db_pool is not None


def _get_connection():
    """
    Get a connection from the pool with error handling.
    
    Returns:
        Connection object from the pool
    
    Raises:
        DatabaseConnectionError: If no connection is available
    """
    pool = get_pool()
    if pool is None:
        raise DatabaseConnectionError("Database connection pool is not initialized")
    
    try:
        return pool.getconn()
    except PoolError as e:
        logger.error(f"Failed to get connection from pool: {e}")
        raise DatabaseConnectionError(f"No available connections in pool: {e}") from e


def _return_connection(conn, close_on_error: bool = False):
    """
    Return a connection to the pool.
    
    Args:
        conn: Connection object to return
        close_on_error: If True, close the connection instead of returning it
    """
    pool = get_pool()
    if pool is not None and conn is not None:
        try:
            if close_on_error:
                pool.putconn(conn, close=True)
            else:
                pool.putconn(conn)
        except Exception as e:
            logger.warning(f"Error returning connection to pool: {e}")


def fetch_all(
    query: str,
    params: Optional[Union[Tuple, Dict]] = None,
    as_dict: bool = False
) -> List[Any]:
    """
    Execute a SELECT query and fetch all results.
    
    Args:
        query: SQL query string (can use %s or %(name)s placeholders)
        params: Query parameters as tuple or dict (optional)
        as_dict: If True, return results as list of dicts instead of tuples
    
    Returns:
        List of result rows (as tuples or dicts based on as_dict parameter)
        Returns empty list if database is not connected or query fails
    
    Example:
        # Fetch all products
        results = fetch_all("SELECT * FROM products")
        
        # Fetch with positional parameters
        results = fetch_all(
            "SELECT * FROM products WHERE category = %s",
            ("electronics",)
        )
        
        # Fetch with named parameters as dicts
        results = fetch_all(
            "SELECT * FROM products WHERE price > %(min_price)s",
            {"min_price": 100},
            as_dict=True
        )
    """
    if not is_connected():
        logger.warning("Database not connected, returning empty list")
        return []
    
    conn = None
    close_on_error = False
    try:
        conn = _get_connection()
        cursor_factory = RealDictCursor if as_dict else None
        with conn.cursor(cursor_factory=cursor_factory) as cur:
            cur.execute(query, params)
            result = cur.fetchall()
            # Convert RealDictRow to regular dict for JSON serialization
            if as_dict:
                return [dict(row) for row in result]
            return result
    except (OperationalError, InterfaceError) as e:
        # Connection error - mark for closing
        close_on_error = True
        logger.error(f"Database connection error during query: {e}")
        return []
    except psycopg2.DatabaseError as e:
        logger.error(f"Database query error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error during fetch_all: {e}")
        return []
    finally:
        _return_connection(conn, close_on_error)


def fetch_one(
    query: str,
    params: Optional[Union[Tuple, Dict]] = None,
    as_dict: bool = False
) -> Optional[Any]:
    """
    Execute a SELECT query and fetch a single result.
    
    Args:
        query: SQL query string (can use %s or %(name)s placeholders)
        params: Query parameters as tuple or dict (optional)
        as_dict: If True, return result as dict instead of tuple
    
    Returns:
        Single result row (as tuple or dict) or None if no results or error
    
    Example:
        # Fetch single product by ID
        product = fetch_one(
            "SELECT * FROM products WHERE id = %s",
            (123,),
            as_dict=True
        )
    """
    if not is_connected():
        logger.warning("Database not connected, returning None")
        return None
    
    conn = None
    close_on_error = False
    try:
        conn = _get_connection()
        cursor_factory = RealDictCursor if as_dict else None
        with conn.cursor(cursor_factory=cursor_factory) as cur:
            cur.execute(query, params)
            result = cur.fetchone()
            # Convert RealDictRow to regular dict for JSON serialization
            if as_dict and result is not None:
                return dict(result)
            return result
    except (OperationalError, InterfaceError) as e:
        # Connection error - mark for closing
        close_on_error = True
        logger.error(f"Database connection error during query: {e}")
        return None
    except psycopg2.DatabaseError as e:
        logger.error(f"Database query error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during fetch_one: {e}")
        return None
    finally:
        _return_connection(conn, close_on_error)


def close_pool() -> None:
    """
    Close all connections in the pool.
    Call this when shutting down the application.
    Safe to call multiple times.
    """
    global _db_pool
    if _db_pool is not None:
        try:
            _db_pool.closeall()
            logger.info("Database connection pool closed")
        except Exception as e:
            logger.warning(f"Error closing connection pool: {e}")
        finally:
            _db_pool = None
