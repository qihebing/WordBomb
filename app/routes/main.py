from flask import Blueprint, jsonify, render_template

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/hello/<name>')
def hello(name):
    return f'Hello, {name}'


@bp.route('/ping')
def ping():
    return jsonify({'status': 'ok', 'game': 'word bomb'})
