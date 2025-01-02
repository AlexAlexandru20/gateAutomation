from flask import Blueprint, render_template, render_template_string, redirect, request, flash, url_for, jsonify
from flask import session as sesiune
from sqlalchemy import and_, desc, func
from flask_login import login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import Details, User, Events, Inventar, Schools
from . import db, connectDB, enterDetails, sendMail, format_datetime
from datetime import datetime
import random, os, shutil


views = Blueprint('views', __name__)


# check user type
def checkUserType(user_rol, user_type):
    if current_user.rol == 'admin':
        return True
    elif current_user.rol == str(user_rol) or current_user.calificare == str(user_type):
        return True
    else:
        flash('Conectati-va cu un alt cont pentru a accesa aceasta pagina.', category='alert')
        if not enterDetails(current_user.id, 'tried to access wrong page for his type'):
            print('Error at section user type check')
        logout_user()
        return False


def deleteFiles():
    path = os.path.join('website', 'static', 'directories')
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
    except Exception as e:
        print(f'Error at deleteing files-background: {e}')


def returningEvents():
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


#admin template
@views.route('/admin', methods=['POST', 'GET'])
@login_required
def admin():
    try: 
        if checkUserType('admin', 'informatician'):
            deleteFiles()
            events = returningEvents()
            with connectDB() as session:
                # elevi
                elevi = session.query(User).filter(
                    User.school_id == current_user.school_id,
                    User.rol == 'elev'
                ).all()
                total_elevi = len(elevi) if elevi else 0

                liceu = session.query(User).filter(
                    User.school_id == current_user.school_id,
                    User.rol == 'elev',
                    (User.tipElev == 'liceu')
                ).all()
                total_liceu = len(liceu) if liceu else 0

                procentajLiceu = int(calcproc(total_liceu, total_elevi)) if elevi else 0

                prof = session.query(User).filter(
                    User.school_id == current_user.school_id,
                    User.rol == 'elev',
                    User.tipElev == 'profesionala'
                ).all()
                total_prof = len(prof) if prof else 0

                procentajProf = int(calcproc(total_prof, total_elevi)) if elevi else 0
                
                other = session.query(User).filter(
                    User.school_id == current_user.school_id,
                    User.rol == 'elev',
                    User.tipElev != 'liceu',
                    User.tipElev != 'profesionala'
                ).all()
                total_other = len(other) if other else 0

                procentajOther = int(calcproc(total_other, total_elevi)) if elevi else 0

                #staff
                staff = session.query(User).filter(
                    User.school_id == current_user.school_id,
                    User.rol != 'elev'
                ).all()
                total_staff = len(staff)
                
                didactic = session.query(User).filter(
                    User.school_id == current_user.school_id,
                    User.rol == 'profesor'
                ).all()
                total_didactic = len(didactic) if staff else 0

                procentajDidactic = int(calcproc(total_didactic, total_staff)) if staff else 0

                nedidactic = session.query(User).filter(
                    User.school_id == current_user.school_id,
                    (User.rol == 'director') |
                    (User.rol == 'tehnic')
                ).all()
                total_nedidactic = len(nedidactic) if staff else 0

                procentajNedidactic = int(calcproc(total_nedidactic, total_staff)) if staff else 0

                #inventar
                inventory = session.query(Inventar).filter_by(school_id = current_user.school_id).all()
                total_inventar = len(inventory) if inventory else 0

                invSum = sum(inv.cant for inv in inventory)
                
                invDidactic = []

                for user in didactic:
                    invDid = session.query(Inventar).filter(
                        Inventar.school_id == current_user.school_id,
                        Inventar.user_id == user.id
                    ).all()

                    if invDid:
                        invDidactic.append(invDid)

                procentajInvDid = int(calcproc(sum(len(inv_list) for inv_list in invDidactic) if didactic else 0, total_inventar))
                
                
                invNedidactic = []

                for user in nedidactic:
                    invNedid = session.query(Inventar).filter(
                        Inventar.school_id == current_user.school_id,
                        Inventar.user_id == user.id
                    ).all()

                    if invNedid:
                        invNedidactic.append(invNedid)
                    else:
                        continue
                procentajInvNedid = int(calcproc(sum(len(inv_list) for inv_list in invNedidactic) if nedidactic else 0, total_inventar))

                #files section
                school = session.query(Schools).filter_by(id = current_user.school_id).first()

                if school:
                    school_name = str(school.school_name).replace('"', '')
                
                folder_path = os.path.join('website', 'static', 'files', school_name)

                files = []

                if os.path.exists(folder_path):
                    file_names = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
                    files = [{'name': file_name.split('.')[0], 'type': file_name.split('.')[-1]} for file_name in file_names]
                
                # Count the occurrences of each file type
                file_type_counts = {}
                total_files = len(files)

                for file_info in files:
                    file_type = file_info['type']
                    file_type_counts[file_type] = file_type_counts.get(file_type, 0) + 1

                # Sort file types based on their frequency
                sorted_file_types = sorted(file_type_counts.items(), key=lambda x: x[1], reverse=True)

                # Calculate the percentage of each file type
                file_type_percentages = {file_type: round((count / total_files) * 100) for file_type, count in sorted_file_types}

                # Create a list to store first and second types along with percentages
                result = []

                # Separate the first two file types
                if len(sorted_file_types) >= 2:
                    first_type = {'name': str(sorted_file_types[0][0]).upper(), 'percentage': file_type_percentages.get(sorted_file_types[0][0], 0)}
                    second_type = {'name': str(sorted_file_types[1][0]).upper(), 'percentage': file_type_percentages.get(sorted_file_types[1][0], 0)}
                    other_percentage = sum(file_type_percentages.get(file_type, 0) for file_type, count in sorted_file_types[2:])
                else:
                    # Handle the case where there are less than two file types
                    first_type, second_type, other_percentage = None, None, 0

                # Append first and second types to the result list
                if first_type:
                    result.append(first_type)
                if second_type:
                    result.append(second_type)

                # Append "other" entry to the result list
                result.append({'name': 'other', 'percentage': other_percentage})

                #recently table results
                users=[]
                users_entry = session.query(User).filter_by(school_id = current_user.school_id).order_by(desc(User.time)).limit(5).all()
                if users_entry:
                    for user in users_entry:
                        name = f'{user.nume} {user.prenume}'
                        user_data = {
                            'id': user.id,
                            'name': name,
                            'role': user.calificare.capitalize() if user.rol == 'tehnic' else user.rol.capitalize(),
                            'email': user.email,
                            'date': user.time.strftime("%H:%M %d/%m"),
                            'frsName': user.nume,
                            'sndName': user.prenume,
                            'phone': user.telefon,
                            'address': user.adresa,
                            'create': user.time.strftime("%d %m %y"),
                            'rol': user.rol.capitalize(),
                            'calif': user.calificare.capitalize(),
                            'clasa': str(user.clasa).upper() if user.rol =='elev' else ''
                        }
                        users.append(user_data)
            return render_template('admin.html', events=events, studentsTotal = total_elevi, procentaj_liceu = procentajLiceu, procentaj_prof = procentajProf, procentaj_other = procentajOther, staffTotal = total_staff, procentaj_didactic = procentajDidactic, procentaj_nedidactic = procentajNedidactic, inventoryTotal=invSum, procentaj_invDid = procentajInvDid, procentaj_invNedid = procentajInvNedid, filesTotal=total_files, firstType=first_type, secondType=second_type, other_percentage=other_percentage, users=users)
        else:
            return redirect(url_for('auth.login'))
    except Exception as e:
        flash(f'S-a produs o eroare: {e}', category='alert')
    

