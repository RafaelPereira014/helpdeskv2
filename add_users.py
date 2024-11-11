import mysql.connector
from mysql.connector import Error, IntegrityError

def connect_to_database():
    # Replace these values with your actual database connection details
    config = {
        'user': 'root',
        'password': 'passroot',
        'host': 'localhost',
        'database': 'helpdesk4',
        'charset': 'utf8mb4'  # Set the charset to handle Unicode characters
    }
    conn = mysql.connector.connect(**config)
    return conn

def insert_names_from_file(filename):
    conn = connect_to_database()
    cursor = conn.cursor()

    # Read data from the file and insert into the database
    with open(filename, 'r', encoding='utf-8') as file:  # Ensure to use UTF-8 encoding for file reading
        next(file)  # Skip header if exists
        for line in file:
            fields = line.strip().split(';')  # Assuming CSV format
            name = fields[0].strip()  # Assuming the first field is the name
            query = "INSERT INTO unidadesorganicas (name) VALUES (%s)"
            try:
                cursor.execute(query, (name,))
                conn.commit()  # Commit after each successful insert
                print(f"Inserted name: {name}")
            except IntegrityError as e:
                # Skip duplicate entry and continue with the next
                print(f"Skipping duplicate entry for name: {name}")
                continue
            except Error as e:
                # Handle other database errors
                print(f"Error: {e}")
                continue

    cursor.close()
    conn.close()

if __name__ == "__main__":
    insert_names_from_file('static/files/divisoes_escolas.txt')
    