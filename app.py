import csv
import datetime
import bleach
from functools import wraps
import secrets
import os
import subprocess
import mysql.connector
from flask import Flask, flash, jsonify, render_template, request, redirect, send_from_directory, url_for
from db_operations import *
from flask import session
from flask import redirect
from datetime import datetime
from flask import request
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from flask import render_template
from flask import send_file





app = Flask(__name__)
# Generate a secure secret key


app.secret_key = secrets.token_bytes(16)
app.config['MAIL_SERVER']='pegasus.azores.gov.pt'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 's0204helpdesk'
app.config['MAIL_PASSWORD'] = 'RL3kieLAziocp7iK'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx','zip'}

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
mail=Mail(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']



config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'passroot',
    'database': 'helpdesk4'
}

connection = mysql.connector.connect(**config)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['username']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = connect_to_database()
        cursor = conn.cursor()
        cursor.execute("SELECT id, type, password FROM users WHERE email = %s", (email,))
        user_data = cursor.fetchone()  # Fetch the user ID, type, and hashed password from the database
        cursor.close()

        if user_data:
            stored_password = user_data[2]
            if hashed_password == stored_password:
                session['user_id'] = user_data[0]  # Store user ID in session
                session['user_type'] = user_data[1]  # Store user type in session
                if is_admin(user_data[0]):
                    return redirect(url_for('admin_init'))  # Redirect admin users to admin_init page
                else:
                    return redirect(url_for('init_page'))  # Redirect non-admin users to init_page
        error = 'Invalid credentials. Please try again.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()  # Clear session data
    return redirect(url_for('index'))  # Redirect to homepage after logout

@app.route('/init_page')
def init_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login page if user is not logged in

    user_id = session['user_id']
    open_tickets = get_opened_tickets_count_by_user(user_id)
    closed_tickets = get_closed_tickets_count_by_user(user_id)
    executing_tickets = get_executing_tickets_count_by_user(user_id)
    
    return render_template('init.html', open_tickets=open_tickets,closed_tickets=closed_tickets,executing_tickets=executing_tickets)

