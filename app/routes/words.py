from flask import jsonify, request, Blueprint

from app.word_validation import check_word

bp = Blueprint('words', __name__)

@bp.route('/')
def index():
    return 'Word Bomb backend is alive'

@bp.route('/hello/<name>')
def hello(name):
    return f'Hello, {name}'

@bp.route('/ping')
def ping():
    return jsonify({'status': 'ok', 'game': 'word bomb'})

@bp.route('/validate', methods=['POST'])
def validate():
    data = request.get_json(silent=True)
    if not data or 'word' not in data or 'prompt' not in data:
        return jsonify({'error': 'request body must include word and prompt'}), 400

    return jsonify(check_word(data['word'], data['prompt']))