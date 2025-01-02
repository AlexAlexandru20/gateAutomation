from flask import Blueprint, request, redirect, url_for, flash, render_template, send_from_directory, send_file, jsonify, current_app, g
from flask import session as sesiune
from flask_login import login_required, current_user
from sqlalchemy import text
from . import connectDB, enterDetails, sendMail, format_datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from validate_email_address import validate_email
import qrcode, os, random, string, uuid, shutil, json
import pandas as pd


import_db = Blueprint('import', __name__)

def returningEvents():
    from .models import Events
    with connectDB() as session:
        events = []
        events_entry = session.query(Events).filter(
            Events.user_id == current_user.id,
            Events.end >= datetime.now()
        ).order_by(Events.start.asc(), Events.end.asc()).all()
        if events_entry:
            for event in events_entry:
                event_start = format_datetime(event.start)
                event_end = format_datetime(event.end)
                if 'T' in event.start:
                    event_data = {
                        'id': event.id,
                        'title': event.title,
                        'start': event_start['month'],
                        'end': event_end['month'],
                        'start_time': event_start['time'],
                        'end_time': event_end['time'],
                        'weekDayStart': event_start['weekDay'],
                        'weekDayEnd': event_end['weekDay'] 
                    }
                else:
                    event_data = {
                        'id': event.id,
                        'title': event.title,
                        'start': event_start['month'],
                        'end': event_end['month'],
                        'weekDayStart': event_start['weekDay'],
                        'weekDayEnd': event_end['weekDay'] 
                    }
                events.append(event_data)
        return events


#Aranjare Input
def clean_input(input_string):
    cleaned_string = input_string.strip()

    words_list = cleaned_string.split()

    cleaned_string = ' '.join(words_list)

    return cleaned_string

# Inregistrare Scoala
@import_db.route('/school-form-login', methods=['POST', 'GET'])
def schoolForm():
    from .models import schoolsRequests

    with connectDB() as session:
        if request.method == 'POST':
            data = request.get_json()
            new_school = schoolsRequests(school_name = data.get('name'), short = str(data.get('short')).upper(), address = data.get('address'), email = data.get('email'), phone = data.get('phone'))
            body = 'Am primit cererea de înregistrare, vom revenii cu detalii la numărul de telefon trimis.'
            
            email_entry = session.query(schoolsRequests).filter_by(email = data.get('email')).first()

            if email_entry:
                return jsonify({'message': 'existed'}), 200
            
            try:
                session.add(new_school)
                session.commit()
                if not sendMail(data.get('email'), 'Cerere Înregistrare', body):
                    print('Error at sending mail')
                return jsonify({'message': 'success'}), 200
            
            except Exception as e:
                session.rollback()
                print(f'S-a produs o eroare: {str(e)}', category='alert')
                return jsonify(), 500
            
            finally:
                session.close()
    return render_template('hero.html', page_name = 'Inregistrare')


#Modificare Setari Scoala
@import_db.route('/change_school', methods=['POST', 'GET'])
@login_required
def change_school():
    from .models import Schools
    school = Schools.query.get_or_404(current_user.school_id)

    events = returningEvents()

    if request.method == 'POST':
        with connectDB() as session:
            address = request.form.get('schoolAdresa')
            email = request.form.get('schoolEmail')
            phone = request.form.get('schoolPhone')

            school_entry = session.query(Schools).filter_by(id=current_user.school_id).first()
            email_check = session.query(Schools).filter_by(email=email).first()


            if address and address != school_entry.adresa:
                school_entry.adresa = address
            if email and email != school_entry.email:
                if not email_check:
                    school_entry.email = email
                else:
                    flash('Emailul este utilizat!', category='alert')
                    redirect(url_for('import.change_school'))
            if phone and phone != school_entry.phone:
                school_entry.phone = phone

            try:
                session.commit()
                if not enterDetails(current_user.id, f'Changed details for school {school_entry.school_name} - ID: {current_user.school_id}'):
                    print('Error with details DB - school modify section')
                flash('Modificari aduse cu success', category='success')
            except Exception as e:
                session.rollback()
                flash(f'Error: {e}', category='alert')
            finally:
                session.close()
    return render_template('forms.html', events=events, page_name = f'{current_user.prenume} {current_user.nume}', school=school)


