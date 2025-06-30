# Database Operations

from datetime import datetime
import re
from config import DB_CONFIG  # Import the database configuration
from flask import session
import pymysql # Import MySQL Connector Python module
from flask_mail import Message
import hashlib
import logging

def connect_to_database():
    """Establishes a connection to the MySQL database."""
    return pymysql.connect(**DB_CONFIG)


# User Authentication and Authorization

def is_admin(user_id):
    """Checks if the user is an Admin"""
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT type FROM users WHERE id = %s", (user_id,))
    user_type = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user_type and user_type[0] == 'admin':  # Check if user_type is not None and compare the first element of the tuple
        return True
    else:
        return False
    
def validate_user(username, password):
    """Validates user credentials against the database."""
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def get_user_group(user_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT group_id FROM users WHERE id = %s", (user_id,))
    user_group = cursor.fetchone()
    cursor.close()
    conn.close()
    return user_group[0] if user_group else None

def get_username(user_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE id = %s", (user_id,))
    user_name = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return user_name

def verify_password(user_id,password):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE id = %s", (user_id,))
    stored_password = cursor.fetchone()
    if stored_password and password == stored_password[0]:
        return True
    
    return False


def update_password(user_id, password):
    # Hash the password
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return "Password updated successfully"


def check_email_contains_edu(user_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    try:
        # Fetch the email for the given user_id
        cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        
        if result:  # Check if a result was returned
            user_email = result[0]  # Extract the email string from the tuple
            print(f"User email: {user_email}")
            
            # Check if "@edu" or "@inforpereira" is in the email string
            return "@edu" in user_email or "@inforpereira" in user_email
        else:
            print("No email found for the given user ID.")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def get_all_users():
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users where visible='1' ORDER BY name ASC")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return users;

def get_all_unidades():
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM unidadesorganicas ORDER BY name ASC")
    unidades = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    
    return unidades;

def get_all_gra():
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT nome FROM divisoesGra ORDER BY nome ASC")
    unidades = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    
    return unidades;

def get_all_ilhas():
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ilhas ORDER BY nome ASC")  # Fetch all fields
    ilhas = cursor.fetchall()  # Fetch all rows
    cursor.close()
    conn.close()
    
    return ilhas  # Return the entire list of rows


def change_password(email):
    try:
        conn = connect_to_database()
        cursor = conn.cursor()
        
        query = "UPDATE users SET password='59886fe3e4a390d23717ffc12004fdf754df4084ff23d7be65130205b865926e' WHERE email = %s"
        values = (email,)
        
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        # Check if any rows were affected
        if cursor.rowcount > 0:
            return True
        else:
            return False
    except Exception as e:
        # Log the exception for debugging
        print(f"Error changing password for {email}: {e}")
        return False
    




# Ticket Operations

def get_ticket_details(ticket_id):
    """Fetches ticket details and associated messages from the database based on the ticket ID."""
    if not ticket_id:
        print("Error: ticket_id is None or invalid.")
        return None

    conn = connect_to_database()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Fetch ticket details
        cursor.execute("""
            SELECT id, description, date, state, created_by, attributed_to, contacto, 
                   title, closed_by, file, UnidadeOrg, attributed_to_name, accepted_at, closed_at 
            FROM tickets 
            WHERE id = %s
        """, (ticket_id,))
        ticket_details = cursor.fetchone()

        if not ticket_details:
            print(f"No ticket found with ID: {ticket_id}")
            return None

        # Fetch messages associated with the ticket
        cursor.execute("""
            SELECT message, sender_type, sent_at, sender_name 
            FROM messages 
            WHERE ticket_id = %s
        """, (ticket_id,))
        messages = cursor.fetchall()
        ticket_details['messages'] = messages

        return ticket_details

    except Exception as e:
        print(f"Error fetching ticket details: {e}")
        return None

    finally:
        cursor.close()
        conn.close()


def get_latest_ticket_message(ticket_id):
    connection = connect_to_database()  # Assuming you have a function to connect to your DB
    cursor = connection.cursor(pymysql.cursors.DictCursor)  # Use dictionary cursor for easier result handling

    try:
        # Query to get the latest ticket message by the highest ID
        query = """
            SELECT * 
            FROM messages
            WHERE ticket_id = %s
            ORDER BY id DESC
            LIMIT 1
        """
        cursor.execute(query, (ticket_id,))
        latest_message = cursor.fetchone()  # Fetch a single result
        return latest_message
    except Exception as e:
        print(f"Error retrieving latest ticket message: {e}")
        return None
    finally:
        cursor.close()
        connection.close()
    
def clean_description(description):
    """Remove unnecessary HTML tags, line breaks, and extra spaces."""
    
    # Remove any leading/trailing spaces from paragraphs
    description = re.sub(r'<p>\s*|\s*</p>', '', description)
    
    # Collapse all other whitespace characters (spaces, newlines, etc.)
    description = re.sub(r'\s+', ' ', description.strip())
    
    return description


def get_all_tickets():
    """Fetches all tickets from the database ordered by creation date (newest to oldest)."""
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM tickets ORDER BY id DESC")
    tickets = cursor.fetchall()
    cursor.close()
    conn.close()
    return tickets

def update_ticket_accept_time(ticket_id, accept_time):
    conn = connect_to_database()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE tickets SET accepted_at = %s WHERE id = %s",
            (accept_time, ticket_id)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def update_ticket_close_time(ticket_id, close_time):
    conn = connect_to_database()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE tickets SET closed_at = %s WHERE id = %s",
            (close_time, ticket_id)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()
        
def send_ticket_message(ticket_id, message_content, sender_type, sender_name,sent_at, file_url=None):
    connection = connect_to_database()
    cursor = connection.cursor()
    
    # Insert message into the database
    if file_url:
        cursor.execute("""
            INSERT INTO messages (ticket_id, message, sender_type, sender_name, file,sent_at) 
            VALUES (%s, %s, %s, %s, %s,%s)
        """, (ticket_id, message_content, sender_type, sender_name, file_url))
    else:
        cursor.execute("""
            INSERT INTO messages (ticket_id, message, sender_type, sender_name,sent_at) 
            VALUES (%s, %s, %s, %s,%s)
        """, (ticket_id, message_content, sender_type, sender_name,sent_at))
    
    connection.commit()
    cursor.close()
    
def insert_files_ticket(ticket_id,user_id,date,file_url):
    connection = connect_to_database()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO anexos (ticket_id,anexed_by,anexed_at,file_url) VALUES (%s,%s,%s,%s)",(ticket_id,user_id,date,file_url,))
    connection.commit()
    cursor.close()
    
def count_files_ticket(ticket_id):
    connection = connect_to_database()
    cursor = connection.cursor()
    
    # Execute the SELECT query to count the files
    cursor.execute("SELECT COUNT(*) FROM anexos WHERE ticket_id=%s", (ticket_id,))
    
    # Fetch the result and extract the count
    result = cursor.fetchone()  # fetchone() returns a tuple (count,)
    
    cursor.close()
    connection.close()
    
    # Return the count of files
    return result[0] if result else 0



def get_all_tickets_group(group_id):
    """Fetches all tickets from the database."""
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM tickets WHERE group_id = %s ORDER BY id DESC", (group_id,))
    tickets = cursor.fetchall()
    cursor.close()
    conn.close()
    return tickets

def get_all_tickets_user(user_id):
    """Fetches all tickets from the database."""
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS all_tickets_count FROM tickets WHERE created_by = %s", (user_id,))
    all_tickets_count = cursor.fetchone()
    cursor.close()
    conn.close()
    return all_tickets_count['all_tickets_count'] if all_tickets_count else 0

def get_opened_tickets_count_by_group(group_id):
    """Fetches the number of opened tickets for a specific group."""
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS opened_tickets_count FROM tickets WHERE state = 'Aberto' AND group_id = %s", (group_id,))
    opened_tickets_count = cursor.fetchone()
    cursor.close()
    conn.close()
    return opened_tickets_count['opened_tickets_count'] if opened_tickets_count else 0

def get_opened_tickets_count_by_user(user_id):
    """Fetches the number of opened tickets for a specific group."""
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS opened_tickets_count FROM tickets WHERE state = 'Aberto' AND created_by = %s", (user_id,))
    opened_tickets_count = cursor.fetchone()
    cursor.close()
    conn.close()
    return opened_tickets_count['opened_tickets_count'] if opened_tickets_count else 0

def get_closed_tickets_count_by_group(group_id):
    """Fetches the number of opened tickets for a specific group."""
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS closed_tickets_count FROM tickets WHERE state = 'Fechado' AND group_id = %s", (group_id,))
    closed_tickets_count = cursor.fetchone()
    cursor.close()
    conn.close()
    return closed_tickets_count['closed_tickets_count'] if closed_tickets_count else 0

def get_closed_tickets_count_by_user(user_id):
    """Fetches the number of opened tickets for a specific group."""
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS closed_tickets_count FROM tickets WHERE state = 'Fechado' AND created_by = %s", (user_id,))
    closed_tickets_count = cursor.fetchone()
    cursor.close()
    conn.close()
    return closed_tickets_count['closed_tickets_count'] if closed_tickets_count else 0

def get_executing_tickets_count_by_group(group_id):
    """Fetches the number of opened tickets for a specific group."""
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS executing_tickets_count FROM tickets WHERE state = 'em execucao' AND group_id = %s", (group_id,))
    executing_tickets_count = cursor.fetchone()
    cursor.close()
    conn.close()
    return executing_tickets_count['executing_tickets_count'] if executing_tickets_count else 0

def get_executing_tickets_count_by_user(user_id):
    """Fetches the number of opened tickets for a specific group."""
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS executing_tickets_count FROM tickets WHERE state = 'em execucao' AND created_by = %s", (user_id,))
    executing_tickets_count = cursor.fetchone()
    cursor.close()
    conn.close()
    return executing_tickets_count['executing_tickets_count'] if executing_tickets_count else 0

def create_ticket(topic_id, description, date, state, created_by, contacto, title,UnidadeOrg,file):
    """Creates a new ticket in the database."""
    conn = connect_to_database()
    cursor = conn.cursor()
    print(UnidadeOrg)
    try:
        if 'DRAC' in UnidadeOrg:
            group_id = 5
        elif 'SGC' in UnidadeOrg:
            group_id = 6
        else:
            # Fetch the group_id associated with the provided topic_id
            cursor.execute("SELECT group_id FROM Topics WHERE id = %s", (topic_id,))
            group_id_row = cursor.fetchone()
            if group_id_row is not None:
                group_id = group_id_row[0]
            else:
                # Handle the case when no result is found
                group_id = None  # or raise an exception, depending on your application logic

        # Fetch the name of the user based on the created_by ID
        cursor.execute("SELECT name FROM users WHERE id = %s", (created_by,))
        created_by_user = cursor.fetchone()[0]

        # Insert the new ticket with the fetched group_id and created_by_user
        cursor.execute("""
            INSERT INTO tickets (topic_id, description, date, state, created_by, contacto, title, group_id, created_by_user,UnidadeOrg,file)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (topic_id, description, date, state, created_by, contacto, title, group_id, created_by_user,UnidadeOrg,file))
        conn.commit()
        print("Ticket created successfully")
    except pymysql.connector.Error as e:
        print("Error creating ticket:", e)
    finally:
        cursor.close()
        conn.close()
        
def get_user_tickets(user_ids):
    """Fetches tickets associated with the given user ID(s)."""
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    if isinstance(user_ids, list):
        # Generate placeholders for the IN clause dynamically
        query = "SELECT id, date, state, description, attributed_to, contacto, title FROM tickets WHERE created_by IN (%s) ORDER BY id DESC" % ','.join(['%s'] * len(user_ids))
        cursor.execute(query, user_ids)
    else:
        cursor.execute("SELECT id, date, state, description, attributed_to, contacto, title FROM tickets WHERE created_by = %s ORDER BY id DESC", (user_ids,))
    user_tickets = cursor.fetchall()
    cursor.close()
    conn.close()
    return user_tickets

def get_creator_name(ticket_id):
    try:
        conn = connect_to_database()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT users.name
            FROM users
            JOIN tickets ON users.id = tickets.created_by
            WHERE tickets.id = %s
        """, (ticket_id,))
        creator_name = cursor.fetchone()
        return creator_name[0] if creator_name else None  # Return None if no user found
    except Exception as e:
        print("Error:", e)
    finally:
        cursor.close()
        conn.close()
        
def get_unidadeOrg(ticket_id):
    try:
        conn = connect_to_database()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT UnidadeOrg
            FROM tickets where id=%s
        """, (ticket_id,))
        creator_name = cursor.fetchone()
        return creator_name[0] if creator_name else None  # Return None if no user found
    except Exception as e:
        print("Error:", e)
    finally:
        cursor.close()
        conn.close()

def no_open_tickets():
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE state = 'Aberto'")
    num_open_tickets = cursor.fetchone()[0]
    cursor.close()
    return num_open_tickets

def no_closed_tickets():
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE state = 'Fechado'")
    num_closed_tickets = cursor.fetchone()[0]
    cursor.close()
    return num_closed_tickets

def no_execution_tickets():
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE state = 'em execucao'")
    num_execution_tickets = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return num_execution_tickets

def get_ticketid(description):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM tickets WHERE description = %s ORDER BY date DESC LIMIT 1",
        (description,)
    )
    ticket_id = cursor.fetchone()  # Fetch the first row
    cursor.close()
    conn.close()
    if ticket_id:
        return ticket_id[0]  # Return the first ticket ID if found
    else:
        return None  # Return None if no ticket is found with the given description
    
def get_title(ticket_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM tickets WHERE id = %s LIMIT 1", (ticket_id,))
    title = cursor.fetchone()  # Fetch the first row
    cursor.close()
    conn.close()
    if title:
        return title[0]  # Return the first ticket ID if found
    else:
        return None  # Return None if no ticket is found with the given description
    
def tickets_today():
    conn = connect_to_database()
    cursor = conn.cursor()
    
    # Get today's date in YYYY-MM-DD format
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Query to count tickets created today
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE DATE(date) = %s", (today,))
    tickets_today = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    return tickets_today

def tickets_solved_today():
    conn = connect_to_database()
    cursor = conn.cursor()
    
    # Get today's date in YYYY-MM-DD format
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Query to count tickets created today
    cursor.execute("SELECT COUNT(*) FROM tickets WHERE DATE(date) = %s and state='Fechado'", (today,))
    tickets_solved_today = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    return tickets_solved_today




def claim_ticket(user_id, ticket_id):
    try:
        conn = connect_to_database()
        cursor = conn.cursor() 
        # Update the attributed_to field
        cursor.execute("UPDATE tickets SET attributed_to = %s WHERE id = %s", (user_id, ticket_id))
        # Update the state to "em execucao"
        cursor.execute("UPDATE tickets SET state = %s WHERE id = %s", ("em execucao", ticket_id))
        conn.commit()
        cursor.execute("""
            UPDATE tickets AS t
            JOIN users AS u ON t.attributed_to = u.id
            SET t.attributed_to_name = u.name
        """)
        
        conn.commit()
        print("Ticket attributed successfully and state updated to 'em execucao'")
    except Exception as e:
        print("Error attributing ticket:", e)
    finally:
        cursor.close()
        conn.close()

        
def attributed_to(user_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE id = %s", (user_id,))
    user_attributed = cursor.fetchone()[0]
    cursor.close()
    return user_attributed

def attributed_to_by_ticket(ticket_id):
    try:
        conn = connect_to_database()
        cursor = conn.cursor()
        cursor.execute("SELECT attributed_to_name FROM tickets WHERE id = %s", (ticket_id,))
        result = cursor.fetchone()
        if result is None:
            print(f"No data found for ticket_id: {ticket_id}")
            return None
        user_name = result[0]
        return user_name
    except Exception as e:
        print(f"Error querying database: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_user_id_by_name(user_name):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE name = %s", (user_name,))
    user_id = cursor.fetchone()[0]  # Assuming user names are unique
    cursor.close()
    conn.close()
    return user_id

def assign_ticket_to_user(ticket_id,user_name):
    assigned_user_id = get_user_id_by_name(user_name)
    conn = connect_to_database()
    if assigned_user_id:
        conn = connect_to_database()
        cursor = conn.cursor()
        cursor.execute("UPDATE tickets SET created_by = %s WHERE id = %s ", (assigned_user_id, ticket_id))
        conn.commit()
        cursor.close()
        conn.close()
        return "Ticket assigned to user successfully"
    else:
        return "User not found"
    
    

def get_open_tickets_count_by_admin(username):
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS open_tickets_count FROM tickets WHERE created_by_user = %s", (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result['open_tickets_count'] if result else 0

def get_closed_tickets_count_by_admin(username):
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS closed_tickets_count FROM tickets WHERE closed_by = %s", (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result['closed_tickets_count'] if result else 0

def get_executing_tickets_count_by_admin(username):
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS executing_tickets_count FROM tickets WHERE state='Em execução' AND attributed_to_name = %s", (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result['executing_tickets_count'] if result else 0


def get_ticket_group(ticketid):
    try:
        conn = connect_to_database()
        cursor = conn.cursor()
        cursor.execute("SELECT group_id FROM tickets WHERE id = %s", (ticketid,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result:
            logging.info(f"Successfully fetched group_id for ticket {ticketid}: {result[0]}")
            return result[0]
        else:
            logging.warning(f"No group_id found for ticket {ticketid}")
            return None
    except Exception as e:
        logging.error(f"Error fetching group_id for ticket {ticketid}: {e}")
        return None

def update_ticket_group(group_id, ticket_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("UPDATE tickets SET group_id = %s WHERE id = %s", (group_id, ticket_id))
    conn.commit()
    cursor.close()
    conn.close()

def get_tickets_for_user(user_id):
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    query = """
        SELECT * FROM tickets
        WHERE created_by = %s OR attributed_to = %s OR closed_by = %s
        ORDER BY id DESC
    """
    cursor.execute(query, (user_id, user_id, user_id))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


def count_executing_tickets_admin(username):
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)  # Use dictionary cursor for better result handling
    query = """
        SELECT COUNT(*) AS executing_tickets_count 
        FROM tickets 
        WHERE state='Em execução' 
        AND (attributed_to_name = %s OR created_by_user = %s)
    """
    cursor.execute(query, (username, username))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result['executing_tickets_count']

def search_tickets(keyword):
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM tickets WHERE title LIKE %s ORDER BY id DESC", ('%' + keyword + '%',))
    tickets = cursor.fetchall()
    cursor.close()
    conn.close()
    return tickets

def search_id(id):
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM tickets WHERE id LIKE %s ORDER BY id DESC", ('%' + id + '%',))
    tickets_id = cursor.fetchall()
    cursor.close()
    conn.close()
    return tickets_id


def search_unidadeorg(unidadeorg):
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM tickets WHERE UnidadeOrg LIKE %s ORDER BY id DESC", ('%' + unidadeorg + '%',))
    tickets_unidadeorg = cursor.fetchall()
    cursor.close()
    conn.close()
    return tickets_unidadeorg

def search_for_user(user):
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM tickets WHERE created_by_user LIKE %s ORDER BY id DESC", ('%' + user + '%',))
    tickets_by_user = cursor.fetchall()
    cursor.close()
    conn.close()
    return tickets_by_user

def search_for_date(date):
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM tickets WHERE date LIKE %s ORDER BY id DESC", ('%' + date + '%',))
    tickets_by_user = cursor.fetchall()
    cursor.close()
    conn.close()
    return tickets_by_user

    


# Miscellaneous Operations


##-------topicos---------##
def get_topics():
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Topics where visible='1' ORDER BY key_word ASC")
    topics = cursor.fetchall()
    cursor.close()
    conn.close()
    return topics

def get_topic_id(ticket_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    # Use a parameterized query to avoid SQL injection
    query = "SELECT topic_id FROM tickets WHERE id = %s "
    cursor.execute(query, (ticket_id,))
    topic_id = cursor.fetchone()  # Fetch the first (and only) row returned by the query
    cursor.close()
    conn.close()
    return topic_id[0] if topic_id else None  # Return the topic_id or None if no topic found




def topic_exists(key_word):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM Topics WHERE key_word = %s", (key_word,))
    exists = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return exists


def insert_topic(keyword, group_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Topics (key_word, group_id) VALUES (%s, %s)", (keyword, group_id))
    conn.commit()
    cursor.close()
    conn.close()
    
def get_topic_name(topic_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    # Use a parameterized query to avoid SQL injection
    query = "SELECT key_word FROM Topics WHERE id = %s "
    cursor.execute(query, (topic_id,))
    topic = cursor.fetchone()  # Fetch the first (and only) row returned by the query
    cursor.close()
    conn.close()
    return topic[0] if topic else None  # Return the topic_id or None if no topic found


def delete_topic(topic_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Topics WHERE id = %s", (topic_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
def visible(topic_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("UPDATE Topics set visible='1' WHERE id = %s", (topic_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
def invisible(topic_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("UPDATE Topics set visible='0' WHERE id = %s", (topic_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
def user_visible(user_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("UPDATE users set visible='1' WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
def user_invisible(user_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("UPDATE users set visible='0' WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
def update_user_name(name,user_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("UPDATE users set name=%s WHERE id = %s", (name,user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
def search_topics(keyword):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Topics WHERE key_word LIKE %s", ('%' + keyword + '%',))
    topics = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Convert each tuple to a dictionary
    topics_dict = []
    for topic in topics:
        topic_dict = {
            'id': topic[0],
            'key_word': topic[1],
            'group_id': topic[2]
        }
        topics_dict.append(topic_dict)
    
    return topics_dict

def edu_topics():
    conn = connect_to_database()
    cursor = conn.cursor()
    keyword = 'EDU'
    
    # Query to select topics containing the keyword 'EDU'
    cursor.execute("SELECT id,key_word FROM Topics WHERE key_word LIKE %s AND visible='1' ORDER BY key_word ASC", ('%' + keyword + '%',))
    
    # Fetch all matching rows
    edu_tickets = cursor.fetchall()
    
    # Extract the first element from each tuple in the list
    
    
    cursor.close()
    conn.close()
    
    return edu_tickets

def gra_topics():
    conn = connect_to_database()
    cursor = conn.cursor()
    keyword = 'EDU'
    
    # Query to select topics containing the keyword 'EDU'
    cursor.execute("SELECT id,key_word FROM Topics WHERE key_word NOT LIKE %s AND visible='1' ORDER BY key_word ASC", ('%' + keyword + '%',))
    
    # Fetch all matching rows
    gra_tickets = cursor.fetchall()
    
    # Extract the first element from each tuple in the list
    
    
    cursor.close()
    conn.close()
    
    return gra_tickets






def save_file_to_database(ticket_id, filename, file_type, file_path, user_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ticket_attachments (ticket_id, filename, file_type, file_path, uploaded_by)
        VALUES (%s, %s, %s, %s, %s)
    """, (ticket_id, filename, file_type, file_path, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    
def save_file_to_message_database(ticket_id, message_id, filename, file_type, file_path):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO message_attachments (message_id, filename, file_type, file_path)
        VALUES (%s, %s, %s, %s)
    """, (message_id, filename, file_type, file_path))
    conn.commit()
    cursor.close()
    conn.close()


##---------------------------------##   

def get_user_details(ticket_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, type,uo FROM users JOIN ON tickets.user.id=users.id WHERE Tickes.ticket_id = %s", ticket_id)
    user_details = cursor.fetchone()
    cursor.close()
    return user_details

def close_ticket(user_id, ticket_id):
    """Closes a ticket by updating its state to 'closed' and sets the 'closed_by' field."""
    # Establish a database connection
    conn = connect_to_database()
    cursor = conn.cursor()
    
    # Fetch the name of the user who is closing the ticket
    cursor.execute("SELECT name FROM users WHERE id = %s", (user_id,))
    user_name = cursor.fetchone()[0]
    
    # Update the ticket state and set the closed_by field
    cursor.execute("UPDATE tickets SET state = 'Fechado', closed_by = %s WHERE id = %s", (user_name, ticket_id))
    conn.commit()
    print("Ticket closed successfully")
    
    # Close the cursor and connection
    cursor.close()
    conn.close()


def reopen_ticket(ticket_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("UPDATE tickets SET state = 'Aberto' WHERE id = %s", (ticket_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return reopen_ticket

def is_closed(ticket_id):
    """Checks if the ticket is closed"""
    closed =0;
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT state FROM Ticket WHERE id = %s", (ticket_id,))
    ticket_state = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if ticket_state == 'Fechado':  # Check if user_type is not None and compare the first element of the tuple
        closed+=1;
        return True
    else:
        return False
    
def add_message_to_ticket(ticket_id, message):
    """Adds a message to the conversation of a ticket."""
    conn = connect_to_database()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO messages (ticket_id, message, sender_type) VALUES (%s, %s, 'admin')",
                       (ticket_id, message))
        conn.commit()
        print("Message added to ticket successfully")
    except mysql.connector.Error as e:
        print("Error adding message to ticket:", e)
    finally:
        cursor.close()
        conn.close()
        
def get_group_name(ticket_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    
    try:
        # Fetch the topic ID associated with the ticket
        cursor.execute("SELECT topic_id FROM tickets WHERE id = %s", (ticket_id,))
        topic_id = cursor.fetchone()[0]
        
        # Fetch the group ID associated with the topic
        cursor.execute("SELECT group_id FROM Topics WHERE id = %s", (topic_id,))
        group_id = cursor.fetchone()[0]
        
        # Fetch the group name based on the group ID
        cursor.execute("SELECT name FROM `Groups` WHERE id = %s", (group_id,))
        group_name = cursor.fetchone()
        
        return group_name[0] if group_name else None  # Return the group name or None if not found
    except Exception as e:
        print("Error fetching group name:", e)
        return None
    finally:
        cursor.close()
        conn.close()



#SMTP 

def get_user_email_by_user(user_id):
    """Fetches the email of the user with the given ID."""
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
    user_email = cursor.fetchone()
    cursor.close()
    conn.close()
    if user_email:
        return user_email[0]  # Return the email if found
    return None  # Return None if user not found or email is not available

def get_user_email_by_ticket(ticket_id):
    """Fetches the email of the user who created the ticket with the given ID."""
    conn = connect_to_database()
    cursor = conn.cursor()
    
    # Fetch the user ID who created the ticket
    cursor.execute("SELECT created_by FROM tickets WHERE id = %s", (ticket_id,))
    ticket_creator = cursor.fetchone()
    
    # If ticket_creator is not None and contains the user ID
    if ticket_creator:
        user_id = ticket_creator[0]  # Extract the user ID from the tuple
        
        # Fetch the email of the user with the extracted user ID
        cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
        user_email = cursor.fetchone()
        
        # Close the cursor and connection
        cursor.close()
        conn.close()
        
        # If user_email is not None, return the email, otherwise return None
        if user_email:
            return user_email[0]  # Return the email if found
    
    # If ticket_creator is None or user_email is None, return None
    return None

def get_emails_by_group(ticket_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT group_id FROM tickets WHERE id = %s", (ticket_id,))
    group_ids = cursor.fetchall()  # Fetch all group IDs for the given ticket
    
    # Extract group IDs from the result
    group_ids = [row[0] for row in group_ids]
    
    # Query emails for all retrieved group IDs
    emails = []
    for group_id in group_ids:
        cursor.execute("SELECT email FROM users WHERE group_id = %s", (group_id,))
        emails.extend(cursor.fetchall())
    
    cursor.close()
    conn.close()
    
    email_list = [row[0] for row in emails]  # Extract emails from the result
    
    return email_list


def is_super_admin(user_id):
    """Checks if the user is an Super Admin"""
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT group_id FROM users WHERE id = %s", (user_id,))
    group_id = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if group_id and group_id[0] == 3:  # Check if user_type is not None and compare the first element of the tuple
        return True
    else:
        return False

def get_unidade_name_by_id(uni_org_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM unidadesorganicas WHERE id = %s", (uni_org_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result[0] if result else None


#Database ADMIN actions 

def dump_database():
    return 0


def get_opened_tickets_count_by_users(user_ids):
    """Fetches the number of opened tickets for the given user ID(s)."""
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    if isinstance(user_ids, list):
        query = "SELECT COUNT(*) AS opened_tickets_count FROM tickets WHERE state = 'Aberto' AND created_by IN (%s)" % ','.join(['%s'] * len(user_ids))
        cursor.execute(query, user_ids)
    else:
        cursor.execute("SELECT COUNT(*) AS opened_tickets_count FROM tickets WHERE state = 'Aberto' AND created_by = %s", (user_ids,))
    opened_tickets_count = cursor.fetchone()
    cursor.close()
    conn.close()
    return opened_tickets_count['opened_tickets_count'] if opened_tickets_count else 0

def get_closed_tickets_count_by_users(user_ids):
    """Fetches the number of closed tickets for the given user ID(s)."""
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    if isinstance(user_ids, list):
        query = "SELECT COUNT(*) AS closed_tickets_count FROM tickets WHERE state = 'Fechado' AND created_by IN (%s)" % ','.join(['%s'] * len(user_ids))
        cursor.execute(query, user_ids)
    else:
        cursor.execute("SELECT COUNT(*) AS closed_tickets_count FROM tickets WHERE state = 'Fechado' AND created_by = %s", (user_ids,))
    closed_tickets_count = cursor.fetchone()
    cursor.close()
    conn.close()
    return closed_tickets_count['closed_tickets_count'] if closed_tickets_count else 0

def get_executing_tickets_count_by_users(user_ids):
    """Fetches the number of executing tickets for the given user ID(s)."""
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    if isinstance(user_ids, list):
        query = "SELECT COUNT(*) AS executing_tickets_count FROM tickets WHERE state = 'em execucao' AND created_by IN (%s)" % ','.join(['%s'] * len(user_ids))
        cursor.execute(query, user_ids)
    else:
        cursor.execute("SELECT COUNT(*) AS executing_tickets_count FROM tickets WHERE state = 'em execucao' AND created_by = %s", (user_ids,))
    executing_tickets_count = cursor.fetchone()
    cursor.close()
    conn.close()
    return executing_tickets_count['executing_tickets_count'] if executing_tickets_count else 0

def get_all_tickets_users(user_ids):
    """Fetches all tickets count for the given user ID(s)."""
    conn = connect_to_database()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    if isinstance(user_ids, list):
        query = "SELECT COUNT(*) AS all_tickets_count FROM tickets WHERE created_by IN (%s)" % ','.join(['%s'] * len(user_ids))
        cursor.execute(query, user_ids)
    else:
        cursor.execute("SELECT COUNT(*) AS all_tickets_count FROM tickets WHERE created_by = %s", (user_ids,))
    all_tickets_count = cursor.fetchone()
    cursor.close()
    conn.close()
    return all_tickets_count['all_tickets_count'] if all_tickets_count else 0