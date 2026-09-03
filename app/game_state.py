import random

TURN_SECONDS = 15
STARTING_LIVES = 3

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
        'turn_order': [],    # frozen full roster once the game starts
        'alive': [],         # players still in the game, shrinks as lives run out
        'turn_index': 0,
        'lives': {},         # player -> remaining lives
        'used_words': set(),
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
    room['alive'] = list(room['players'])
    room['turn_index'] = 0
    room['lives'] = {p: STARTING_LIVES for p in room['players']}
    room['used_words'] = set()
    room['prompt'] = new_prompt()
    return room


def current_player(game_id):
    room = rooms[game_id]
    if not room['alive']:
        return None
    return room['alive'][room['turn_index'] % len(room['alive'])]


def advance_turn(game_id):
    """Move to the next alive player after a successful word. No life lost."""
    room = rooms[game_id]
    room['turn_index'] = (room['turn_index'] + 1) % len(room['alive'])
    room['prompt'] = new_prompt()
    return current_player(game_id)


def record_timeout(game_id):
    """Charge the current player a life for running out the clock.

    Returns (eliminated, winner): `eliminated` is True if this timeout
    knocked the player out, `winner` is the remaining player's name once
    only one is left, else None.
    """
    room = rooms[game_id]
    idx = room['turn_index'] % len(room['alive'])
    player = room['alive'][idx]
    room['lives'][player] -= 1

    if room['lives'][player] > 0:
        room['turn_index'] = (idx + 1) % len(room['alive'])
        room['prompt'] = new_prompt()
        return False, None

    room['alive'].pop(idx)
    if len(room['alive']) <= 1:
        winner = room['alive'][0] if room['alive'] else None
        return True, winner

    room['turn_index'] = idx % len(room['alive'])
    room['prompt'] = new_prompt()
    return True, None


def is_word_used(game_id, word):
    return word in rooms[game_id]['used_words']


def mark_word_used(game_id, word):
    rooms[game_id]['used_words'].add(word)


def end_game(game_id):
    room = rooms[game_id]
    room['status'] = 'finished'
    return room


def cancel_timer(game_id):
    room = rooms[game_id]
    if room['timer'] is not None:
        room['timer'].cancel()
        room['timer'] = None