@app.route('/my_profile', methods=['GET', 'POST'])
def profile_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login page if user is not logged in

    user_id = session['user_id']
    user_name = get_username(user_id)
    admin_status = is_admin(user_id)

    message = None  # Initialize message variable
    
    tickets_closed_by = get_closed_tickets_count_by_admin(user_name)
    tickets_open_by = get_open_tickets_count_by_admin(user_name)
    tickets_executing_by = get_executing_tickets_count_by_admin(user_name)
    

    if request.method == 'POST':
        password = request.form['password']
        new_pass = request.form['new_password']
        confirm_pass = request.form['confirm_password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()


        # Verify the current password
        if verify_password(user_id, hashed_password):
            # Update the password
            if new_pass == confirm_pass:
                update_password(user_id, new_pass)
                message = {'type': 'success', 'content': 'Password atualizada com sucesso!'}
            else:
                message = {'type': 'error', 'content': 'Nova password não confirmada.Tente outra vez.'}
        else:
            message = {'type': 'error', 'content': 'Password incorreta!'}

    return render_template('new_forms/my_profile.html', user_name=user_name, is_admin=admin_status, message=message, tickets_closed_by= tickets_closed_by,tickets_open_by=tickets_open_by,tickets_executing_by=tickets_executing_by)



@app.route('/admin_init')
def admin_init():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login page if user is not logged in
    
    user_id = session['user_id']
    super_admin = is_super_admin(user_id)
    tickets_created_today = tickets_today()
    tickets_solved = tickets_solved_today()
    
    return render_template('admin_init.html',super_admin=super_admin,tickets_created_today=tickets_created_today,tickets_solved=tickets_solved)



@app.route('/new_ticket', methods=['GET', 'POST'])
def new_ticket():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login page if user is not logged in
    
    user_id = session['user_id']
    is_edu = check_email_contains_edu(user_id) 
    admin_status = is_admin(user_id)
    all_users = get_all_users()
    all_unidades = get_all_unidades()
    edu_topics_list = edu_topics()
    gra_topics_list = gra_topics()
    all_topics = get_topics()

    if request.method == 'POST':
        topic_id = request.form['topic_id']
        description = request.form['description']
        state = "Aberto"
        uni_org = request.form['UnidadeOrg']
        date = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        contacto = request.form['contacto']
        title = request.form['title']
        assigned_to = request.form.get('assigned_to')
        
        if assigned_to:
            created_by = get_user_id_by_name(assigned_to)
            user_name = get_username(created_by)
        else:
            created_by = session.get('user_id')
            user_name = get_username(created_by)
            
        
        # Check if file is uploaded
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            else:
                filename = "Sem ficheiro."
        else:
            filename = "Sem ficheiro."
        
        

        create_ticket(topic_id, description, date, state, created_by, contacto, title, uni_org, filename)

        ticket_id = get_ticketid(description)
        user_email = get_user_email_by_user(created_by)
        admin_emails = get_emails_by_group(ticket_id)

        # Email notifications
        if user_email:
        # Send email notification to user
            msg = Message(f'Helpdesk NIT: {title} #{ticket_id}', sender='noreply@azores.gov.pt', recipients=[user_email])
            with app.open_resource('static/files/styles.css') as f:
                css_content = f.read().decode('utf-8')
            msg.html = f"""
                <html>
                <head>
                    <style>{css_content}</style>
                </head>
                <body>
                    <h1>Caro(a) {user_name}</h1>
                    <p>O seu pedido de apoio foi registado e foi-lhe atribuída a referência #{ticket_id}.</p>
                    <p>Logo que possível um dos técnicos do Núcleo de Informática e Telecomunicações fará o despiste e irá apoiar na resolução da situação.</p>
                    <p>Poderá, a qualquer momento, acompanhar em <a href="https://helpdesk.edu.azores.gov.pt">https://helpdesk.edu.azores.gov.pt</a> a evolução do seu pedido:</p>
                    <p>Assunto: {title}</p>
                    <p>{description}</p>
                    <hr></hr>
                    <p><strong>Núcleo de Informática e Telecomunicações</strong></p>
                    <p><strong>Secretaria Regional da Educação, Cultura e Desporto</strong></p>
                    <p>Paços da Junta Geral</p>
                    <p>Rua Carreira dos Cavalos</p>
                    <p>9700 – 167 Angra do Heroísmo</p>
                    <p>Telefones: 295 401 125,295 401 130,295 401 135,295 401 131, 295 401 173</p>
                    <p>Telefones VOIP GRA:310 390,310 385,310 381,310 383,310 382</p>
                    <p>E-mail GRA: sre.nit@azores.gov.pt</p>
                    <p>E-mail EDU: sre.nit@edu.azores.gov.pt</p>
                    <p>Helpdesk: <a href="https://helpdesk.edu.azores.gov.pt">https://helpdesk.edu.azores.gov.pt</a></p>
                </body>
                </html>
            """
            mail.send(msg)

            
        if admin_emails:
            # Send email notification to admins
            unique_admin_emails = set(admin_emails)
            for admin_email in unique_admin_emails:
                msg = Message(f'Helpdesk NIT: Novo ticket aberto #{ticket_id}', sender='noreply@azores.gov.pt', recipients=[admin_email])
                msg.html = f"""
                    <html>
                    <head>
                        <style>
                            /* CSS styles for email content */
                            body {{
                                font-family: Arial, sans-serif;
                                font-size: 14px;
                                line-height: 1.6;
                            }}
                            h1 {{
                                color: #333;
                            }}
                            p {{
                                margin-bottom: 10px;
                            }}
                            hr {{
                                border: 1px solid #ccc;
                                margin: 20px 0;
                            }}
                            /* Add more styles as needed */
                        </style>
                    </head>
                    <body>
                        <table role="presentation" width="100%">
                            <tr>
                                <td bgcolor="#00A4BD" align="center" style="color: white;">
                                    <h1> Novo ticket recebido!</h1>
                                </td>
                        </table>
                        <table role="presentation" border="0" cellpadding="0" cellspacing="10px" style="padding: 30px 30px 30px 60px;">
                            <tr>
                                <td>
                                    <p>Criado por: {user_name}</p>
                                    <p>Unidade organica: {uni_org}</p>
                                    <hr></hr>                           
                                    <p>Foi recebido um novo ticket com o número #<strong>{ticket_id}</strong> e com assunto <strong>{title}</strong>.</p>
                                    <p>Descrição: {description}</p>
                                </td>
                            </tr>
                        </table>
                        <p>Obrigado por usar o nosso helpdesk.</p>
                        <h3><strong>SREC-NIT</strong></h3>
                    </body>
                    </html>
                """
                mail.send(msg)


        if is_admin(user_id):
            return redirect(url_for('admin_panel'))
        else:
            return redirect(url_for('my_tickets'))

    return render_template('new_ticket.html', is_edu=is_edu,admin_status=admin_status,all_users=all_users,edu_topics_list=edu_topics_list,gra_topics_list=gra_topics_list,all_topics=all_topics,all_unidades=all_unidades)



@app.route('/my_tickets')
def my_tickets():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login page if user is not logged in

    user_id = session['user_id']
    tickets = get_user_tickets(user_id)  # Function to fetch tickets associated with the user ID
    open_tickets = get_opened_tickets_count_by_user(user_id)
    close_tickets = get_closed_tickets_count_by_user(user_id)
    executing_tickets = get_executing_tickets_count_by_user(user_id)
    all_tickets = get_all_tickets_user(user_id)



    ticket_fields = []  # List to store ticket fields

    for ticket in tickets:
        group_name = get_group_name(ticket['id'])
        attributed_name = attributed_to_by_ticket(ticket['id'])
        ticket_fields.append({
            'id': ticket['id'],  # Assuming the ticket dictionary has an 'id' field
            'date': ticket['date'],  # Replace with actual field name from the database
            'state': ticket['state'],  # Replace with actual field name from the database
            'description': ticket['description'],  # Replace with actual field name from the database
            'attributed_to': ticket['attributed_to'],  # Replace with actual field name from the database
            'title': ticket['title'],
            'group_name': group_name,
            'attributed_name': attributed_name
        })
    
    admin_status = is_admin(user_id)

    # Render the template with the tickets and admin status
    return render_template('my_tickets.html', tickets=ticket_fields, is_admin=admin_status,open_tickets=open_tickets,close_tickets=close_tickets,executing_tickets=executing_tickets,all_tickets=all_tickets)



@app.route('/send_message', methods=['POST'])
def send_message():
    ticket_id = request.form.get('ticket_id')
    message = bleach.clean(
        request.form.get('message', ''),
        tags=['p', 'strong', 'em', 'a', 'span', 'br'],
        attributes={
            'p': ['class'],
            'a': ['href']
        }
    )

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'User not logged in'}), 403

    connection = connect_to_database()
    cursor = connection.cursor()
    cursor.execute("SELECT type FROM users WHERE id = %s", (user_id,))
    user_type = cursor.fetchone()
    cursor.close()

    sender_type = user_type[0] if user_type else 'user'
    sender_name = get_username(user_id)

    file_url = None
    if 'file' in request.files:
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            app.logger.info(f"File saved to {file_path}")
            file_url = url_for('uploaded_file', filename=filename, _external=True)
            app.logger.info(f"File URL generated: {file_url}")

    cursor = connection.cursor()
    if file_url:
        cursor.execute(
            "INSERT INTO messages (ticket_id, message, sender_type, sender_name, file) VALUES (%s, %s, %s, %s, %s)",
            (ticket_id, message, sender_type, sender_name, file_url)
        )
    else:
        cursor.execute(
            "INSERT INTO messages (ticket_id, message, sender_type, sender_name) VALUES (%s, %s, %s, %s)",
            (ticket_id, message, sender_type, sender_name)
        )

    connection.commit()
    cursor.close()
    
    admin_emails = get_emails_by_group(ticket_id)

    title = get_title(ticket_id)    

    # Check if the message contains specific phrases
    if "este ticket foi aceite com sucesso." not in message.lower() and "este ticket foi fechado com sucesso." not in message.lower():
        # If the sender is an admin, send the message to the email of the ticket creator
        if sender_type == 'admin':
            ticket_creator_email = get_user_email_by_ticket(ticket_id)
            if ticket_creator_email:
                msg = Message(
                    f'Helpdesk NIT: Atualização no ticket#{ticket_id}', 
                    sender='noreply@azores.gov.pt', 
                    recipients=[ticket_creator_email]
                )
                msg.html = f"""
                    <p>Foi registada a seguinte atualização no seu ticket com o numero #<strong>{ticket_id}|{title}</strong>.</p>
                    <p>Mensagem: {message}</p>
                    <hr></hr>
                    <p><strong>Núcleo de Informática e Telecomunicações</strong></p>
                    <p><strong>Secretaria Regional da Educação, Cultura e Desporto</strong></p>
                    <p>Paços da Junta Geral</p>
                    <p>Rua Carreira dos Cavalos</p>
                    <p>9700 – 167 Angra do Heroísmo</p>
                    <p>Telefones: 295 401 125,295 401 130,295 401 135,295 401 131, 295 401 173</p>
                    <p>Telefones VOIP GRA:310 390,310 385,310 381,310 383,310 382</p>
                    <p>E-mail GRA: sre.nit@azores.gov.pt</p>
                    <p>E-mail EDU: sre.nit@edu.azores.gov.pt</p>
                    <p>Helpdesk: <a href="https://helpdesk.edu.azores.gov.pt">https://helpdesk.edu.azores.gov.pt</a></p>
                """
                mail.send(msg)
        else:
            # Send email notification to unique admin emails
            if admin_emails:
                unique_admin_emails = set(admin_emails)
                for admin_email in unique_admin_emails:
                    msg = Message(
                        f'Helpdesk NIT: Atualização no ticket#{ticket_id}', 
                        sender='noreply@azores.gov.pt', 
                        recipients=[admin_email]
                    )
                    msg.html = f"""
                        <html>
                            <head>
                                <style>
                                    /* CSS styles for email content */
                                    body {{
                                        font-family: Arial, sans-serif;
                                        font-size: 14px;
                                        line-height: 1.6;
                                    }}
                                    h1 {{
                                        color: #333;
                                    }}
                                    p {{
                                        margin-bottom: 10px;
                                    }}
                                    hr {{
                                        border: 1px solid #ccc;
                                        margin: 20px 0;
                                    }}
                                    /* Add more styles as needed */
                                </style>
                            </head>
                            <body>
                                <table role="presentation" width="100%">
                                    <tr>
                                        <td bgcolor="#00A4BD" align="center" style="color: white;">
                                            <h1>Atualização no ticket!</h1>
                                        </td>
                                </table>
                                <table role="presentation" border="0" cellpadding="0" cellspacing="10px" style="padding: 30px 30px 30px 60px;">
                                    <tr>
                                        <td>
                                            <h4>Foi registada a seguinte atualização no ticket com o numero #<strong>{ticket_id}</strong>.</h4>
                                            <p>Mensagem: {message}</p>
                                            <hr></hr>
                                        </td>
                                    </tr>
                                </table>
                                <p>Obrigado por usar o nosso helpdesk.</p>
                                <h3><strong>SREC-NIT</strong></h3>
                            </body>
                        </html>
                    """
                    mail.send(msg)

    return jsonify({'success': True, 'file_url': file_url if file_url else ''})



