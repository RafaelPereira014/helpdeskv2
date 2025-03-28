import csv
import pymysql
from config import CONTAINER_DB_CONFIG



def connect_to_database():
    """Establishes a connection to the MySQL database."""
    return pymysql.connect(**CONTAINER_DB_CONFIG)

def update_names_from_csv(csv_file_path, table_name, column_name):
    """
    Updates rows in a table based on a CSV file.
    Expects the CSV file to have 'id' as the first column, 'nome1' as the second, and 'nome2' as the third.
    """
    try:
        # Establish database connection
        connection = connect_to_database()
        cursor = connection.cursor()

        # Read the CSV file
        with open(csv_file_path, mode='r', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file, delimiter=';')  
            
            # Update database rows for each valid CSV entry
            for row in reader:
                if len(row) != 3:
                    print(f"Skipping invalid row: {row}")
                    continue  # Skip rows that don't have exactly three values
                
                record_id, nome1, nome2 = row  # Extract `id`, `nome1`, and `nome2` from each row
                
                # Convert `record_id` to an integer
                try:
                    record_id = int(record_id)
                except ValueError:
                    print(f"Invalid ID value: {record_id}, skipping row.")
                    continue
                
                cursor.execute(
                    f"""
                    UPDATE {table_name}
                    SET {column_name} = %s
                    WHERE id = %s
                    """,
                    (nome2, record_id)
                )

        # Commit the changes to the database
        connection.commit()
        return "Names updated successfully!"
    except Exception as e:
        # Rollback in case of an error
        if 'connection' in locals():
            connection.rollback()
        return f"Error occurred: {e}"
    finally:
        # Close the connection
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    # Configuration
    csv_path = "static/files/utilizadores_helpdesk.csv"  # Replace with the actual path to your CSV file
    table = "users"          # Replace with your table name
    column = "name"   # Replace with the column name to update

    # Execute the function
    result = update_names_from_csv(csv_path, table, column)
    print(result)