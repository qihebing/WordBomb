from flask_socketio import join_room, emit
from app import socketio
from app.game_state import join_room_state, get_room

@socketio.on('join')
def handle_join(data):
    room_id = data['room_id']
    player_name = data['player_name']

    join_room(room_id)
    join_room_state(room_id, player_name)

    emit('room_update', get_room(room_id), room=room_id)

@socketio.on('submit_word')
def handle_submit_word(data):
    room_id = data['room_id']
    word = data['word']

    emit('word_submitted', {'player': data.get('player_name'), 'word': word}, room=room_id)