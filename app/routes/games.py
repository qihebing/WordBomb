import psycopg
from flask import jsonify, request, Blueprint
from app.db import get_connection
from app.room_cleanup import cleanup_abandoned_rooms

bp = Blueprint('games', __name__)


@bp.route('/games', methods=['POST'])
def create_game():
    cleanup_abandoned_rooms()
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Serialize allocation so simultaneous creates cannot select the same gap.
            cur.execute('LOCK TABLE games IN EXCLUSIVE MODE')
            cur.execute(
                """INSERT INTO games (id, status)
                SELECT MIN(candidate), 'waiting'
                FROM (
                    SELECT 1 AS candidate
                    UNION ALL
                    SELECT id + 1 FROM games
                ) AS candidates
                WHERE NOT EXISTS (SELECT 1 FROM games WHERE id = candidate)
                RETURNING id, status, created_at"""
            )
            game_id, status, created_at = cur.fetchone()

    return jsonify({
        'id': game_id,
        'status': status,
        'created_at': created_at.isoformat(),
    }), 201


@bp.route('/games/<int:game_id>', methods=['GET'])
def get_game(game_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, status, created_at FROM games WHERE id = %s", (game_id,)
            )
            game = cur.fetchone()
            if game is None:
                return jsonify({'error': 'game not found'}), 404

            cur.execute(
                "SELECT id, name, joined_at FROM players WHERE game_id = %s ORDER BY joined_at",
                (game_id,),
            )
            players = cur.fetchall()

    return jsonify({
        'id': game[0],
        'status': game[1],
        'created_at': game[2].isoformat(),
        'players': [
            {'id': p[0], 'name': p[1], 'joined_at': p[2].isoformat()}
            for p in players
        ],
    })


@bp.route('/games/<int:game_id>/join', methods=['POST'])
def join_game(game_id):
    data = request.get_json(silent=True)
    if not data or not data.get('name'):
        return jsonify({'error': 'request body must include name'}), 400

    name = data['name']

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM games WHERE id = %s", (game_id,))
            if cur.fetchone() is None:
                return jsonify({'error': 'game not found'}), 404

            try:
                cur.execute(
                    "INSERT INTO players (game_id, name) VALUES (%s, %s) RETURNING id, joined_at",
                    (game_id, name),
                )
            except psycopg.errors.UniqueViolation:
                conn.rollback()
                return jsonify({'error': f'name "{name}" is already taken in this game'}), 409

            player_id, joined_at = cur.fetchone()

    return jsonify({
        'id': player_id,
        'game_id': game_id,
        'name': name,
        'joined_at': joined_at.isoformat(),
    }), 201