def calcproc(x, y):
    return round(x * 100 / y) if y != 0 else 0


#director template
@views.route('/director')
@login_required
def director():
    try: 
        if checkUserType('director', 'director'):
            deleteFiles()
            events = returningEvents()
            return render_template('director.html', events=events)
        else:
            return redirect(url_for('auth.login'))
    except Exception as e:
        flash(f'S-a produs o eroare: {e}', category='alert')


# profesor template
@views.route('/profesor')
@login_required
def teacher():
    try:
        if checkUserType('profesor','director adjunct'):
            deleteFiles()
            events = returningEvents()
            return render_template('teacher.html', events=events)
        else:
            return redirect(url_for('auth.login'))
    except Exception as e:
        flash(f'S-a produs o eroare: {e}', category='alert')
        return redirect(url_for('auth.login'))


#elev template
@views.route('/elev')
@login_required
def student():
    try: 
        if checkUserType('elev', ''):
            return render_template('student.html')
        else:
            return redirect(url_for('auth.login'))
    except Exception as e:
        flash(f'S-a produs o eroare: {e}', category='alert')


@views.route('/getUserData/<userId>', methods=['GET'])
@login_required
def getUserData(userId):
    with connectDB() as session:
        user_entry = session.query(User).filter(
            User.id == userId,
            User.school_id == current_user.school_id
        ).first()
        if user_entry:
            user = {
                'id': user_entry.id,
                'name': user_entry.nume,
                'sndName': user_entry.prenume,
                'email': user_entry.email,
                'phone': user_entry.telefon,
                'address': user_entry.adresa,
                'role': user_entry.rol.capitalize(),
                'calif': user_entry.calificare.capitalize(),
                'class': str(user_entry.clasa).upper() if user_entry.rol == 'elev' else '',
                'create': user_entry.time.strftime("%d %m %Y")
            }
            return jsonify(user), 200
        else:
            return jsonify({'error': 'Error'}), 500


