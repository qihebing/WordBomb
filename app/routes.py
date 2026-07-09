from flask import jsonify, request
from app import app

@app.route('/')
def index():
    return 'Word Bomb backend is alive'

@app.route('/hello/<name>')
def hello(name):
    return f'Hello, {name}'

@app.route('/ping')
def ping():
    return jsonify({'status': 'ok', 'game': 'word bomb'})

@app.route('/validate', methods=['POST'])
def validate():
    data = request.get_json()
    word = data['word'].lower()
    prompt = data['prompt'].lower()

    contains_prompt = prompt in word

    return jsonify({
        'word': word,
        'prompt': prompt,
        'valid': contains_prompt,
    })