@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/uploads/<filename>')
def download_file(filename):
    # Safely join the upload folder and filename to prevent directory traversal
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        file_url = url_for('static', filename='uploads/' + filename)
        return jsonify({'file_url': file_url}), 200

    



def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_type') != 'admin':
            return redirect(url_for('index'))  # Redirect non-admin users to the homepage
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin_pannel')
@admin_required
def admin_panel():
    search_keyword = request.args.get('search')
    
    
    if search_keyword:
        tickets = search_tickets(search_keyword)  # Search for tickets matching the keyword
        print(tickets)
    else:
        tickets = get_all_tickets()  # Fetch all tickets from the database

    open_tickets = no_open_tickets()
    closed_tickets = no_closed_tickets()
    executing_tickets = no_execution_tickets()
    
    for ticket in tickets:
        ticket['attributed_name'] = attributed_to_by_ticket(ticket['id'])
        

    return render_template('admin_pannel.html', tickets=tickets, open_tickets=open_tickets, closed_tickets=closed_tickets, executing_tickets=executing_tickets)

@app.route('/update_group_id/<int:ticket_id>', methods=['POST'])
def update_group_id(ticket_id):
    try:
        data = request.get_json()
        group_id = data['group_id']
        update_ticket_group(group_id, ticket_id)
        return jsonify({"success": True}), 200
    except Exception as e:
        # Log the error and return an error response
        print(f"Error updating group_id for ticket {ticket_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/gerirtopicos', methods=['GET', 'POST'])
@admin_required
def topicos():
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        topics = search_topics(keyword)
        return render_template('new_forms/gerirtopicos.html', topics=topics)
    else:
        # Return None or simply render the template without passing any topics data
        return render_template('new_forms/gerirtopicos.html')


@app.route('/delete_topic/<int:topic_id>', methods=['POST'])
def delete_topic_route(topic_id):
    if request.method == 'POST':
        delete_topic(topic_id)
    return redirect(url_for('topicos'))  # Redirect to the topicos route to refresh the page


@app.route('/add_topic', methods=['POST'])
@admin_required
def add_topic():
    if request.method == 'POST':
        new_keyword = request.form.get('new_keyword')
        new_group_id = request.form.get('new_group_id')
        insert_topic(new_keyword, new_group_id)
        return redirect(url_for('topicos'))
    
@app.route('/get_topics')
def get_topics_route():
    topics = get_topics()  # Call the existing get_topics function
    print(topics)
    # Assuming topics is a list of dictionaries where each dictionary represents a topic
    return jsonify(topics)

@app.route('/new_user', methods=['GET', 'POST'])
@admin_required
def new_user():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login page if user is not logged in

    if request.method == 'POST':
        # Extract user details from the form
        name = request.form['name']
        password = request.form['password']
        type = request.form['type']
        if type == 'user':
            group = None  # For user type, group is set to None
        else:
            group = request.form.get('group_id', None)  # For admin type, group is set to the selected value
        email = request.form['email']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # Here, you would add code to insert the new user into the database
        try:
            conn = connect_to_database()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (name, password, type, group_id, email) VALUES (%s, %s, %s, %s, %s)",
                            (name, hashed_password, type, group, email))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('admin_init'))  # Redirect to dashboard after user creation
        except Exception as e:
            print("Error creating user:", e)
            return "Error creating user. Please try again later."

    # Render the form for adding a new user
    return render_template('new_forms/novo_utilizador.html')