#Adaugare user nou
@import_db.route('/add_user', methods=['POST', 'GET'])
@login_required
def add_user():
    events = returningEvents()
    if request.method == 'POST':
        from .models import User, Schools
        with connectDB() as session:
            name = clean_input(request.form.get('user_name'))
            sndname = clean_input(request.form.get('user_sndname'))
            address = request.form.get('user_address')
            email = clean_input(request.form.get('user_email'))
            phone = clean_input(request.form.get('user_phone'))
            role = request.form.get('rolSelect').lower()
            calificare = request.form.get('calificareSelect').lower()
            userType = request.form.get('user_type').lower()
            
            #choose only first name if it's more
            sndparts = sndname.split()
            first_sndname = sndparts[0] if sndparts else ''

            #choose only first second name if it's more
            frsparts = name.split()
            first_name = frsparts[0] if frsparts else ''


            usernames = [f'{first_name}{random.randint(0, 100)}{first_sndname}']
            chosen_username = random.choice(usernames)
            password = generate_password_hash(f'{name}01', method='pbkdf2:sha256')

            school_id = current_user.school_id

            user_check = session.query(User).filter_by(username=chosen_username).first()

            if not user_check:
                user = session.query(User).filter_by(email=email).first()
                if user:
                    flash('User existent.', category='alert')
                    return redirect(url_for('import.change', user_id=user.id))

                school_entry = session.query(Schools).filter_by(id=school_id).first()

                if school_entry:
                    school_entry.pers += 1

                    if calificare == 'director':
                        school_entry.director = f'{name} {sndname}'
                    short = school_entry.short
                    id = generateRefId(short)

                    new_user = User(id=id, nume=name, prenume=sndname, email=email, username=chosen_username, password=password, rol=role, telefon=phone, adresa=address, calificare=calificare if role != 'elev' else '', clasa = calificare if role == 'elev' else '', school_id=school_id, time=datetime.now(), tipElev=userType)

                    session.add(new_user)
                    body = f'Username: {chosen_username} \nParola: {name}01\nLink de conectare: 127.0.0.1:5000'

                    try:
                        session.commit()
                        if not sendMail(email, 'Detalii conectare', body):
                            flash('S-a produs o eroare!', category='alert')
                        if not enterDetails(current_user.id, f'added a user: {name} {sndname}'):
                            print('Error with Details DB - add user section')
                        flash('User adaugat cu succes', category='success')
                    except Exception as e:
                        session.rollback()
                        print(f'Error: {e}')
                        flash(f'S-a produs o eroare: {e}', category='alert')
                    finally:
                        session.close()
            else:
                flash('Username existent!', category='alert')
    return render_template('forms.html', events=events, page_name=f'{current_user.prenume} {current_user.nume}')


#Modificare user
@import_db.route('/change/<user_id>', methods=['POST', 'GET'])
@login_required
def change(user_id):
    from .models import User
    #verificare existenta user
    user_check = User.query.get_or_404(user_id)
    if user_check:
        user = {
            'id': user_check.id,
            'nume': user_check.nume,
            'prenume': user_check.prenume,
            'email': user_check.email,
            'telefon': user_check.telefon,
            'adresa': user_check.adresa,
            'rol': str(user_check.rol).capitalize(),
            'calificare': str(user_check.calificare).capitalize()
        }
    events = returningEvents()
    if request.method == 'POST':
        name = request.form.get('inputName')
        sndname = request.form.get('inputSndname')
        email = request.form.get('inputEmail')
        phone = request.form.get('inputTelefon')
        address = request.form.get('inputAddress')
        rol = request.form.get('rolSelectChange')
        calificare = request.form.get('calificareSelectChange')

        body = 'S-au adus următorele modificări acestui user: \n'

        with connectDB() as session:
            id_check = session.query(User).filter_by(id=user_id).first()
            email_check = session.query(User).filter_by(email=email).first()

            if id_check:
                if name and name != id_check.nume:
                    id_check.nume = name
                    body += f'Numele => {name} \n'
                if sndname and sndname != id_check.prenume:
                    id_check.prenume = sndname
                    body += f'Prenumele => {sndname} \n'
                if email and email != id_check.email:
                    if not email_check:
                        id_check.email = email
                        body += f'Email => {email} \n'
                    else: 
                        flash('Email existent', category='alert') 
                        return redirect(url_for('import.change', user_id = user_id))
                if phone and phone != id_check.telefon:
                    id_check.telefon = phone
                    body += f'Telefon => {phone} \n'
                if address and address != id_check.adresa:
                    id_check.adresa = address
                    body += f'Adresa => {address} \n'
                if rol and rol != id_check.rol:
                    id_check.rol = rol.lower()
                    body += f'Rolul in școală => {rol} \n'
                if calificare and calificare != id_check.calificare:
                    id_check.calificare = calificare.lower()
                    body += f'Rolul în școală => {calificare} \n'

                try:
                    session.commit()
                    if not enterDetails(current_user.id, f'modify user\'s ~{user_id}~ settings'):
                        print('Error with details DB - user modify section')

                    if not sendMail(email, 'Modificari user', body):
                        print('Error sending  mail')

                    return jsonify(), 200
                except Exception as e:
                    session.rollback()
                    flash(f's-a produs o eroare: {e}', category='alert')
                    return jsonify(), 500

    return render_template('forms.html', user=user, events = events)


#Stergere user
@import_db.route('/delete_user/<user_id>', methods=['POST', 'GET'])
@login_required
def delete(user_id):
    from .models import User, Schools, Inventar

    with connectDB() as session:
        try:
            user = session.query(User).filter_by(id=user_id).first()

            if user:
                deleted_user_id = user.id
                deleted_user_name = f'{user.nume} {user.prenume}'

                school_entry = session.query(Schools).filter_by(id=current_user.school_id).first()
                inventar_entries = session.query(Inventar).filter_by(user_id=user.id).all()

                if school_entry:
                    school_entry.pers -= 1

                if inventar_entries:
                    for inventar_entry in inventar_entries:
                        file = f'{inventar_entry.uniqueid}.png'
                        file_path = os.path.join('website', 'static', 'images', 'qrcodes', file)

                        try:
                            session.delete(inventar_entry)
                            os.remove(file_path)
                        except Exception as e:
                            print(f'Error: {e}')
                            session.rollback()

                session.delete(user)
                session.commit()

                if not enterDetails(current_user.id, f'deleted user {deleted_user_name}'):
                    print('Error with details DB - delete user section')

                flash('User deleted.', category='success')

        except Exception as e:
            session.rollback()
            flash(f'An error occurred: {e}', category='alert')

    return redirect(url_for('views.allUsers'))


