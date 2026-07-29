rooms = {}

def join_room_state(room_id, player_name):
    rooms.setdefault(room_id, {"players": []})
    rooms[room_id]["players"].append(player_name)

def get_room(room_id):
    return rooms.get(room_id)