@app.route('/change_password', methods=['POST'])
def change_user_password():
    email = request.form['email_change']
    
    # Call the change_password function to update the user's password
    change_pass = change_password(email)
    
    # Provide feedback to the user
    flash('Password alterada para password%100 para o utilizador com o email: {}'.format(email))
    
    return redirect(url_for('new_user'))


@app.route('/pannel_group')
def group_panel():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login page if user is not logged in

    user_id = session['user_id']
    # Fetch the group_id associated with the user
    group_id = get_user_group(user_id)
    # Fetch tickets based on the group_id
    tickets = get_all_tickets_group(group_id)
    closed_tickets = get_closed_tickets_count_by_group(group_id)
    opened_tickets = get_opened_tickets_count_by_group(group_id)
    executing_tickets = get_executing_tickets_count_by_group(group_id)
    
    return render_template('pannel_group.html', tickets=tickets,closed_tickets=closed_tickets,opened_tickets=opened_tickets,executing_tickets=executing_tickets)

@app.route('/pannel_personal')
def personal_panel():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login page if user is not logged in

    user_id = session['user_id']
    # Fetch the group_id associated with the user
    tickets = get_tickets_for_user(user_id)
    user_name = get_username(user_id)
    closed_tickets = get_closed_tickets_count_by_admin(user_name)
    opened_tickets = get_opened_tickets_count_by_user(user_id)
    executing_tickets = count_executing_tickets_admin(user_name)
    return render_template('personal_pannel.html', tickets=tickets,closed_tickets=closed_tickets,opened_tickets=opened_tickets,executing_tickets=executing_tickets)


