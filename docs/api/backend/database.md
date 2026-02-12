# Database (DB)

PostgreSQL database module with connection pooling and query functions.

::: backend.DB
    options:
      members:
        - DatabaseError
        - DatabaseConnectionError
        - DatabaseQueryError
        - init_db
        - get_pool
        - is_connected
        - fetch_all
        - fetch_one
        - close_pool
