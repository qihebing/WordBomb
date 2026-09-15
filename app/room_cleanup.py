"""Room expiry for the single-process game server."""
from functools import wraps

from eventlet.semaphore import Semaphore

from app.db import get_connection
from app.game_state import cancel_timer, rooms

UNCONNECTED_ROOM_SECONDS = 300
membership_lock = Semaphore()


def serialize_membership(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        with membership_lock:
            return handler(*args, **kwargs)
    return wrapped


def cleanup_abandoned_rooms():
    # Import here to avoid a circular import during socket registration.
    from app.sockets import connections

    with membership_lock:
        occupied_ids = list({game_id for game_id, _ in connections.values()})
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """DELETE FROM games
                    WHERE created_at < now() - (%s * interval '1 second')
                      AND NOT (id = ANY(%s::integer[]))
                    RETURNING id""",
                    (UNCONNECTED_ROOM_SECONDS, occupied_ids),
                )
                deleted_ids = [row[0] for row in cur.fetchall()]
        for game_id in deleted_ids:
            if game_id in rooms:
                cancel_timer(game_id)
                rooms.pop(game_id)
        return deleted_ids
