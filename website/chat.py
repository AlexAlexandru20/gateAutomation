from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from flask_socketio import join_room, leave_room, emit, SocketIO, send
from flask_login import login_required, current_user
from string import ascii_uppercase
import random
from . import socketio

chat_blueprint = Blueprint('chat', __name__)

# Using a dictionary to store rooms and their details
rooms = {}


def generate_room_code(length):
    while True:
        room = ''.join(random.choice(ascii_uppercase) for _ in range(length))
        if room not in rooms:
            return room


@chat_blueprint.route('/connect', methods=['GET', 'POST'])
@login_required
def chat():
    session.clear()
    if request.method == 'POST':
        username = current_user.username
        code = request.form.get('join')
        join = request.form.get('join-btn', False)
        create = request.form.get('create', False)
        
        session.permanent = False

        if join and not code:
            flash('Introduceti un cod!', category='alert')

        if create is not False:
            room = generate_room_code(5)
            rooms[room] = {"members": 0, "messages": []}
            session['room'] = room
            return redirect(url_for('chat.room'))
        elif join is not False and code:
            if code not in rooms:
                flash(f'Codul nu este corect! codul {code}', category='alert')
            else:
                session['room'] = code
                return redirect(url_for("chat.room"))

    return render_template('chat.html', page_name='WebChat')

@chat_blueprint.route('/room', methods=['GET', 'POST'])
@login_required
def room():
    room = session.get('room')
    return render_template('room.html', page_name='Webchat', code = room)


@socketio.on('message')
def message(data):
    room = session.get('room')

    if room not in rooms:
        return
    
    content = {
        "name": current_user.username,
        "message": data["data"]
    }

    send(content, to=room)
    rooms[room]["messages"].append(content)


@socketio.on('connect')
def handle_connect(auth):
    room = session.get('room')
    name = current_user.username

    if not room or not name:
        return

    if room not in rooms:
        rooms[room] = {"members": 0, "messages": []}

    join_room(room)
    rooms[room]["members"] += 1

    socketio.emit("message", {"name": name, "message": "has entered the room"}, room=room)

@socketio.on('disconnect')
def handle_disconnect():
    room = session.get('room')
    name = current_user.username

    if room is None:
        return

    if room in rooms:
        rooms[room]["members"] -= 1

        if rooms[room]["members"] == 0:
            del rooms[room]
            socketio.emit("message", {"name": name, "message": "has left the room"}, room=room)

        socketio.emit("message", {"name": name, "message": "has left the room"}, room=room)
    else:
        print("Current rooms dictionary:", rooms)
        print(f"Room {room} not found in the rooms dictionary.")
