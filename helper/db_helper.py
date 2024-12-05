"""DB Helper"""
import os
from mysql.connector.pooling import MySQLConnectionPool

DB_HOST = os.environ.get('DB_HOST', 'localhost').strip()
DB_NAME = os.environ.get('DB_NAME', 'db_transaction').strip()
DB_USER = os.environ.get('DB_USER', 'root').strip()
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'transaction').strip()
DB_POOLNAME = os.environ.get('DB_POOLNAME', 'transaction_pool').strip()
POOL_SIZE = int(os.environ.get('POOL_SIZE', '5').strip())
PORT = int(os.environ.get('PORT', '3307').strip())


db_pool = MySQLConnectionPool(
    host=DB_HOST,
    user=DB_USER,
    port=PORT,
    password=DB_PASSWORD,
    database=DB_NAME,
    pool_size=POOL_SIZE,  
    pool_name=DB_POOLNAME
)


def get_connection():
    """
    Get connection db connection from db pool
    """
    connection = db_pool.get_connection()
    connection.autocommit = True
    return connection
