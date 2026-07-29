-- words table is loaded separately from enable1.txt; IF NOT EXISTS keeps this script idempotent.
CREATE TABLE IF NOT EXISTS words (
    word TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS games (
    id SERIAL PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'waiting' CHECK (status IN ('waiting', 'in_progress', 'finished')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (game_id, name)
);

CREATE INDEX IF NOT EXISTS players_game_id_idx ON players(game_id);
