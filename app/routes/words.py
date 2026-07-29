import psycopg
from flask import jsonify, request, Blueprint

bp = Blueprint('words', __name__)

CONN_INFO = "host=localhost port=5432 dbname=wordbomb user=postgres password=devpassword"

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

    word = data['word'].lower()
    prompt = data['prompt'].lower()
    contains_prompt = prompt in word

    with psycopg.connect(CONN_INFO) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM words WHERE word = %s", (word,))
            is_real_word = cur.fetchone() is not None

    valid = contains_prompt and is_real_word
    return jsonify({
        'word': word, 'prompt': prompt, 'valid': valid,
        'contains_prompt': contains_prompt, 'is_real_word': is_real_word,
    })