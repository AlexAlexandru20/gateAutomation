from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash
from . import connectDB, enterDetails
from .models import User
from flask_login import logout_user, login_user, login_required, current_user

auth = Blueprint('auth', __name__)

@auth.route('/', methods = ['GET'])
def hero():
    return render_template('index.html')

#login route
@auth.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        print(f'{username} {password}')
        session['username'] = username

        with connectDB() as session_db:

            user = session_db.query(User).filter_by(username=username).first()

            if user:
                if check_password_hash(user.password, password):
                    flash('Conectat cu succes', category='success')
                    #add details in DB
                    if not enterDetails(user.id, 'connected to server'):
                        print('s-a produs o eroare, reincercati!', category='alert')
                    login_user(user, remember=True)
                    #redirect to reset page
                    if user.count == 0:
                        return redirect(url_for('views.reset_pass'))
                    role = user.rol
                    cal = user.calificare
                    return jsonify({'userRole': role, 'userCalif': cal}), 200
                else:
                    return jsonify({'message': 'wrong'}), 200
            else:
                return jsonify({'message': 'wrong'}), 200
    return render_template('login.html')


#logout route
@auth.route('/logout')
@login_required
def logout():
    #add details to DB
    if not enterDetails(current_user.id, 'disconnected from server'):
        flash('s-a produs o eroare, incercati din nou', category='alert')
    logout_user()
    return redirect(url_for('auth.login'))