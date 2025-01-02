from flask import Blueprint, render_template, Response
from flask_login import login_required, current_user
from . import socketio, connectDB, format_datetime
from .models import Events
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from datetime import datetime

qreader = Blueprint('qread', __name__)

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

global cap

qr_code_detected = False

def generate_frames():
    global cap, qr_code_detected
    
    while not qr_code_detected:
        success, frame = cap.read()

        if not success:
            break
        else:
            frame_flip = cv2.flip(frame, 1)
            try:
                decoded_data = decode(frame_flip)

                if decoded_data:
                    for qrcode in decoded_data:
                        my_data = qrcode.data.decode('utf-8')

                        pts = np.array([qrcode.polygon], np.int32) 
                        pts = pts.reshape((-1, 1, 2))
                        cv2.polylines(frame_flip, [pts], True, (0, 0, 0), 3)

                        qr_code_detected = True

                        # Emit a SocketIO event to the client
                        socketio.emit('qr_detected', {'query': my_data}, namespace='/qrscanner')
                        qr_code_detected = False

            except Exception as e:
                print(f"Error decoding QR code: {e}")

            ret, buffer = cv2.imencode('.jpg', frame_flip)
            frame = buffer.tobytes()

        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@qreader.route('/qrscanner')
@login_required
def qrscanner():
    events = returningEvents()
    global cap
    cap = cv2.VideoCapture(0)
    return render_template('qrscanner.html', events=events)

@qreader.route('/video')
@login_required
def videoStreaming():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('close_page', namespace='/qrscanner')
def handle_close_page(data):
    cap.release()