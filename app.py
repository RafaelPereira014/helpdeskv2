import csv
import datetime
import bleach
from functools import wraps
import secrets
import os
import subprocess
from flask_caching import Cache
from flask import Flask, flash, jsonify, render_template, request, redirect, send_from_directory, url_for
import requests
from db_operations import *
from more_operations import *
from flask import session
from flask import redirect
from datetime import datetime
from flask import request
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from flask import render_template
from flask import send_file
from config import DB_CONFIG
from config import Config

app = Flask(__name__)
# Generate a secure secret key


app.secret_key = secrets.token_bytes(16)
app.config.from_object(Config)
cache = Cache(app)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
mail=Mail(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']




connection = pymysql.connect(**DB_CONFIG)

def cache_ticket_count(cache_key, func):
    count = func()
    cache.set(cache_key, count, timeout=7200)  # Cache for 2 hours

    return count

@app.route('/')
def index():
    return render_template('login.html')
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_type') != 'admin':
            return redirect(url_for('index'))  # Redirect non-admin users to the homepage
        return f(*args, **kwargs)
    return decorated_function

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

@app.route('/get_unidades/<ilha_id>', methods=['GET'])
def get_unidades(ilha_id):
    conn = connect_to_database()
    cursor = conn.cursor()
    query = """
        SELECT id, name 
        FROM unidadesorganicas 
        WHERE ilha_id = %s 
        ORDER BY name ASC
    """
    cursor.execute(query, (ilha_id,))
    unidades = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Return data as JSON for the frontend to use
    return jsonify([{'id': unidade[0], 'name': unidade[1]} for unidade in unidades])

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
    all_ilhas = get_all_ilhas()
    gra_divisoes = get_all_gra()
    admin_unidades = sorted(all_unidades + gra_divisoes)
    material_types = get_material_types()

    

    if request.method == 'POST':
        topic_id = request.form['topic_id']
        description = request.form['description']
        state = "Aberto"
        uni_org = request.form['UnidadeOrg']
        if uni_org.isdigit():
            uni_org = get_unidade_name_by_id(int(uni_org))  # Convert to integer to query the DB
            
        date = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        contacto = request.form['contacto']
        title = request.form['title']
        assigned_to = request.form.get('assigned_to')
        material_type = request.form.getlist('material_type')
        material_quantity = request.form.getlist('quantity_type')
        quantidade = '1'
        motivo = 'Requisição'
        data_inicio = request.form.get('start_date')
        data_fim = request.form.get('end_date')
        
        if assigned_to:
            created_by = get_user_id_by_name(assigned_to)
            user_name = get_username(created_by)
        else:
            created_by = session.get('user_id')
            user_name = get_username(created_by)
            
        
        # Check if file is uploaded
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join('static/uploads', filename)  # Define your upload folder
                file.save(file_path)
                
            else:
                filename = "Sem ficheiro."
        else:
            filename = "Sem ficheiro."
        
        #description = clean_description(description)
       
        

        create_ticket(topic_id, description, date, state, created_by, contacto, title, uni_org, filename)
        
        
        ticket_id = get_ticketid(description)
        user_email = get_user_email_by_user(created_by)
        admin_emails = get_emails_by_group(ticket_id)
        topico = get_topic_name(topic_id)
         
       
        data_to_send = {
            'ID': ticket_id,
            'User': user_name,
            'User email': user_email,
            'material_type': material_type,
            'quantity': material_quantity,
            'quantidade': quantidade,
            'motivo': motivo,
            'data_inicio': data_inicio,
            'data_fim': data_fim
        }
        print(data_to_send)

        
        #api_url = 'http://172.22.130.12:8081/receive-data'  
        api_url = 'http://127.0.0.1:8081/receive-data'  
        try:
            response = requests.post(api_url, json=data_to_send)
            if response.status_code == 200:
                print("Data successfully sent to /receive-data")
            else:
                print(f"Error sending data: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
        
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
                    <p>Poderá, a qualquer momento, acompanhar em <a href="https://helpdesk.edu.azores.gov.pt/{ticket_id}">https://helpdesk.edu.azores.gov.pt/{ticket_id}</a> a evolução do seu pedido:</p>
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
                                    <p><strong>Criado por:</strong> {user_name}</p>
                                    <p><strong>Tópico:</strong> {topico}</p>
                                    <p><strong>Unidade orgânica:</strong> {uni_org}</p>
                                    <hr></hr>                           
                                    <p>Foi recebido um novo ticket com o número #<strong><a href="https://helpdesk.edu.azores.gov.pt/ticket_details/{ticket_id}" target="_blank">{ticket_id}</a></strong> e com assunto <strong>{title}</strong>.</p>
                                    <p><strong>Descrição:</strong> {description}</p>
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

    return render_template('new_ticket.html', 
            is_edu=is_edu,
            admin_status=admin_status,
            all_users=all_users,
            edu_topics_list=edu_topics_list,
            gra_topics_list=gra_topics_list,
            all_topics=all_topics,
            all_unidades=all_unidades,
            all_ilhas=all_ilhas,
            gra_divisoes=gra_divisoes,
            admin_unidades=admin_unidades,
            material_types = material_types)



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

    

    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO messages (ticket_id, message, sender_type, sender_name) VALUES (%s, %s, %s, %s)",
        (ticket_id, message, sender_type, sender_name)
    )

    connection.commit()
    cursor.close()
    
    admin_emails = get_emails_by_group(ticket_id)

    title = get_title(ticket_id)
    criado_por = get_creator_name(ticket_id)
    unidade_org = get_unidadeOrg(ticket_id)
    attributed_user = attributed_to_by_ticket(ticket_id)
    info = get_ticket_details(ticket_id)
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
                    <p>Poderá, a qualquer momento, acompanhar em <a href="https://helpdesk.edu.azores.gov.pt/{ticket_id}">https://helpdesk.edu.azores.gov.pt/{ticket_id}</a> a evolução do seu pedido:</p>
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
            if info.get('state') == 'Fechado':
                cursor = connection.cursor()
                cursor.execute("UPDATE tickets SET state = 'em execucao' WHERE id = %s", (ticket_id,))
                connection.commit()
                cursor.close()
            
            print(attributed_user)
            
            if attributed_user is None :
                cursor = connection.cursor()
                cursor.execute("UPDATE tickets SET state = 'Aberto' WHERE id = %s", (ticket_id,))
                connection.commit()
                cursor.close()
                attributed_user = "-"
                
            
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
                                            <h4>Foi registada a seguinte atualização no ticket com o numero 
                                                #<strong><a href="https://helpdesk.edu.azores.gov.pt/ticket_details/{ticket_id}" target="_blank">{ticket_id}</a></strong>.
                                            </h4>
                                            <p><strong>Criado por</strong>: {criado_por}</p>
                                            <p><strong>Unidade Orgânica</strong>: {unidade_org}</p>
                                            <p><strong>Atribuido a</strong>: {attributed_user}</p>
                                            <p><strong>Mensagem</strong>: <br>{message}</p>
                                            
                                            <hr>
                                        </td>
                                    </tr>
                                </table>
                                <p>Obrigado por usar o nosso helpdesk.</p>
                                <h3><strong>SREC-NIT</strong></h3>
                            </body>
                        </html>
                    """
                    mail.send(msg)

    return jsonify({'success': True})



@app.route('/upload', methods=['POST'])
def upload_file():
    user_id = session.get('user_id')
    ticket_id = request.form.get('ticket_id')  # Get the ticket ID from the form submission

    # Ensure user is authenticated
    if not user_id:
        return {"success": False, "message": "Unauthorized"}, 401

    # Validate and process the uploaded file
    file = request.files.get('uploaded_file')
    if not file:
        return {"success": False, "message": "No file uploaded"}, 400

    if file and allowed_file(file.filename):  # Validate file type
        filename = secure_filename(file.filename)
        file_path = os.path.join('static/uploads', filename)  # Define your upload folder
        file.save(file_path)  # Save the file

        # Insert file metadata into the database
        insert_files_ticket(ticket_id, user_id, datetime.now(), filename)

        return {"success": True, "message": "File uploaded successfully"}, 200
    else:
        return {"success": False, "message": "Invalid file type"}, 400
    
@app.route('/get_files/<int:ticket_id>')
def get_files(ticket_id):
    # Connect to the database
    conn = connect_to_database()
    cursor = conn.cursor()

    # Fetch stored files for the specific ticket
    cursor.execute("SELECT file_url FROM anexos WHERE ticket_id = %s", (ticket_id,))
    files = cursor.fetchall()

    cursor.close()
    conn.close()

    # Return the file list as JSON
    return {"files": [file[0] for file in files]}  # Assuming filename is the first column

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/remove_file/<int:ticket_id>', methods=['POST'])
@admin_required
def remove_file(ticket_id):
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    data = request.get_json()
    filename = data.get('filename')
    
    if not filename:
        return jsonify({"success": False, "message": "No filename provided"}), 400

    # Remove file from the file system
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    else:
        return jsonify({"success": False, "message": "File not found"}), 404

    # Remove the file entry from the database
    try:
        conn = connect_to_database()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM anexos WHERE ticket_id = %s AND file_url = %s", (ticket_id, filename))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"success": True, "message": "File removed successfully"})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500




@app.route('/admin_pannel')
@admin_required
def admin_panel():
    search_keyword = request.args.get('search')
    
    if search_keyword:
        tickets = search_tickets(search_keyword)  # Search for tickets matching the keyword
    else:
        tickets = get_all_tickets()  # Fetch all tickets from the database

    # Compute and cache ticket counts
    open_tickets = cache_ticket_count('open_tickets', no_open_tickets)
    closed_tickets = cache_ticket_count('closed_tickets', no_closed_tickets)
    executing_tickets = cache_ticket_count('executing_tickets', no_execution_tickets)
    
    for ticket in tickets:
        # Retrieve attributed name
        ticket['attributed_name'] = attributed_to_by_ticket(ticket['id'])

    return render_template(
        'admin_pannel.html',
        tickets=tickets,
        open_tickets=open_tickets,
        closed_tickets=closed_tickets,
        executing_tickets=executing_tickets
    )

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
    if request.method == 'GET':
        visible_topics = get_topics(visible=True)
        invisible_topics = get_topics(visible=False)
        
        return render_template('new_forms/gerirtopicos.html', 
                               visible_topics=visible_topics, 
                               invisible_topics=invisible_topics)
    else:
        visible_topics = get_topics(visible=True)
        invisible_topics = get_topics(visible=False)
        
    
        return render_template('new_forms/gerirtopicos.html', 
                               visible_topics=visible_topics, 
                               invisible_topics=invisible_topics)
        
@app.route('/gerir_utilizadores', methods=['GET', 'POST'])
@admin_required
def gerir_utilizadores():
    if request.method == 'GET':
        visible_users = get_users(visible=True)
        invisible_users = get_users(visible=False)
    
        return render_template('new_forms/gerir_utilizadores.html', 
                               visible_users=visible_users, 
                               invisible_users=invisible_users)
    else:
        visible_users = get_users(visible=True)
        invisible_users = get_users(visible=False)
    
        return render_template('new_forms/gerir_utilizadores.html', 
                               visible_users=visible_users, 
                               invisible_users=invisible_users)

@app.route('/toggle_topic_visibility_on/<int:topic_id>', methods=['POST'])
def toggle_visibility_on(topic_id):
    if request.method == 'POST':
        visible(topic_id)
    return redirect(url_for('topicos'))  

@app.route('/toggle_topic_visibility_off/<int:topic_id>', methods=['POST'])
def toggle_visibility_off(topic_id):
    if request.method == 'POST':
        invisible(topic_id)
    return redirect(url_for('topicos')) 

@app.route('/toggle_user_visibility_on/<int:user_id>', methods=['POST'])
def toggle_user_visibility_on(user_id):
    if request.method == 'POST':
        user_visible(user_id)
    return redirect(url_for('gerir_utilizadores'))  

@app.route('/toggle_user_visibility_off/<int:user_id>', methods=['POST'])
def toggle_user_visibility_off(user_id):
    if request.method == 'POST':
        user_invisible(user_id)
    return redirect(url_for('gerir_utilizadores')) 

@app.route('/edit_user_name/<int:user_id>', methods=['POST'])
def edit_user_name(user_id):
    if request.method == 'POST':
        new_name = request.form['new_name']  # Get the new name from the form
        update_user_name(new_name, user_id)  # Update the user's name in the database

    
    return redirect(url_for('gerir_utilizadores'))

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

    error_message = None

    if request.method == 'POST':
        # Extract user details from the form
        name = request.form['name']
        password = request.form['password']
        user_type = request.form['type']
        group = request.form.get('group_id', None) if user_type == 'admin' else None
        email = request.form['email']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # Check if the user already exists
        try:
            conn = connect_to_database()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()

            if existing_user:
                error_message = "Atenção,o utilizador já existe com este email!"
            else:
                # Insert the new user into the database
                cursor.execute(
                    "INSERT INTO users (name, password, type, group_id, email) VALUES (%s, %s, %s, %s, %s)",
                    (name, hashed_password, user_type, group, email)
                )
                conn.commit()
                return redirect(url_for('admin_init'))  # Redirect to dashboard after user creation

            cursor.close()
            conn.close()
        except Exception as e:
            print("Error creating user:", e)
            error_message = "Erro ao criar utilizador. Tente novamente mais tarde."

    # Render the form for adding a new user, passing the error message (if any)
    return render_template('new_forms/adicionar_utilizador.html', error_message=error_message)

@app.route('/change_password', methods=['GET', 'POST'])
@admin_required
def change_user_password():
    if request.method == 'GET':
        return render_template('new_forms/alterar_password.html')  # Serve the form page

    if request.method == 'POST':
        email = request.form.get('email_change')
        success = change_password(email)
        if success:
            flash(f'✅ Password do utilizador com o email: {email} alterada com sucesso.', 'success')
        else:
            flash(f'❌ Não foi possível alterar a password do utilizador com o email: {email}', 'error')
        
        return render_template('new_forms/alterar_password.html')



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
    
    for ticket in tickets:
        # Get the latest ticket message
        info = get_latest_ticket_message(ticket['id'])

        # Add sent_from_user property to the ticket
        ticket['sent_from_user'] = False  # Default value

        # Check if info exists and sender_type is 'user'
        if info and info.get('sender_type') == 'user':
            ticket['sent_from_user'] = True
        
        print(ticket['sent_from_user'])
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
    
    
    if ticket_details and ticket_details.get('description'):
        ticket_details['description'] = clean_description(ticket_details['description'])
        
    no_anexos = count_files_ticket(ticket_id)
    

    cursor.close()
    conn.close()
    
    admin_status = is_admin(user_id)
    id_topico = get_topic_id(ticket_id)
    topico = get_topic_name(id_topico)

    return render_template('ticket_details.html', ticket_details=ticket_details, is_admin=admin_status, user_name=user_name,topico=topico,no_anexos=no_anexos)


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
        
        send_ticket_message(ticket_id,"Este Ticket foi fechado com sucesso.",'admin',attributed_to(user_id),closed_time,None)

        
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
    
    
    send_ticket_message(ticket_id,"Este Ticket foi aceite com sucesso.",'admin',attributed_to(user_id),accept_time,None)
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
    app.run(debug=True,host='0.0.0.0',port=8080)