from flask import Blueprint, render_template, request, url_for, redirect, flash, jsonify
from flask import session as sesiune
from flask_login import current_user, login_required
from sqlalchemy import desc
from . import connectDB, enterDetails, socketio, format_datetime
from datetime import datetime
import qrcode, os, random, string, uuid, pytz

news = Blueprint('news', __name__)


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
    

@news.route('/accept', methods=['POST', 'GET'])
@login_required
def requests():
    from .models import Requests, User, News
    events = returningEvents()
    user_sender = []
    user_receiver = []
    with connectDB() as session:
        #news section
        noutati = session.query(News).filter_by(user_id=current_user.id).order_by(desc(News.time)).all()

        #consent section
        requests = session.query(Requests).filter_by(toUser=current_user.id).order_by(desc(Requests.time)).all()
        for request in requests:
            fromUser = session.query(User).filter_by(id=request.fromUser).first()
            if fromUser:
                fromName = f'{fromUser.nume} {fromUser.prenume}'
                user_sender.append(fromName)
            sessionName = f'data-{request.uniqueid}'
            oldUser = sesiune.get(sessionName)
            
            if oldUser:
                toUser = session.query(User).filter_by(id=oldUser).first()
            else:
                toUser = session.query(User).filter_by(id=request.toUser).first()
            toName = f'{toUser.nume} {toUser.prenume}'
            user_receiver.append(toName)

    return render_template('news.html', events=events, pytz=pytz, noutati=noutati, requests=requests, user_sender=user_sender, user_receiver=user_receiver)


@news.route('/responseUser', methods=['POST'])
@login_required
def responseUser():
    data = request.json

    response = data['response']
    uniqueid = data['uniqueid']

    if response == 'accept':
        if sendRequestDirector(uniqueid):
            flash('S-a trimis aprobarea către direcțiune.', category='success')
            return jsonify(success=True), 200
    else:
        if deleteRequest(uniqueid):
            flash('Transfer anulat')
            return jsonify(success=True), 200


@news.route('/responseDirector', methods=['POST'])
@login_required
def responseDirector():
    data = request.json
    response = data.get('response')
    uniqueid = data.get('uniqueid')

    if response == 'accept':
        if acceptTransferInv(uniqueid):
            flash('Transfer realizat cu success', category='success')
            return jsonify({'message': 'success'}), 200
    else:
        try:
            if deleteRequest(uniqueid):
                flash('S-a anulat transferul.', category='success')
                return jsonify(success=True), 200
            else:
                return jsonify({'message': 'error'}), 500
        except Exception as e:
            print(f'Error: {e}')
            return jsonify({'message': 'error'}), 500



def sendRequestDirector(requestID):
    from .models import Requests, User, News
    with connectDB() as session:
        req_entry = session.query(Requests).filter_by(uniqueid=requestID).first()
        if req_entry:
            toUser = req_entry.toUser
            invID = req_entry.invID
            sessionName = f'data-{requestID}'
            sesiune[sessionName] = toUser

            sessName = f'{invID}-ids'
            ids = sesiune.get(sessName)

            director = session.query(User).filter(
                User.calificare == 'director',
                User.school_id == current_user.school_id
            ).first()
            req_entry.toUser = director.id

            id=uniqueID()
            ids.append(id)
            new_news = News(id=id, type='waiting', title=f'In curs de autorizare - {invID}', user_id=toUser, time=datetime.now())

            session.add(new_news)
            try:
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                print(f'Error: {e}')
                return False


def deleteRequest(requestID):
    from .models import Requests, News
    with connectDB() as session:
        request_entry = session.query(Requests).filter_by(uniqueid=requestID).first()
        if request_entry:

            session.delete(request_entry)
            try:
                sessName = f'{request_entry.invID}-ids'
                ids = sesiune.get(sessName)
                session.commit()
                if not enterDetails(current_user.id, f'Deny transfer id: {requestID}'):
                    print('Error at entering details')
                
                for id in ids:
                    newsEntry = session.query(News).filter_by(id=id).first()
                    if newsEntry:
                        newsEntry.type = 'deny'
                        newsEntry.time = datetime.now()
                        session.commit()
                        sesiune.pop(sessName)
                return True
            except Exception as e:
                session.rollback()
                print(f'Error: {e}')
                return False