@views.route('allUsers', methods=['POST', 'GET'])
@login_required
def allUsers():
    events = returningEvents()
    with connectDB() as session:
        users = [] 
        user_entry = session.query(User).filter_by(school_id = current_user.school_id).order_by(User.nume.asc()).all()
        for user in user_entry:
            user_data = {
                'id': user.id,
                'nume': user.nume,
                'prenume': user.prenume,
                'rol': user.rol.capitalize(),
                'calificare': user.calificare.capitalize() if user.rol != 'elev' else str(user.clasa).upper()
            }
            users.append(user_data)
    
    return render_template('tables.html', tables=True, users = users, events=events)


@views.route('students', methods=['POST', 'GET'])
@login_required
def students():
    with connectDB() as session:
        users = [] 
        user_entry = session.query(User).filter(
            User.school_id == current_user.school_id,
            User.rol == 'elev'
        ).order_by(User.nume.asc()).all()
        for user in user_entry:
            user_data = {
                'id': user.id,
                'nume': user.nume,
                'prenume': user.prenume,
                'rol': user.rol.capitalize(),
                'calificare': str(user.clasa).upper()
            }
            users.append(user_data)
    
    return render_template('tables.html', tables=True, users = users)


@views.route('staff', methods=['POST', 'GET'])
@login_required
def staff():
    with connectDB() as session:
        events = returningEvents()
        users = [] 
        user_entry = session.query(User).filter(
            User.school_id == current_user.school_id,
            User.rol != 'elev'
        ).order_by(User.nume.asc()).all()
        for user in user_entry:
            user_data = {
                'id': user.id,
                'nume': user.nume,
                'prenume': user.prenume,
                'rol': user.rol.capitalize(),
                'calificare': user.calificare.capitalize()
            }
            users.append(user_data)
    
    return render_template('tables.html', tables=True, users = users, events=events)


#calendar route
@views.route('/calendar', methods=['POST', 'GET'])
@login_required
def calendarGenerator():
    if request.method == 'POST':
        try:
            data = request.get_json()

            title = data.get('title')
            startDate = data.get('dates', {}).get('start')
            endDate = data.get('dates', {}).get('end')
            with connectDB() as session:
                new_event = Events(title=title, start=startDate, end=endDate, user_id=current_user.id)
                session.add(new_event)
                try:
                    session.commit()
                except Exception as e:
                    session.rollback()
                    print(f'Error: f{str(e)}')

            return jsonify({'message': 'Event created succesfully'}), 200
        except Exception as e:
            print(f'Error: {str(e)}')
            return jsonify({'message': 'Error'}), 500
        
    events_calendar=Events.query.filter_by(user_id=current_user.id).all()
    events = returningEvents()
    return render_template('calendar.html', events_calendar=events_calendar, events=events)


