from . import db
from flask_login import UserMixin
from sqlalchemy import func

class schoolsRequests(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school_name = db.Column(db.String(100))
    short = db.Column(db.String(10))
    address = db.Column(db.String(200))
    phone = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True)


class Events(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    start = db.Column(db.String(100))
    end = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User')


class News(db.Model):
    id = db.Column(db.String, primary_key=True)
    type = db.Column(db.String(20))
    title= db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    time = db.Column(db.DateTime(timezone=True), default=func.now())
    user = db.relationship('User')


class Requests(db.Model):
    uniqueid = db.Column(db.String(20), primary_key=True)
    invID = db.Column(db.String(30))
    name = db.Column(db.String(100))
    cant = db.Column(db.Integer)
    price = db.Column(db.Float())
    fromUser = db.Column(db.Integer, db.ForeignKey('user.id'))
    toUser = db.Column(db.Integer)
    title = db.Column(db.String(100))
    time = db.Column(db.DateTime(timezone=True), default=func.now())
    user = db.relationship('User')


class Inventar(db.Model):
    uniqueid = db.Column(db.String(255), unique=True, primary_key = True)
    name = db.Column(db.String(150))
    cant = db.Column(db.Integer)
    price = db.Column(db.Float())
    total_price = db.Column(db.Float())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    school_id = db.Column(db.Integer)
    qrcode = db.Column(db.String(255))


class User(db.Model, UserMixin):
    id = db.Column(db.String(20), primary_key=True)
    nume = db.Column(db.String(150))
    prenume = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(160))
    telefon = db.Column(db.String(14))
    adresa = db.Column(db.String(150))
    rol = db.Column(db.String(20))
    calificare = db.Column(db.String(20))
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'))
    clasa = db.Column(db.String(10))
    tipElev = db.Column(db.String(30))
    count = db.Column(db.Integer, default=0)
    time = db.Column(db.DateTime(timezone=True), default=func.now)
    school = db.relationship('Schools', back_populates='users')
    inventar = db.relationship('Inventar')
    connect = db.relationship('Details')


class Schools(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school_name = db.Column(db.String(150))
    short = db.Column(db.String(10))
    adresa = db.Column(db.String(200))
    phone = db.Column(db.String(100))
    email = db.Column(db.String(150), unique=True)
    pers = db.Column(db.Integer, default=0)
    director = db.Column(db.String(150))
    users = db.relationship('User', back_populates='school')


class Details(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_time = db.Column(db.DateTime(timezone=True), default=func.now())
    motiv = db.Column(db.String(100))
    ip_address = db.Column(db.String(20))