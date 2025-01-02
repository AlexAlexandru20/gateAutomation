from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from .models import User, Inventar, Schools, Events
from . import connectDB, format_datetime
from datetime import datetime
import os

results = Blueprint('results', __name__)

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

@results.route('/inventory', methods=['POST', 'GET'])
@login_required
def inventory():
    inventory = []
    events=returningEvents()
    with connectDB() as session:
        inventar = session.query(Inventar).filter_by(school_id = current_user.school_id).all()
        if inventar:
            for inv in inventar:
                user = session.query(User).filter_by(id = inv.user_id).first()
                inv_data = {
                    'id': inv.uniqueid,
                    'nume': inv.name,
                    'user': f'{user.nume} {user.prenume}',
                    'cant': inv.cant
                }
                inventory.append(inv_data)
    return render_template('tables.html', inventar = inventory, events=events)

@results.route('/getInvData/<invId>', methods=['GET'])
@login_required
def getInvData(invId):
    with connectDB() as session:
        inv = session.query(Inventar).filter(
            Inventar.school_id == current_user.school_id,
            Inventar.uniqueid == invId
        ).first()
        user = session.query(User).filter_by(id=inv.user_id).first()
        inv_data = {
            'id': inv.uniqueid,
            'name': inv.name,
            'user': f'{user.nume} {user.prenume}',
            'cant': inv.cant,
            'price': inv.price,
            'total': inv.total_price
        }
    return jsonify(inv_data), 200