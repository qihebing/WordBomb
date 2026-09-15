# Word Bomb

A real-time multiplayer word game: players take turns typing a real word containing a given letter combination before a server-driven timer runs out. Miss the deadline three times and you're eliminated — last player standing wins.

**Live demo:** [word-bomb.up.railway.app](https://word-bomb.up.railway.app/)

Open it in two browser tabs (or send the link to a friend) to actually play — it's a multiplayer game, so a single tab will just sit in the lobby waiting for a second player.

## What it does

- Create a game, share the game ID, join from another browser.
- Real-time lobby and turn state pushed to every connected player over WebSockets — no polling, no manual refresh.
- Each turn gives you a letter combination (e.g. `th`, `ing`, `at`); submit any real English word containing it before the clock runs out.
- Word validity is checked against a ~172,000-word dictionary (the ENABLE word list) on every submission.
- A word can't be reused within the same game once it's been played.
- 3 lives per player. Timing out costs a life; running out of lives eliminates you. Last player remaining wins.

## Tech stack

| Piece | Choice | Why |
|---|---|---|
| Backend | Flask + Flask-SocketIO | Flask-SocketIO's "room" abstraction maps directly onto game lobbies |
| Async server | eventlet | Required for Flask-SocketIO to hold WebSocket connections open |
| Database | PostgreSQL, raw `psycopg` (no ORM) | Deliberate choice to keep SQL and query plans visible while learning — not an oversight |
| Live game/room state | In-memory Python dict, not the database | Turn order and timers change many times per second; the database holds only durable state (accounts, dictionary) |
| Frontend | Vanilla JS/HTML/CSS, no framework | The frontend is a thin layer over a JSON/WebSocket API — doesn't need React/Vue at this scale |
| Deployment | Railway | Managed Postgres and native WebSocket proxy support in one place |

## Architecture

**REST API** (game/player setup — synchronous, backed by Postgres):

| Endpoint | Purpose |
|---|---|
| `POST /games` | Create a new game |
| `GET /games/<id>` | Fetch game status and roster |
| `POST /games/<id>/join` | Join a game by name |
| `POST /validate` | Check a word against the dictionary + a prompt (standalone, outside a live game) |

**WebSocket events** (live gameplay — in-memory room state, broadcast to everyone in the room):

| Client → Server | Server → Client |
|---|---|
| `join` | `room_update`, `error` |
| `start_game` | `game_started` |
| `submit_word` | `word_submitted`, `invalid_word`, `turn_update`, `turn_timeout`, `game_over` |

A player joins a game via the REST API first (so the roster is durable), then connects a socket and emits `join` to attach to that game's live room. From there, all turn state — whose turn it is, the current prompt, the countdown deadline, remaining lives — is server-authoritative and pushed to every client in the room.

## Running it locally

### Room lifetime

When the last connected player leaves or disconnects, the server deletes the game
and its player records and cancels its timer. New games use the lowest available
positive room ID. Multiple sockets for the same player keep that player present
until their last socket leaves. A lost network connection is cleaned up when
Socket.IO detects the disconnect; players can also use **Leave game**.
Disconnected players must join again. Cleanup runs once at server startup
and before creating each new room. It deletes rooms older than five minutes with no connected
sockets, including rooms that never connected and records left by a server crash.
Connected rooms are preserved regardless of age. Deleted rooms release their IDs
and cascade-delete player records. Start the server with `python run.py` to run
startup cleanup. Existing abandoned records are cleaned on that pass or the next
room creation. There is no periodic database polling while the app is idle.
Connection tracking, like gameplay state, assumes a single server process.

Requires Python 3.13+ and Docker.

```powershell
git clone https://github.com/qihebing/WordBomb.git
cd WordBomb
python -m venv venv
venv\Scripts\pip install -r requirements.txt

# Postgres in Docker
docker run -d --name wordbomb-db -e POSTGRES_PASSWORD=devpassword -e POSTGRES_DB=wordbomb -p 5432:5432 postgres:16

# Apply schema and load the dictionary
venv\Scripts\python scripts\init_schema.py
venv\Scripts\python scripts\load_words.py path\to\enable1.txt

# Run the app
venv\Scripts\python run.py
```

Then open `http://localhost:5000`. The ENABLE word list isn't bundled in this repo (it's a large third-party wordlist); grab a copy of `enable1.txt` before running `load_words.py`.

## Project status

Full game loop is implemented and deployed: real-time lobby, turn order, server-driven timers, live dictionary validation, word-reuse blocking, lives/elimination, and win condition. Verified end-to-end against a real Postgres instance and real Socket.IO clients before deploying.

Open for further iteration: page styling, reconnect/disconnect handling for dropped players, and a rematch flow without needing a fresh URL.

## About

Built by qihebing — Penn CS, Class of 2028. Systems programming background (PennFAT, PennOS, an LC4 simulator) and ML research experience (JAX/Flax, physics-informed neural networks), building this project to add real-time backend and database experience alongside that.

- GitHub: [github.com/qihebing](https://github.com/qihebing)
- LinkedIn: [linkedin.com/in/qihecui](https://linkedin.com/in/qihecui)
- Email: qihecui2023@gmail.com

## License

MIT — see [LICENSE](LICENSE).
