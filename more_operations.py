from datetime import datetime
from config import DB_CONFIG  # Import the database configuration
from flask import session
import pymysql # Import MySQL Connector Python module



def connect_to_database():
    """Establishes a connection to the MySQL database."""
    return pymysql.connect(**DB_CONFIG)

def execute_query(query, params=None):
    """Executes a query on the MySQL database."""
    connection = connect_to_database()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)  # Executes the query
            result = cursor.fetchall()  # Fetch all results
            connection.commit()  # Commit if needed (for insert/update/delete)
            return result
    except Exception as e:
        connection.rollback()  # Rollback in case of an error
        raise e
    finally:
        connection.close()  # Ensure the connection is always closed

def get_topics(visible=True):
    query = "SELECT id,key_word,group_id FROM topics WHERE visible = %s"
    return execute_query(query, (visible,))

def get_users(visible=True):
    # Query to fetch id and name from the users table where the 'visible' column matches the given value
    query = "SELECT id, name FROM users WHERE visible = %s"
    
    # Execute the query and return the result
    return execute_query(query, (visible,))

def search_topics(keyword, visible=True):
    query = "SELECT * FROM topics WHERE key_word LIKE %s AND visible = %s"
    return execute_query(query, (f"%{keyword}%", visible))

def search_users(keyword, visible=True):
    query = "SELECT * FROM users WHERE name LIKE %s AND visible = %s"
    return execute_query(query, (f"%{keyword}%", visible))
