DB_NAME = 'management.db'

class Config:
    SECRET_KEY = '441376764651111'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_NAME}'
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = 'schoolsucksmg@gmail.com'
    MAIL_PASSWORD = 'crva tufe rwhd pkhq'
    MAIL_DEFAULT_SENDER = 'schoolsucksmg@gmail.com'
    REDIS_URL = None