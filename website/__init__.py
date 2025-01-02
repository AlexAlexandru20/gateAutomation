from flask import Flask, current_app, request, render_template
from flask_mail import Mail, Message
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_sse import sse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from os import path
from babel.dates import format_date, format_time, format_datetime
from datetime import datetime
import os

#init DB
db = SQLAlchemy()

#init socketIO
socketio = SocketIO()

#init mail
mail = Mail()


#Create APP
def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    db.init_app(app)
    #init Mail
    mail.init_app(app)


    from .views import views
    from .auth import auth
    from .models import User
    from .qrscanner import qreader
    from .import_changes import import_db
    from .chat import chat_blueprint
    from .results import results
    from .convertFiles import convert
    from .noutati import news
    from .createFiles import create

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(results, url_prefix='/')
    app.register_blueprint(convert, url_prefix='/')
    app.register_blueprint(chat_blueprint, url_prefix='/chat')
    app.register_blueprint(import_db, url_prefix='/import')
    app.register_blueprint(qreader, url_prefix='/')
    app.register_blueprint(news, url_prefix='/news')
    app.register_blueprint(create, url_prefix='/')

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def user_loader(id):
        return User.query.get(id)

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('error.html'), 404
    
    with app.app_context():
        db.create_all()

    socketio.init_app(app)
        
    return app



#ConnectDB called function
def connectDB():
    database_url = f'sqlite:///{os.path.join(current_app.instance_path, 'management.db')}'
    engine = create_engine(database_url)

    Session = sessionmaker(bind=engine)
    
    return Session()


#Enter Details in DB
def enterDetails(id, motiv):
    from .models import Details
    ip=request.remote_addr
    new_detail = Details(user_id = id, motiv=motiv, ip_address = ip)
    with connectDB() as session:
        try:
            session.add(new_detail)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f'Error: {e}')
            return False


#sendMails
def sendMail(receiver, subject, body):
    msg = Message(subject=subject, recipients=[receiver], body=body)

    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f'Error: {e}')
        return False

DB_NAME = 'management.db'

def create_database(app):
    if not path.exists(DB_NAME):
        with app.app_context():
            db.create_all()
        print('Database created')


def format_datetime_babel(datetime_str, locale='ro'):
    dt_object = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S") if "T" in datetime_str else datetime.strptime(datetime_str, "%Y-%m-%d")

    month_full = format_date(dt_object, format='d MMMM', locale=locale)
    week_day = format_date(dt_object, format='EEEE', locale=locale)
    time_formatted = format_time(dt_object, format='HH:mm', locale=locale) if "T" in datetime_str else None

    result = {
        'month': month_full,
        'weekDay': week_day
    }

    if time_formatted:
        result['time'] = time_formatted

    return result
