from flask import Blueprint, jsonify, request

from app.word_validation import check_word

bp = Blueprint('validation', __name__)


@bp.route('/validate', methods=['POST'])
def validate():
    data = request.get_json(silent=True)
    if not data or 'word' not in data or 'prompt' not in data:
        return jsonify({'error': 'request body must include word and prompt'}), 400

    return jsonify(check_word(data['word'], data['prompt']))