# update event
@views.route('/update_event', methods=['POST'])
@login_required
def update_event():
    try:
        data = request.get_json()

        event_id = int(data.get('id'))
        new_start = data.get('start')
        new_end = data.get('end')

        with connectDB() as session:
            updated_event = session.query(Events).filter_by(id=event_id).first()

            if updated_event is not None:
                updated_event.start = new_start
                updated_event.end = new_end
                try:
                    session.commit()
                    return jsonify({'message': 'Event updated successfully'}), 200
                except Exception as e:
                    session.rollback()
            else:
                print('not found')
                return jsonify({'message' 'Event not found'}), 404


    except Exception as e:
        print(f'Error {str(e)}')
        return jsonify({'message': 'Error'}), 500


# delete event
@views.route('/delete_event', methods=['POST'])
@login_required
def delete_event():
    try:
        data = request.get_json()

        event_id = data.get('eventID')

        with connectDB() as session:
            event = session.query(Events).filter_by(id=event_id).first()
            if event:
                print('Event found')
                session.delete(event)
                try:
                    session.commit()
                    return jsonify({'message': 'Successfully'}), 200
                except Exception as e:
                    session.rollback()
                    print(f'error: {str(e)}')
                    return jsonify({'message': 'Error'}), 500
    except Exception as e:
        print(f'Error: {e}')


# reset password
@views.route('/reset_pass', methods=['GET','POST'])
@login_required
def reset_pass():
    if request.method == 'POST':
        password = request.form.get('password_reset')
        confirm_pass = request.form.get('password_confirm')
        old = check_password_hash(current_user.password, password)

        if old:
            flash('Parola nu poate fi aceasi cu cea veche', category='alert')
        elif password != confirm_pass:
            flash('Parolele nu corespund', category='alert')
        else:
            current_user.password = generate_password_hash(password, method='pbkdf2:sha256')

            current_user.count = 1
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash(f'S-a produs o eroare: {e}', category='alert')
            if not enterDetails(current_user.id, 'changed his password'):
                print('Error at entering details - changed password')
            try:
                body = 'Datele de conectare au fost schimbate.\nDaca nu ati facut aceste modificari, adresati-va administratorului.'
                sendMail(current_user.email, 'Date de conectare schimbate', body)
            except Exception as e:
                print(f'Error at mail - change password: {e}')
            flash('Parolă schimbată cu succes', category='succes')

            role = current_user.rol
            try:
                match role.lower():
                        case 'admin' | 'tehnic':
                            return redirect(url_for('views.admin'))
                        case 'profesor':
                            return redirect(url_for('views.teacher'))
                        case 'elev':
                            return redirect(url_for('views.student'))
                        case 'director':
                            return redirect(url_for('views.director'))
                        case _:
                            flash('Contul nu apartine organizatiei. Va rugam contactati administratorul scolii', category='alert')
                            return redirect(url_for('auth.login'))
            except Exception as e:
                flash(f'S-a produs o eroare: {e}', category='alert')
    return render_template('reset.html')


#reset username
@views.route('/reset_user', methods=['POST', 'GET'])
@login_required
def reset_user():
    if request.method == 'POST':
        old_username = request.form.get('user_reset')
        new_username = request.form.get('username_confirm')

        user = current_user.username
        existing_user = db.session.query(User).filter_by(username = new_username).first()

        if old_username != user:
            flash('Username gresit. ', category='alert')
        elif old_username == new_username:
            flash('Trece valori diferite', category='alert')
        elif existing_user:
            flash('Username existent.', category='alert')
        else:    
            try:
                current_user.username = new_username
                db.session.commit()
                if not enterDetails(current_user.id, 'Changed the username'):
                    print('Error at entering details')
                flash('Username schimbat', category='success')
                if sendMail(current_user.email, 'Date de conectare schimbate', f'S-a modificat username-ul acestui cont. \nVechiul Username: {old_username}\nNoul Username: {new_username}'):
                    logout_user()
                else:
                    print('Error at sending mail')
                    logout_user()
                return redirect(url_for('auth.login', username = new_username))
            except Exception as e:
                db.session.rollback()
                flash(f'S-a produs o eroare: {e}', category='alert')

    return render_template('reset.html', page_name='Resetare username')