def acceptTransferInv(requestID):
    from .models import Inventar, Requests, News
    with connectDB() as session:
        reqEntry = session.query(Requests).filter_by(uniqueid=requestID).first()
        sessionName = f'data-{requestID}'
        to = sesiune.get(sessionName)
        if reqEntry:
            cant = reqEntry.cant
            fromUser = reqEntry.fromUser

            invEntry = session.query(Inventar).filter_by(uniqueid=reqEntry.invID).first()

            if invEntry:
                if to:
                    duplicate = session.query(Inventar).filter(
                        Inventar.user_id == to,
                        Inventar.name == reqEntry.name,
                        Inventar.price == reqEntry.price
                    ).first()
                else: 
                    duplicate = session.query(Inventar).filter(
                        Inventar.user_id == reqEntry.toUser,
                        Inventar.name == reqEntry.name,
                        Inventar.price == reqEntry.price
                    ).first()

                if cant == invEntry.cant:
                    if duplicate:
                        duplicate.cant += cant
                        duplicate.total_price = duplicate.price * duplicate.cant

                        try:
                            session.commit()
                        except Exception as e:
                            session.rollback()
                            print(f'Error: {e}')
                    else:
                        if to:
                            invEntry.user_id = to
                        else:
                            invEntry.user_id = reqEntry.toUser

                elif cant > invEntry.cant:

                    if duplicate:
                        duplicate.cant += cant
                        duplicate.total_price = duplicate.price * duplicate.cant

                        try:
                            session.commit()

                        except Exception as e:
                            session.rollback()
                            print(f'Error: {e}')
                        try:
                            session.delete(invEntry)
                            qrPath = os.path.join('website', 'static', 'images', 'qrcodes', f'{reqEntry.invID}.png')

                            if os.path.exists(qrPath):
                                os.remove(qrPath)
                            else:
                                print('No Path')
                            session.commit()

                        except Exception as e:
                            session.rollback()
                            print(f'Error: {e}')
                    else:
                        if to:
                            invEntry.user_id = to
                        else:
                            invEntry.user_id = reqEntry.toUser

                        invEntry.cant = reqEntry.cant
                        invEntry.total_price = invEntry.cant * invEntry.price

                        try:
                            session.commit()
                        except Exception as e:
                            session.rollback()
                            print(f'Error: {e}')

                elif cant < invEntry.cant:
                    if duplicate:
                        duplicate.cant += cant
                        duplicate.total_price = duplicate.price * duplicate.cant

                        invEntry.cant -= cant
                        invEntry.total_price = invEntry.price * invEntry.cant

                        try:
                            session.commit()
                        except Exception as e:
                            session.rollback()
                            print(f'Error: {e}')
                    else:
                        uniqueid = uniqueID()
                        qrcode = createQR(uniqueid)
                        if to:
                            new_inventar = Inventar(uniqueid=uniqueid, name=reqEntry.name, cant=cant, price=invEntry.price, total_price=cant * invEntry.price, user_id = to, school_id = current_user.school_id, qrcode=qrcode)
                        else:
                            new_inventar = Inventar(uniqueid=uniqueid, name=reqEntry.name, cant=cant, price=invEntry.price, total_price=cant * invEntry.price, user_id = reqEntry.toUser, school_id = current_user.school_id, qrcode=qrcode)
                        session.add(new_inventar)

                        try:
                            session.commit()

                            invEntry.cant += cant
                            invEntry.total_price = invEntry.price * invEntry.cant

                            session.commit()
                        except Exception as e:
                            session.rollback()
                            print(f'Error: {e}')

        try:
            sessName = f'{reqEntry.invID}-ids'
            ids = sesiune.get(sessName)

            session.delete(reqEntry)

            if not enterDetails(current_user.id, f'Transfer inventory object {reqEntry.invID}'):
                print('Error at entering details')

            session.commit()

            for id in ids:
                newsEntry = session.query(News).filter_by(id=id).first()
                if newsEntry:
                    newsEntry.type = 'accept'
                    newsEntry.time = datetime.now()
                    session.commit()
                    sesiune.pop(sessName)
            
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


@news.route('/deleteNews', methods=['POST'])
@login_required
def deleteNews():
    from .models import News
    data = request.json

    response = data['response']
    id = data['id']

    with connectDB() as session:
        newsEntry = session.query(News).filter_by(id=id).first()

        if response == 'close':
            if newsEntry:
                session.delete(newsEntry)

                try:
                    session.commit()
                    return jsonify(success=True), 200
                except Exception as e:
                    session.rollback()
                    print(f'Error: {e}')
                    return jsonify(success=False), 500
