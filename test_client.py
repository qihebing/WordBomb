import sys
import socketio

room_id = sys.argv[1] if len(sys.argv) > 1 else 'room1'
player_name = sys.argv[2] if len(sys.argv) > 2 else 'player'

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


@sio.on('word_submitted')
def on_word_submitted(data):
    print('word_submitted:', data)


sio.connect('http://127.0.0.1:5000')
sio.emit('join', {'room_id': room_id, 'player_name': player_name})

print("Type a word and press Enter to submit it. Type 'quit' to exit.")
try:
    while True:
        word = input('> ').strip()
        if word == 'quit':
            break
        sio.emit('submit_word', {'room_id': room_id, 'player_name': player_name, 'word': word})
finally:
    sio.disconnect()