#confirm Email
@views.route('/confirm-email', methods=['POST', 'GET'])
@login_required
def confirmEmail():
    if request.method == 'POST':
        from .models import User
        email = request.form.get('email')
        with connectDB() as session:
            user_check = session.query(User).filter(
                User.email == email,
                User.id == current_user.id
            ).first()

            if user_check:
                otp = generate_prime_sum_digits()
                token = f'otp_{current_user.id}'
                sesiune[token] = otp
                sesiune.permanent = True
                try:
                    body = f'Codul pentru resetarea parolei este: {otp}.\nCodul este valabil pentru 5 minute\nDaca nu ati solicitat resetarea parolei, va sugeram sa va securizati contul. '
                    sendMail(email, 'Cod resetare parola', body)
                    return jsonify({'message': 'success'}), 200
                except Exception as e:
                    print(f'Error: {e}')
                    return jsonify({'error'}), 500
            else:
                return jsonify({'message': 'success'}), 200
    return render_template('reset.html', page_name='Resetare Parola')

def is_prime(n):
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def generate_prime_sum_digits():
    digits = list(range(1, 10))
    prime_sum = None

    while prime_sum is None:
        combination = random.sample(digits, 6)
        if is_prime(sum(combination)):
            prime_sum = combination
    # Convert digits to strings and join them
    result_string = ''.join(map(str, prime_sum))
    return result_string


#verify OTP
@views.route('/verifyOTP', methods=['POST', 'GET'])
@login_required
def verifyOTP():
    if request.method == 'POST':
        otp = str(request.form.get('otp'))
        token= f'otp_{current_user.id}'
        correct_otp = str(sesiune.get(token))
        if otp == correct_otp:
            sesiune.pop(token, None)
            return jsonify({'message': 'success'}), 200
        else:
            return jsonify({'error'}), 500
    return render_template('reset.html', page_name='Resetare Parola')


#inventar route
@views.route('/inventar', methods=['GET', 'POST'])
@login_required
def inventar():
    events = returningEvents()
    with connectDB() as session:
        if current_user.rol in ['admin', 'tehnic']:
            inventars = session.query(Inventar).filter_by(school_id=current_user.school_id).order_by(Inventar.name.asc()).all()
            currentUser = session.query(User).filter(
                User.school_id==current_user.school_id, 
                User.id==current_user.id,
                Inventar.user_id==current_user.id
            ).first()
            restUsers = session.query(User).filter(
                User.school_id==current_user.school_id, 
                User.id!=current_user.id, 
                Inventar.user_id==User.id
                ).order_by(User.nume.asc()).all()
            #fetch users
            if not currentUser:
                users = restUsers
            else:
                users = [currentUser] + restUsers

            if not inventars:
                return render_template('error.html', page_type='Nu aveți obiecte de inventar')
            
            results={}
            for user in users:
                user_inventory = []
                for inventar in inventars:
                    if inventar.user_id == user.id:
                        user_inventory.append({
                            "inventarTitle": inventar.name,
                            "inventarCant": inventar.cant,
                            "inventarPrice": inventar.price,
                            "inventarTotalPrice": inventar.total_price
                        })
                results[user.id] = {
                    "userId": user.id,
                    "userName": f'{user.nume} {user.prenume}',
                    "inventory": user_inventory
                }
        else:
            inventars = session.query(Inventar).filter(
                and_(
                    Inventar.school_id == current_user.school_id,
                    Inventar.user_id == current_user.id
                )
            ).all()
            user = session.query(User).filter_by(id=current_user.id).first()
            results={}
            user_inventory=[]
            for inventar in inventars:
                user_inventory.append({
                    "inventarTitle": inventar.name,
                    "inventarCant": inventar.cant,
                    "inventarPrice": inventar.price,
                    "inventarTotalPrice": inventar.total_price
                })
            results[user.id] = {
                "userId": user.id,
                "userName": f'{user.nume} {user.prenume}',
                "inventory": user_inventory
            }
            if not user_inventory:
                return render_template('error.html', page_type='Nu aveți obiecte de inventar')


    return render_template('forms.html', results=results, events=events)


@views.route('/errors/<error>', methods=['POST', 'GET'])
def error(error):
    return render_template('error.html', pagetype=error)