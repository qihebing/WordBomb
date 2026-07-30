import random

TURN_SECONDS = 15

# Letter combos common enough that plenty of real words contain them.
PROMPTS = [
    'th', 'er', 'an', 'in', 'on', 'at', 'en', 'es', 'or', 'is',
    'it', 'al', 'ar', 'st', 'to', 'nt', 'ng', 'se', 'ha', 'as',
    'ou', 'io', 'le', 'ed', 'ct', 'ur', 'ss', 'ing', 'ent', 'ate',
]

rooms = {}


def _new_room():
    return {
        'players': [],       # cached from the DB, ordered by joined_at
        'status': 'waiting',
        'turn_order': [],    # frozen player order once the game starts
        'turn_index': 0,
        'deadline': None,    # unix timestamp the current turn expires at
        'timer': None,       # eventlet GreenThread for the pending timeout
        'prompt': None,      # letter combo the current word must contain
    }


def new_prompt():
    return random.choice(PROMPTS)


def get_room(game_id):
    return rooms.get(game_id)


def sync_players(game_id, players):
    room = rooms.setdefault(game_id, _new_room())
    room['players'] = players
    return room


def start_game(game_id):
    room = rooms[game_id]
    room['status'] = 'in_progress'
    room['turn_order'] = list(room['players'])
    room['turn_index'] = 0
    room['prompt'] = new_prompt()
    return room


def current_player(game_id):
    room = rooms[game_id]
    if not room['turn_order']:
        return None
    return room['turn_order'][room['turn_index'] % len(room['turn_order'])]


def advance_turn(game_id):
    room = rooms[game_id]
    room['turn_index'] += 1
    room['prompt'] = new_prompt()
    return current_player(game_id)


def cancel_timer(game_id):
    room = rooms[game_id]
    if room['timer'] is not None:
        room['timer'].cancel()
        room['timer'] = None