#Stergere itemi multipli
@import_db.route('/delete-multiple', methods=['POST'])
@login_required
def deleteMultiple():
    try:
        data = request.get_json()
        urlType = data.get('url_type', '')

        #Delete User Logic
        if urlType == 'users':
            user_ids = data.get('user_ids', [])
            if deleteUsers(user_ids):
                flash('Useri stersi', category='success')
                return jsonify({'message': 'Successfully deleted users'}), 200
            else:
                return jsonify({'error'}), 500
        
        #Delete Inventar Logic
        if urlType == 'inventar':
            inv_ids = data.get('inv_ids', [])
            if deleteInventar(inv_ids):
                return jsonify({'message': 'Successfully deleted users'}), 200
            else:
                return jsonify({'error'}), 500

        #Files remover
        elif urlType == 'file':
            files_details = data.get('user_ids', [])
            if deleteFiles(files_details):
                flash('Fisiere sterse', category='success')
                return jsonify({'message': 'Successfully deleted users'}), 200
            else:
                return jsonify({'error'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#users Delete Logic
def deleteUsers(user_ids):
    from .models import User, Schools, Inventar
    try:
        user_name = ''
        with connectDB() as session:
            school_entry = session.query(Schools).filter_by(id=current_user.school_id).first()
            if school_entry:
                for user_id in user_ids:
                    user_entry = session.query(User).filter_by(id=user_id).first()
                    user_name = f'{user_entry.nume} {user_entry.prenume}'
                    if user_entry:
                        try:
                            session.delete(user_entry)
                            session.commit()
                        except Exception as e:
                            session.rollback()
                            print(f'Error deleting user: {e}')
                            return False

                    school_entry.pers -= 1

                    try:
                        session.commit()
                    except Exception as e:
                        session.rollback()
                        print(f'Error updating school data: {e}')
                        return False

                    inventar_entries = session.query(Inventar).filter_by(user_id=user_id).all()
                    if inventar_entries:
                        for inventar_entry in inventar_entries:
                            unique_id = inventar_entry.uniqueid
                            print(unique_id)
                            try:
                                session.delete(inventar_entry)
                                session.commit()
                            except Exception as e:
                                session.rollback()
                                print(f'Error deleting inventory entry: {e}')
                if not enterDetails(current_user.id, f'deleted users: {user_name}'):
                    print('Error')
                return True
    except Exception as e:
        print(f'Error: {e}')
        return False


#Delete Inventar Logic
def deleteInventar(inv_ids):
    from .models import Inventar
    try:
        with connectDB() as session:
            for inv_id in inv_ids:
                inventar_entry = session.query(Inventar).filter_by(uniqueid=inv_id).first()

                if inventar_entry:
                    try:
                        session.delete(inventar_entry)
                        session.commit()
                    except Exception as e:
                        session.rollback()
                        print(f'Error deleting inventory entry: {e}')
                        return False

                file = f'{inv_id}.png'
                file_path = os.path.join('website', 'static', 'images', 'qrcodes', file)

                try:
                    os.remove(file_path)
                    if not enterDetails(current_user.id, f'deleted inventory object: {inv_id}'):
                        print('Error entering details')
                except Exception as e:
                    print(f'Error deleting file or entering details: {e}')
                    return False

            return True  

    except Exception as e:
        print(f'Error: {e}')
        return False


#Delete Files Logic
def deleteFiles(file_names):
    from .models import Schools
    try:
        with connectDB() as session:
            for file_name in file_names:
                school_entry = session.query(Schools).filter_by(id=current_user.school_id).first()
                if school_entry:
                    school_name = school_entry.short

                file_path = os.path.abspath(os.path.join('website', 'static', 'files', school_name, file_name))

                try:
                    os.remove(file_path)
                    if not enterDetails(current_user.id, f'deleted file: {file_name}'):
                        print('Error')
                    return True
                except Exception as e:
                    print(f'Error: {e}')
                    return False
            flash('Fisiere sterse', category='success')
    except Exception as e:
        print(f'Error: {e}')
        return False

#Resetare parola user
@import_db.route('/reset_change/<user_id>', methods = ['POST', 'GET'])
@login_required
def reset_password(user_id):
    from .models import User
    user = User.query.get_or_404(user_id)
    events = returningEvents()
    if request.method == 'POST':
        new_pass = request.form.get('password_reset')
        confirm_pass = request.form.get('password_confirm')
        reset = request.form.get('reset_connect')

        with connectDB() as session:
            check_id = session.query(User).filter_by(id=user_id).first()
            if check_id:
                old = check_password_hash(check_id.password, new_pass)
                if old:
                    flash('Parola nu poate fi aceeasi cu cea veche', category='alert')
                    return redirect(url_for('import.reset_password', user_id = user_id))
                elif new_pass != confirm_pass:
                    flash('Parolele nu corespund', category='alert')
                    return redirect(url_for('import.reset_password', user_id = user_id))
                else:
                    check_id.password = generate_password_hash(new_pass, method='pbkdf2:sha256')
                    if reset == '1':
                        check_id.count -= 1
                    email_user = check_id.email
                    body = 'Parola a fost modificata! \nDacă nu ați cerut schimbarea parolei, adresați-vă Administratorului!'
                    try:
                        session.commit()
                        if not sendMail(email_user, 'Parola Schimbata', body):
                            flash('S-a produs o eroare!')
                        if not enterDetails(current_user.id, f'reset user ~{user_id}~ password'):
                            print('Error with details DB - reset user section')
                        flash('Parola schimbata cu succes', category='success')
                        return redirect(url_for('import.change', user_id = user_id))

                    except Exception as e:
                        session.rollback()
                        flash(f's-a produs o eroare: {e}', category='alert')
    return render_template('reset.html', user=user, events=events)


#Add Files
@import_db.route('/add-files', methods=['POST', 'GET'])
@login_required
def add_files():
    from .models import Schools
    events = returningEvents()
    if request.method == 'POST':
        files = request.files.getlist('files')

        with connectDB() as session:
            school_check = session.query(Schools).filter_by(id=current_user.school_id).first()

            if school_check:
                school_name = school_check.short

            folder_path = os.path.join('website', 'static', 'files', school_name)

            try:
                os.makedirs(folder_path, exist_ok=True)
            except Exception as e:
                current_app.logger.error(f'Error creating folder: {e}')

        if len(files) == 1:
            for file in files:
                file_name = request.form.get('file-name')

                extension = getExtension(file.filename)

                try:
                    if file_name:
                        file_name = f'{file_name}.{extension}'
                    else:
                        original_file_name = file.filename
                        name, file_extension = os.path.splitext(original_file_name)
                        file_name = f'{name}{file_extension}'

                    full_file_path = os.path.join(folder_path, file_name)

                    counter = 1
                    while os.path.exists(full_file_path):
                        base_name, ext = os.path.splitext(file_name)
                        file_name = f'{base_name}({counter:02d}){ext}'
                        full_file_path = os.path.join(folder_path, file_name)
                        counter += 1

                    file.save(full_file_path)

                    if not enterDetails(current_user.id, 'added files'):
                        print('Error with details DB - add files section')

                    flash('S-a adaugat fisierul', category='success')

                except Exception as e:
                    current_app.logger.error(f'Error saving file: {e}')
                    flash(f'S-a produs o eroare: {e}', category='alert')
        else:
            for file in files:
                try:
                    extension = getExtension(file.filename)

                    original_file_name = file.filename
                    name, file_extension = os.path.splitext(original_file_name)

                    file_name = f'{name}{file_extension}'
                    full_file_path = os.path.join(folder_path, file_name)

                    counter = 1
                    while os.path.exists(full_file_path):
                        base_name, ext = os.path.splitext(file_name)
                        file_name = f'{base_name}({counter:02d}){ext}'
                        full_file_path = os.path.join(folder_path, file_name)
                        counter += 1

                    file.save(full_file_path)

                    if not enterDetails(current_user.id, 'added files'):
                        print('Error with details DB - add files section')

                except Exception as e:
                    current_app.logger.error(f'Error saving files: {e}')
            
            flash('S-au adaugat fisierele', category='success')
    return render_template('forms.html', page_name='Adaugare Fisiere', events=events)

#get file extension
def getExtension(filename):
    try:
        return filename.rsplit('.', 1)[1].lower()
    except IndexError:
        return None


#download file
@import_db.route('/download/<file_name>.<file_type>', methods=['GET', 'POST'])
@login_required
def download_file(file_name, file_type):
    from .models import Schools
    try:
        with connectDB() as session:
            school_entry = session.query(Schools).filter_by(id=current_user.school_id).first()
            if school_entry:
                school_names = school_entry.short

            files_folder = os.path.join('static', 'files', school_names)
            file = f'{file_name}.{file_type}'
            return send_from_directory(files_folder, file, as_attachment=True)
        
    except Exception as e:
        flash(f'S-a produs o eroare: {e}', category='alert')


#delete file
@import_db.route('/delete-file/<file_name>.<file_type>', methods=['GET', 'POST'])
@login_required
def delete_file(file_name, file_type):
    from .models import Schools
    with connectDB() as session:
        school_entry = session.query(Schools).filter_by(id = current_user.school_id).first()
        if school_entry:
            school_names = school_entry.short
        file_title = f'{file_name}.{file_type}'
        file = os.path.abspath(os.path.join('website', 'static', 'files', school_names, file_title))
        try:
            os.remove(file)
            session.commit()
            if not enterDetails(current_user.id, f'deleted file {file_title}'):
                print('Error with details DB - delete files section')
            flash('Fisier sters!', category='success')
        except Exception as e:
            flash(f'S-a produs o eroare: {e}', category='alert')
    return redirect(url_for('views.allUsers'))


#add inventar
@import_db.route('/add_inventar', methods=['POST', 'GET'])
@login_required
def add_inventar():
    from .models import User, Inventar
    events = returningEvents()
    users = []
    try:
        with connectDB() as session:
            user_entry = session.query(User).filter(
                User.school_id == current_user.school_id,
                User.rol.in_(['director', 'tehnic', 'profesor', 'admin'])
            ).all()
            if user_entry:
                for user in user_entry:
                    user_calificare = str(user.calificare)
                    capitalized = user_calificare.title()
                    user_new = {'id': user.id, 'nume': f'{user.nume} {user.prenume}', 'calificare': capitalized}
                    users.append(user_new)
                    sesiune['users'] = users
    finally:
        session.close()


    if request.method == 'POST':
        denumire = request.form.get('inventarNume')
        cantitate = request.form.get('inventarCant')
        pret = request.form.get('inventarPret')

        if current_user.rol in ['admin', 'tehnic', 'director']:
            userJson = request.form.get('inventarUserName')

            #deserialize json string
            user = json.loads(userJson)
        else: 
            user = current_user.id

        if user:
            with connectDB() as session:
                if current_user.rol in ['admin', 'tehnic', 'director']: 
                    user_entry = session.query(User).filter_by(id=user['id']).first()
                    school_id = user_entry.school_id
                else: 
                    user_entry = True
                    school_id = current_user.school_id

                if user_entry:
                    total = int(cantitate) * float(pret)
                    try:
                        unique_id = uniqueID()
                        qr_code = createQR(unique_id)
                    except Exception as e:
                        flash(f'S-a produs o eroare: {e}', category='alert')
                    if current_user.rol in ['admin', 'tehnic', 'director']:
                        new_inventar = Inventar(uniqueid=unique_id, name=denumire, cant=cantitate, price=pret, total_price=round(total, 2), user_id=user['id'], school_id=school_id, qrcode=qr_code)
                    else: 
                        new_inventar = Inventar(uniqueid=unique_id, name=denumire, cant=cantitate, price=pret, total_price=round(total, 2), user_id=user, school_id=school_id, qrcode=qr_code)
                    session.add(new_inventar)

                    try:
                        session.commit()
                        flash('Obiect de inventar adaugat cu succes', category='success')
                        if not enterDetails(current_user.id, 'added inventory object'):
                            print('Error at entering details - add inventory object')
                    except Exception as e:
                        session.rollback()
                        flash(f'Error: {e}', category='alert')
                else:
                    flash('Eroare, anuntati administratorul.')
                    print('Error at user query - add inventory')
        else:
            flash('Eroare, contactati administratorul')
    return render_template('forms.html', page_name=f'{current_user.prenume} {current_user.nume}', events=events, users = users)


#autocomplete route
@import_db.route('/autocomplete', methods=['POST'])
@login_required
def autocomplete():
    query = request.form.get('query')
    
    users = sesiune.get('users')
    if users:

        # Filter the list of users based on the input query
        filtered_users = [user for user in users if query.lower() in user['nume'].lower()]

        # Return the suggestions as JSON
        return jsonify({'suggestions': filtered_users})

#inventar changes
@import_db.route('/change_inventar/<unique_id>', methods=['GET', 'POST'])
@login_required
def change_inventar(unique_id):
    from .models import Inventar, User
    inventar = Inventar.query.get_or_404(unique_id)
    events = returningEvents()
    
    #querying for email
    user_id = inventar.user_id
    with connectDB() as session:
        user_check = session.query(User).filter_by(id=user_id).first()
        if user_check:
            email_detinator = user_check.email
            nume_detinator=f'{user_check.nume} {user_check.prenume}'

    if request.method == 'POST':
        #take form inputs
        denumire = request.form.get('inventarName')
        cantitate = request.form.get('inventarCant')
        price = request.form.get('inventarPret')
        total = int(cantitate) * float(price)
        email = request.form.get('inventarEmail')

        with connectDB() as session:
            id_check = session.query(Inventar).filter_by(uniqueid=unique_id).first()

            if id_check:
                if denumire and denumire != id_check.name:
                    id_check.name = denumire
                if cantitate and cantitate != id_check.cant:
                    id_check.cant = cantitate
                    id_check.total_price = round(total, 2)
                if price and price != id_check.price:
                    id_check.price = price
                    id_check.total_price = round(total, 2)
                try:
                    session.commit()
                    if not enterDetails(current_user.id, 'modify inventar settings'):
                        print('Error with details DB - modify inventar section')
                    flash('Modificari aduse cu succes', category='success')
                except Exception as e:
                    session.rollback()
                    flash(f'S-a produs o eroare: {e}')

    return render_template('forms.html', page_name=f'{current_user.prenume} {current_user.nume}', events=events, inventar=inventar, nume_detinator=nume_detinator)


# Delete Inventar Entry
@import_db.route('/delete_inventar/<unique_id>', methods=['GET', 'POST'])
@login_required
def delete_inventar(unique_id):
    from .models import Inventar
    with connectDB() as session:
        inventar = session.query(Inventar).filter_by(uniqueid=unique_id).first()
        
        if inventar:
            session.delete(inventar)

            file = f'{unique_id}.png'
            file_path = os.path.join('website', 'static', 'images', 'qrcodes', file)

            try:
                session.commit()
                os.remove(file_path)
                if not enterDetails(current_user.id, f'deleted Inventar object {file}'):
                    print('Error with details DB - delete Inventar section')
                flash('Obiect de inventar sters', category='success')
            except Exception as e:
                session.rollback()
                flash(f'An error occurred: {e}', category='alert')

    return redirect(url_for('results.inventory'))

# Upload CSV file
@import_db.route('/upload', methods=['POST'])
def upload():
    if 'fileInput' not in request.files:
        return redirect(request.url)

    file = request.files['fileInput']
    csv_path = None
    # Check if the file is selected 
    if file.filename == '':
        return redirect(request.url)

    filename = secure_filename(file.filename)

    if filename == 'detalii.xlsx':
        csv_path = os.path.join('website', 'static', 'csv', file.filename)
        file.save(csv_path)
        try:
            if handle_user(csv_path) and handle_inventar(csv_path):
                with connectDB() as session:
                    try:
                        session.commit()
                        os.remove(csv_path)
                        print('Informatii adaugate')
                    except Exception as e:
                        session.rollback()
                        print(f'S-a produs o eroare: {e}')

        except Exception as e:
            print(f'S-a produs o eroare: {e}')
    elif filename == 'users.xlsx':
        csv_path = os.path.join('website', 'static', 'csv', file.filename)
        file.save(csv_path)
        try:
            if handle_user(csv_path):
                with connectDB() as session:
                    try:
                        session.commit()
                        os.remove(csv_path)
                        print('Informatii adaugate')
                    except Exception as e:
                        session.rollback()
                        print(f'S-a produs o eroare: {e}')
        except Exception as e:
            print(f'S-a produs o eroare: {e}')
    elif filename == 'inventory.xlsx':
        csv_path = os.path.join('website', 'static', 'csv', file.filename)
        file.save(csv_path)
        try:
            if handle_inventar(csv_path):
                with connectDB() as session:
                    try:
                        session.commit()
                        os.remove(csv_path)
                        print('Informatii adaugate')
                    except Exception as e:
                        session.rollback()
                        print(f'S-a produs o eroare: {e}')
        except Exception as e:
            print(f'S-a produs o eroare: {e}')
    else:
        flash("Please rename to detalii.xlsx", category='alert')
    
    return redirect(url_for('views.admin'))


# User table
def handle_user(csv_path):
    from .models import User, Schools

    sheet_name = 'user'

    df_csv = pd.read_excel(csv_path, sheet_name=sheet_name, engine='openpyxl')

    if df_csv.empty:
        return True

    with connectDB() as session:
        for _, row in df_csv.iterrows():
            name = clean_input(str(row["nume"]))
            second_name = clean_input(str(row["prenume"]))
            email = row["email"]
            phone = str(row["telefon"])
            address = str(row["adresa"])
            role = str(row["rol"]).lower()
            school_name = str(row["scoala"])
            calificare = str(row["calificare"]).lower().replace('nan', ' ')
            clasa = row["clasa"]
            elevType = str(row["tip învățământ"]).lower().replace('nan', '')
            # Generate usernames based on the provided logic
            sndparts = second_name.split()
            first_sndname = sndparts[0] if sndparts else ''

            #choose only first second name if it's more
            frsparts = name.split()
            first_name = frsparts[0] if frsparts else ''


            usernames = [f'{first_name}{random.randint(0, 100)}{first_sndname}']
            chosen_username = random.choice(usernames)

            password = f'{name}01'

            # Check if the phone number starts with '0', if not, add '0'
            if not phone.startswith('0'):
                telefon = f'0{phone.rstrip('0').rstrip('.')}'

            school_entry = session.query(Schools).filter_by(school_name=school_name).first()

            if school_entry:
                school_entry.pers += 1

                if calificare == 'director':
                    school_entry.director = f'{name} {second_name}'
                    
                short = school_entry.short

                id = generateRefId(short)

                new_user = User(
                    id=id, nume=name, prenume=second_name, email=email, username=chosen_username,
                    password=generate_password_hash(password, method='pbkdf2:sha256'), rol=role,
                    telefon=telefon, adresa=address, calificare=calificare, school=school_entry, clasa=clasa, time=datetime.now(), tipElev=elevType
                )

                session.add(new_user)
                body = f'ID unic: {id} \nUsername: {chosen_username} \nParola: {password} \nLink de access: 127.0.0.1:5000'
                if validate_email(email):
                    if not sendMail(email, 'Detalii de conectare', body):
                        print('Error at sending email')
                else:
                    print('Not valide email')
        try:
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False


def generateRefId(short, lenght = 6):
    radNum = ''.join(random.choices(string.digits, k=lenght))

    id = f'{short}{radNum}'

    return id


#Inventar table
def handle_inventar(csv_path):
    from .models import Inventar, User

    sheet_name = 'inventar'
    inventar = pd.read_excel(csv_path, sheet_name=sheet_name, engine='openpyxl')

    if inventar.empty:
        return True

    with connectDB() as session:

        for index, row in inventar.iterrows():
            nume = row['denumire']
            cantitate = int(row['bucati'])
            userID = row['ID user']
            price = row['pret/buc']
            total_price = cantitate * price
            user = User.query.filter_by(id=userID).first()
            if user:
                user_id = user.id
                school_id = user.school_id
            else:
                user_id = 'Necesita modificare'
                school_id = 0   
            custom_id = uniqueID()
            custom_qr = createQR(custom_id)

            new_inventar = Inventar(uniqueid = custom_id, name = nume, cant = cantitate, price = price, total_price = total_price, user_id = user_id, qrcode = custom_qr, school_id = school_id)

            session.add(new_inventar)
        try:
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            return False


@import_db.route('/downloadQRCodes', methods=['GET'])
@login_required
def downloadQR():
    from .models import User, Schools, Inventar
    if request.method == 'GET':
        inv_ids = request.args.getlist('inv_ids')
        with connectDB() as session:
            school_entry = session.query(Schools).filter_by(id=current_user.school_id).first()
            if school_entry:
                school_name = school_entry.short
            
            directory = os.path.join('website', 'static', 'directories', school_name)
            zip_directory = os.path.join('website', 'static', 'directories', f'{school_name} - QRCodes')
            file = os.path.join('static', 'directories', f'{school_name} - QRCodes')
            try: 
                os.makedirs(directory, exist_ok=True)
            except Exception as e:
                print(f'S-a produs o eroare: {e}')
            
            users = session.query(User).filter_by(school_id=current_user.school_id).all()

            for user in users:
                user_names = f'{user.nume} {user.prenume}'
                user_directory = os.path.join(directory, user_names)
                try:
                    os.makedirs(user_directory, exist_ok=True)
                except Exception as e:
                    print(f'S-a produs o eroare: {e}')
            

            inventar_entries = []
            for inv in inv_ids:
                inventar = session.query(Inventar).filter_by(uniqueid=inv).first()
                inventar_entries.append(inventar)

            for inventar_entry in inventar_entries:
                user = session.query(User).get(inventar_entry.user_id)

                if user:
                    user_names = f'{user.nume} {user.prenume}'
                    user_directory = os.path.join(directory, user_names)

                    source = os.path.join('website', 'static', 'images', 'qrcodes', f'{inventar_entry.uniqueid}.png')

                    destination = os.path.join(user_directory, f'{inventar_entry.name}.png')

                    try:
                        shutil.copy(source, destination)
                    except Exception as e:
                        print(f'S-a produs o erore: {e}')

                all_inventar = os.path.join(directory, 'Toate Codurile QR')
                try:
                    os.makedirs(all_inventar, exist_ok=True)
                except Exception as e:
                    print(f'S-a produs o eroare: {e}')
                source = os.path.join('website', 'static', 'images', 'qrcodes', f'{inventar_entry.uniqueid}.png')
                destination = os.path.join(all_inventar, f'{inventar_entry.name}.png')
                try:
                    shutil.copy(source, destination)
                except Exception as e:
                    print(f'S-a produs o eroare: {e}')

            remove_empty_directories(directory)
            try:
                shutil.make_archive(zip_directory, 'zip', directory)
                shutil.rmtree(directory)
                if not enterDetails(current_user.id, 'downloaded Compressed QRs'):
                    print('Error with details DB - download QRs section')
                session.commit()
            except Exception as e:
                session.rollback()
                print(f'S-a produs o eroare: {e}')

        return jsonify({'response': f'{file}.zip'})


# create and download compressed directory of qr codes
@import_db.route('/download-qr-codes', methods=['GET'])
@login_required
def downloadQrDirectory():
    from .models import User, Schools, Inventar
    if request.method == 'GET':
        with connectDB() as session:
            school_entry = session.query(Schools).filter_by(id=current_user.school_id).first()
            if school_entry:
                school = school_entry.school_name
                school_name = school.replace('"', '')
            
            directory = os.path.join('website', 'static', 'directories', school_name)
            zip_directory = os.path.join('website', 'static', 'directories', f'{school_name} - QRCodes')
            file = os.path.join('static', 'directories', f'{school_name} - QRCodes')
            try: 
                os.makedirs(directory, exist_ok=True)
            except Exception as e:
                print(f'S-a produs o eroare: {e}')
            
            users = session.query(User).filter_by(school_id=current_user.school_id).all()

            for user in users:
                user_names = f'{user.nume} {user.prenume}'
                user_directory = os.path.join(directory, user_names)
                try:
                    os.makedirs(user_directory, exist_ok=True)
                except Exception as e:
                    print(f'S-a produs o eroare: {e}')
            
            
            inventar_entries = session.query(Inventar).filter_by(school_id=current_user.school_id).all()

            for inventar_entry in inventar_entries:
                user = session.query(User).get(inventar_entry.user_id)

                if user:
                    user_names = f'{user.nume} {user.prenume}'
                    user_directory = os.path.join(directory, user_names)

                    source = os.path.join('website', 'static', 'images', 'qrcodes', f'{inventar_entry.uniqueid}.png')

                    destination = os.path.join(user_directory, f'{inventar_entry.name}.png')

                    try:
                        shutil.copy(source, destination)
                    except Exception as e:
                        print(f'S-a produs o erore: {e}')

                all_inventar = os.path.join(directory, 'Toate Codurile QR')
                try:
                    os.makedirs(all_inventar, exist_ok=True)
                except Exception as e:
                    print(f'S-a produs o eroare: {e}')
                source = os.path.join('website', 'static', 'images', 'qrcodes', f'{inventar_entry.uniqueid}.png')
                destination = os.path.join(all_inventar, f'{inventar_entry.name}.png')
                try:
                    shutil.copy(source, destination)
                except Exception as e:
                    print(f'S-a produs o eroare: {e}')

            remove_empty_directories(directory)
            try:
                shutil.make_archive(zip_directory, 'zip', directory)
                shutil.rmtree(directory)
                if not enterDetails(current_user.id, 'downloaded Compressed QRs'):
                    print('Error with details DB - download QRs section')
                session.commit()
            except Exception as e:
                session.rollback()
                print(f'S-a produs o eroare: {e}')

        return send_file(f'{file}.zip', as_attachment=True)
    
#Verificare continut Folder
def is_directory_empty(directory_path):
    try:
        items = os.listdir(directory_path)

        return not items
    except OSError as e:
        print(f"Error checking directory: {e}")
        return False

#Stergere Foldere Goale
def remove_empty_directories(base_directory):
    for folder in os.listdir(base_directory):
        folder_path = os.path.join(base_directory, folder)

        if os.path.isdir(folder_path) and is_directory_empty(folder_path):
            try:
                os.rmdir(folder_path)
            except OSError as e:
                print(f"Error removing directory: {e}")

#transfer inventar
@import_db.route('/transfer', methods=['POST', 'GET'])
@login_required
def inventarTransfer():
    from .models import Inventar, User
    events = returningEvents()
    inventory = []
    users = []
    try:
        with connectDB() as session:
            inv_entry = session.query(Inventar).filter_by(school_id = current_user.school_id).all()
            if inv_entry:
                for inv in inv_entry:
                    name = inv.name
                    unique_id = inv.uniqueid
                    cant = inv.cant
                    userID = inv.user_id
                    user_entry = session.query(User).filter_by(id = userID).first()

                    if user_entry:
                        userName = f'{user_entry.nume} {user_entry.prenume}'

                        inv_new = {'uniqueID': unique_id, 'name': name, 'cant': cant, 'user': userName, 'userID': userID}
                    else:
                        inv_new = {'uniqueID': unique_id, 'name': name, 'cant': cant, 'userID': ''}

                    inventory.append(inv_new)

                    sesiune['inventory'] = inventory
            
            user_entry = session.query(User).filter(
                User.school_id == current_user.school_id,
                User.rol.in_(['admin', 'tehnic', 'director', 'profesor'])
            ).all()

            if user_entry:
                for user in user_entry:
                    user_id = user.id,
                    user_name = f'{user.nume} {user.prenume}'
                    userCalif = str(user.calificare).title()

                    new_user = {'userID': user_id, 'name': user_name, 'calificare': userCalif}

                    users.append(new_user)
                    sesiune['new_users'] = users
    finally:
        session.close()
    if request.method == 'POST':
        data = request.json
        try:
            if sendRequest(data):
                flash('Trimis către aprobare.', category='success')
                return jsonify(success=True), 200

        except Exception as e:
            print(f'Error at sending request - transfer route: {e}')  
            return jsonify(), 500
                      
    return render_template('forms.html', events=events)

@import_db.route('/autocompleteINV', methods=['POST'])
@login_required
def inventoryID():
    query = request.form.get('query')
    inventory = sesiune.get('inventory')

    if inventory:
        suggestions = [inv for inv in inventory if query.lower() in inv['name'].lower() or query in inv['uniqueID']]

    return jsonify({'suggestions': suggestions}), 200


@import_db.route('/autocompleteUS', methods=['POST'])
@login_required
def inventarUsers():
    query = request.form.get('users')
    users = sesiune.get('new_users')

    if users:
        suggestions = [user for user in users if query.lower() in user['name'].lower()]

    return jsonify({'users': suggestions}), 200


def sendRequest(data):
    from .models import Requests, Inventar, News
    invData = data['inventar']
    userData = data['useri']
    ids = []

    for user in userData:
        user=user
    
    with connectDB() as session:    
        invEntry = session.query(Inventar).filter_by(uniqueid=invData['uniqueid']).first()

        if invEntry:
            requestID = uniqueID()
            ids.append(requestID)
            sessionName = f'{invData['uniqueid']}-ids'
            sesiune[sessionName] = ids

            newRequest = Requests(uniqueid=requestID, invID=invData['uniqueid'], name=invEntry.name, cant=int(invData['cant']), price=invEntry.price, fromUser=invData['userID'], toUser=user, title='Transfer Obiect de Inventar', time=datetime.now())
            newNews = News(id=requestID, type='waiting', title=f'In curs de autorizare - {invData['uniqueid']}', user_id=invData['userID'], time=datetime.now())
            session.add(newRequest)

            try:
                session.commit()

                session.add(newNews)
                session.commit()

                return True
            except Exception as e:
                session.rollback()
                print(f'Error: {e}')
                return False



#Creare ID unic inventar
def uniqueID():
    uuid_str = str(uuid.uuid4().int)
    unique_id = uuid_str.replace('-', ' ')

    characters = string.ascii_lowercase + string.digits + string.ascii_uppercase

    custom_id = ''.join(random.choice(characters) for _ in range(len(unique_id)))[:13]

    return custom_id


#Creare cod QR
def createQR(custom_id):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=1
    )
    qr.add_data(custom_id)
    qr.make(fit=True)

    file = f'{custom_id}.png'
    svg_path = os.path.join('website', 'static', 'images', 'qrcodes', file)

    img = qr.make_image(fill_color='black', back_color='white')

    img.save(svg_path)

    return svg_path