@app.route('/ticket_details/<int:ticket_id>')
def ticket_details(ticket_id):
    user_id = session.get('user_id')
    
    conn = connect_to_database()
    cursor = conn.cursor()

    # Fetch the user who created the ticket
    cursor.execute("SELECT u.name FROM users u JOIN tickets t ON u.id = t.created_by WHERE t.id = %s", (ticket_id,))
    user_tuple = cursor.fetchone()
    if user_tuple:
        user_name = user_tuple[0]  # Access the first element of the tuple
    else:
        user_name = None  # or any default value you want

    # Fetch ticket details
    ticket_details = get_ticket_details(ticket_id)
    #print((ticket_details['closed_by']))
    
    # # Get the username for closed_by field
    # if ticket_details.get('closed_by'):
    #     ticket_details['closed_by'] = get_username(ticket_details['closed_by'])

    # # Handle other fields similarly if needed
    # if ticket_details.get('accepted_by'):
    #     ticket_details['accepted_by'] = get_username(ticket_details['accepted_by'])
    
    # if ticket_details.get('reopened_by'):
    #     ticket_details['reopened_by'] = get_username(ticket_details['reopened_by'])

    cursor.close()
    conn.close()
    
    admin_status = is_admin(user_id)

    return render_template('ticket_details.html', ticket_details=ticket_details, is_admin=admin_status, user_name=user_name)


