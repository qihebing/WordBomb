import sys

import requests
import socketio

BASE_URL = 'http://127.0.0.1:5000'

game_id_arg = sys.argv[1] if len(sys.argv) > 1 else 'new'
player_name = sys.argv[2] if len(sys.argv) > 2 else 'player'

if game_id_arg == 'new':
    resp = requests.post(f'{BASE_URL}/games')
    resp.raise_for_status()
    game_id = resp.json()['id']
    print(f'[created game {game_id}]')
else:
    game_id = int(game_id_arg)

join_resp = requests.post(f'{BASE_URL}/games/{game_id}/join', json={'name': player_name})
if join_resp.status_code not in (201, 409):
    join_resp.raise_for_status()

sio = socketio.Client()


@sio.event
def connect():
    print(f'[connected as {player_name}]')


@sio.event
def disconnect():
    print('[disconnected]')


@sio.on('room_update')
def on_room_update(data):
    print('room_update:', data)


@sio.on('game_started')
def on_game_started(data):
    print('game_started:', data)


@sio.on('turn_update')
def on_turn_update(data):
    print('turn_update:', data)


@sio.on('turn_timeout')
def on_turn_timeout(data):
    print('turn_timeout:', data)


@sio.on('word_submitted')
def on_word_submitted(data):
    print('word_submitted:', data)


@sio.on('error')
def on_error(data):
    print('error:', data)


sio.connect(BASE_URL)
sio.emit('join', {'game_id': game_id, 'player_name': player_name})

print(f"Game id: {game_id}. Type 'start' to start the game, a word to submit it, or 'quit' to exit.")
try:
    while True:
        line = input('> ').strip()
        if line == 'quit':
            break
        if line == 'start':
            sio.emit('start_game', {'game_id': game_id})
            continue
        sio.emit('submit_word', {'game_id': game_id, 'player_name': player_name, 'word': line})
finally:
    sio.disconnect()
