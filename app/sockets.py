import time

import eventlet
from flask_socketio import join_room, emit

from app import socketio
from app.db import get_connection
from app.game_state import (
    TURN_SECONDS,
    advance_turn,
    cancel_timer,
    current_player,
    end_game,
    get_room,
    is_word_used,
    mark_word_used,
    record_timeout,
    start_game,
    sync_players,
)
from app.word_validation import check_word


def _fetch_players(game_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM games WHERE id = %s", (game_id,))
            if cur.fetchone() is None:
                return None
            cur.execute(
                "SELECT name FROM players WHERE game_id = %s ORDER BY joined_at", (game_id,)
            )
            return [row[0] for row in cur.fetchall()]


def _room_state(game_id):
    room = get_room(game_id)
    state = {'game_id': game_id, 'players': room['players'], 'status': room['status']}
    if room['status'] == 'in_progress':
        state['current_player'] = current_player(game_id)
        state['deadline'] = room['deadline']
        state['prompt'] = room['prompt']
        state['alive'] = room['alive']
        state['lives'] = room['lives']
    return state


def _start_timer(game_id):
    room = get_room(game_id)
    room['deadline'] = time.time() + TURN_SECONDS
    room['timer'] = eventlet.spawn_after(TURN_SECONDS, _handle_timeout, game_id)


def _schedule_turn(game_id):
    _start_timer(game_id)
    socketio.emit('turn_update', _room_state(game_id), room=str(game_id))


def _finish_game(game_id, winner):
    room = get_room(game_id)
    cancel_timer(game_id)
    end_game(game_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE games SET status = 'finished' WHERE id = %s", (game_id,))
    socketio.emit(
        'game_over', {'winner': winner, 'lives': room['lives']}, room=str(game_id)
    )


def _handle_timeout(game_id):
    room = get_room(game_id)
    if room is None or room['status'] != 'in_progress':
        return

    timed_out_player = current_player(game_id)
    eliminated, winner = record_timeout(game_id)
    socketio.emit(
        'turn_timeout',
        {
            'player': timed_out_player,
            'eliminated': eliminated,
            'lives_left': room['lives'][timed_out_player],
        },
        room=str(game_id),
    )

    if winner is not None:
        _finish_game(game_id, winner)
        return

    _schedule_turn(game_id)


@socketio.on('join')
def handle_join(data):
    game_id = data['game_id']
    player_name = data['player_name']

    players = _fetch_players(game_id)
    if players is None:
        emit('error', {'error': 'game not found'})
        return
    if player_name not in players:
        emit('error', {'error': 'join the game via POST /games/<id>/join before connecting'})
        return

    join_room(str(game_id))
    sync_players(game_id, players)
    emit('room_update', _room_state(game_id), room=str(game_id))


@socketio.on('start_game')
def handle_start_game(data):
    game_id = data['game_id']
    room = get_room(game_id)
    if room is None:
        emit('error', {'error': 'join the room before starting it'})
        return
    if room['status'] != 'waiting':
        emit('error', {'error': f"game is already {room['status']}"})
        return
    if len(room['players']) < 2:
        emit('error', {'error': 'need at least 2 players to start'})
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE games SET status = 'in_progress' WHERE id = %s", (game_id,))

    start_game(game_id)
    _start_timer(game_id)
    emit('game_started', _room_state(game_id), room=str(game_id))


@socketio.on('submit_word')
def handle_submit_word(data):
    game_id = data['game_id']
    player_name = data.get('player_name')
    word = data.get('word', '')

    room = get_room(game_id)
    if room is None or room['status'] != 'in_progress':
        emit('error', {'error': 'game is not in progress'})
        return
    if player_name != current_player(game_id):
        emit('error', {'error': 'not your turn'})
        return

    result = check_word(word, room['prompt'])
    if result['valid'] and is_word_used(game_id, result['word']):
        result['valid'] = False
        result['already_used'] = True
    if not result['valid']:
        emit('invalid_word', result)
        return

    mark_word_used(game_id, result['word'])
    cancel_timer(game_id)
    emit(
        'word_submitted',
        {'player': player_name, 'word': result['word'], 'prompt': room['prompt']},
        room=str(game_id),
    )
    advance_turn(game_id)
    _schedule_turn(game_id)