@app.route('/close_ticket/<int:ticket_id>', methods=['POST'])
def close_ticket_route(ticket_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'User not logged in'}), 401

    try:
        user_id = session['user_id']
        
        # Perform the ticket closure logic
        close_ticket(user_id, ticket_id)
        
        # Get the current time when the ticket is closed
        closed_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        update_ticket_close_time(ticket_id,closed_time)
        
        # Send an email to the user
        user_email = get_user_email_by_ticket(ticket_id)
        if user_email:
            msg = Message(f'Helpdesk NIT: Ticket fechado #{ticket_id}', sender='noreply@azores.gov.pt', recipients=[user_email])
            msg.html = f"""
                <h2>O seu ticket com o número #{ticket_id} foi concluído com sucesso.</h2>
                <hr></hr>
                <p><strong>Núcleo de Informática e Telecomunicações</strong></p>
                <p><strong>Secretaria Regional da Educação, Cultura e Desporto</strong></p>
                <p>Paços da Junta Geral</p>
                <p>Rua Carreira dos Cavalos</p>
                <p>9700 – 167 Angra do Heroísmo</p>
                <p>Telefones: 295 401 125, 295 401 130, 295 401 135, 295 401 131, 295 401 173</p>
                <p>Telefones VOIP GRA: 310 390, 310 385, 310 381, 310 383, 310 382</p>
                <p>E-mail GRA: sre.nit@azores.gov.pt</p>
                <p>E-mail EDU: sre.nit@edu.azores.gov.pt</p>
                <p>Helpdesk: <a href="https://helpdesk.edu.azores.gov.pt">https://helpdesk.edu.azores.gov.pt</a></p>
            """
            mail.send(msg)
        
        return jsonify({'success': True, 'closed_time': closed_time})

    except Exception as e:
        # Log the exception and return an error message as JSON
        print(f"Error closing ticket: {e}")
        return jsonify({'success': False, 'error': str(e)})





@app.route('/reopen_ticket/<int:ticket_id>', methods=['POST'])
def reopen_ticket_route(ticket_id):
    reopen_ticket(ticket_id)

    return jsonify({'success': True})

