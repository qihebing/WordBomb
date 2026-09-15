import os

import eventlet
eventlet.monkey_patch()

from app import app, socketio
from app.room_cleanup import cleanup_abandoned_rooms

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    # The debug reloader's parent must not clean up the serving child's rooms.
    if not debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        try:
            cleanup_abandoned_rooms()
        except Exception:
            app.logger.exception('Startup room cleanup failed; will retry when a room is created')
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)
