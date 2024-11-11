# Helpdesk Ticketing System

## Description
The Helpdesk Ticketing System is a web application designed to streamline the process of managing support tickets within an organization. It allows users to submit new support requests, track the status of their requests, and assign tickets to support engineers. This system aims to improve efficiency and communication in handling support issues.

## Running Commands



### Installation
1. Clone the repository:
    ```bash
    git clone git@github.com:RafaelPereira014/helpdesk_nit.git
    ```

2. Navigate to the project directory:
    ```bash
    cd helpdesk_nit
    ```
2. Install requirements:
    ```bash
    pip install -r requirements.txt
    ```   
4. Set up the MySQL database:
    - Create a new database named `helpdesk`.
    - Import the SQL schema from `helpdesk_backup.sql`.

5. Start the Flask server:
    ```bash
    python app.py
    ```

6. Access the application in your web browser at `http://localhost:5000`.

## Major Requirements
- Python 3.x
- Flask
- MySQL Server

## Contributors
- Rafael Pereira

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