@app.route('/accept_ticket/<int:ticket_id>', methods=['POST'])
def accept_ticket_route(ticket_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    claim_ticket(user_id, ticket_id)
    attributed_to(user_id)

    # Get the current time and update the ticket with this time
    accept_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    update_ticket_accept_time(ticket_id, accept_time)

    user_email = get_user_email_by_ticket(ticket_id)
    if user_email:
        msg = Message(f'Helpdesk NIT: Ticket aceite #{ticket_id}', sender='noreply@azores.gov.pt', recipients=[user_email])
        msg.html = f"""
            <h2>O seu ticket com o número #{ticket_id} foi aceite e encontra-se neste momento em execução.</h2>
            <hr></hr>
            <p><strong>Núcleo de Informática e Telecomunicações</strong></p>
            <p><strong>Secretaria Regional da Educação, Cultura e Desporto</strong></p>
            <p>Paços da Junta Geral</p>
            <p>Rua Carreira dos Cavalos</p>
            <p>9700 – 167 Angra do Heroísmo</p>
            <p>Telefones: 295 401 125,295 401 130,295 401 135,295 401 131, 295 401 173</p>
            <p>Telefones VOIP GRA:310 390,310 385,310 381,310 383,310 382</p>
            <p>E-mail GRA: sre.nit@azores.gov.pt</p>
            <p>E-mail EDU: sre.nit@edu.azores.gov.pt</p>
            <p>Helpdesk: <a href="https://helpdesk.edu.azores.gov.pt">https://helpdesk.edu.azores.gov.pt</a></p>
        """
        mail.send(msg)

    return jsonify({'success': True, 'message': 'Este ticket foi aceite com sucesso', 'accept_time': accept_time})






@app.route('/accountform')
def create_accountEDU_page():
    return render_template('/new_forms/create_accountform.html')



@app.route('/dump_database', methods=['POST'])
def dump_database():
    selected_items = {
        'users': [],
        'tickets': []
        # Uncomment and add more tables as needed
        # 'topics': [],
        # 'groups': []
    }

    # Check which fields have been selected for each table
    for item in selected_items.keys():
        if request.form.get(item) == item:
            if request.form.get('id') == 'id':
                selected_items[item].append('id')
            if item == 'users':
                if request.form.get('name') == 'name':
                    selected_items[item].append('name')
                if request.form.get('email') == 'email':
                    selected_items[item].append('email')
                if request.form.get('created_at') == 'created_at':
                    selected_items[item].append('created_at')
                if request.form.get('group_id') == 'group_id':
                    selected_items[item].append('group_id')
                if request.form.get('type') == 'type':
                    selected_items[item].append('type')
            elif item == 'tickets':
                if request.form.get('title') == 'title':
                    selected_items[item].append('title')
                if request.form.get('description') == 'description':
                    selected_items[item].append('description')
                if request.form.get('created_by_user') == 'created_by_user':
                    selected_items[item].append('created_by_user')
                if request.form.get('state') == 'state':
                    selected_items[item].append('state')
                if request.form.get('closed_by') == 'closed_by':
                    selected_items[item].append('closed_by')

    if all(len(fields) == 0 for fields in selected_items.values()):
        return "Nenhum item selecionado para exportar."

    # Define the CSV file name and path
    file_name = "database_dump.csv"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)

    # Run the SELECT queries and write to CSV
    with open(file_path, mode='w', newline='') as f:
        for table, fields in selected_items.items():
            if fields:
                select_string = ", ".join(fields)
                query = f"SELECT {select_string} FROM {table}"
                dump_command = [
                    'mysql',
                    '-u', 'root',
                    '-ppassroot',  # Note: No space between -p and password
                    'helpdesk4',
                    '--batch',
                    '--silent',
                    '-e', query
                ]
                try:
                    result = subprocess.run(dump_command, stdout=f, stderr=subprocess.PIPE, text=True, check=True)
                except subprocess.CalledProcessError as e:
                    error_message = f"Error executing command: {e}\n{e.stderr}"
                    return error_message

    return send_file(file_path, as_attachment=True)
if __name__ == '__main__':
    app.run(debug=True)

