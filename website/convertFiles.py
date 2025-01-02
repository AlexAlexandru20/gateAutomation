from flask import Blueprint, render_template, request, url_for
from flask_login import current_user, login_required

convert = Blueprint('convert', __name__)

@convert.route('/pdf', methods=['POST', 'GET'])
@login_required
def pdf():
    render_template('convert.html')