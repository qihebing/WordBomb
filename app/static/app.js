let gameId = null;
let playerName = null;
let socket = null;
let fuseTurn = null;
let boomUntil = 0;
let boomPlayer = null;

const el = (id) => document.getElementById(id);

function logLine(text) {
  const li = document.createElement('li');
  li.textContent = text;
  el('log').prepend(li);
}

function isMyTurn(state) {
  return state.status === 'in_progress' && state.current_player === playerName;
}

function renderRoomState(state) {
  el('status').textContent = state.status;

  el('players').innerHTML = '';
  for (const name of state.players) {
    const li = document.createElement('li');
    let text = name;
    if (state.status === 'in_progress') {
      if (!state.alive.includes(name)) {
        text += ' — eliminated';
      } else {
        const lives = state.lives[name];
        text += ` — ${lives} ${lives === 1 ? 'life' : 'lives'}`;
        if (name === state.current_player) {
          text += ' (current turn)';
        }
      }
    }
    li.textContent = text;
    el('players').appendChild(li);
  }

  el('start-btn').hidden = state.status !== 'waiting';

  const inProgress = state.status === 'in_progress';
  el('turn-info').hidden = !inProgress;
  if (inProgress) {
    el('prompt').textContent = state.prompt;
    fuseTurn = {
      player: state.current_player,
      startedAt: state.turn_started_at,
    };
  } else {
    fuseTurn = null;
  }
  renderFuse();

  const myTurn = isMyTurn(state);
  el('word-input').disabled = !myTurn;
  el('word-form').querySelector('button').disabled = !myTurn;
  if (myTurn) {
    el('word-input').focus();
  }
}

function renderFuse() {
  const exploding = Date.now() < boomUntil;
  el('fuse-display').hidden = !exploding && fuseTurn === null;
  if (!exploding && fuseTurn === null) return;

  const name = exploding ? boomPlayer : fuseTurn.player;
  el('fuse-label').textContent = `The fuse is lit for ${name}.`;
  el('fuse-line').classList.toggle('boom', exploding);
  if (exploding) {
    el('fuse-line').textContent = 'BOOM!';
    return;
  }

  // Burn for ten seconds, then keep two segments until the server times out.
  const elapsed = Math.max(0, Date.now() / 1000 - fuseTurn.startedAt);
  const burned = Math.floor(Math.min(elapsed / 10, 1) * 22);
  el('fuse-line').textContent = `${' '.repeat(burned)}*${'-'.repeat(24 - burned)}`;
}

setInterval(renderFuse, 100);

async function joinGame() {
  el('lobby-error').textContent = '';

  const name = el('name-input').value.trim();
  const gameIdInput = el('game-id-input').value.trim();

  if (!name) {
    el('lobby-error').textContent = 'name is required';
    return;
  }

  try {
    if (gameIdInput) {
      gameId = parseInt(gameIdInput, 10);
    } else {
      const resp = await fetch('/games', { method: 'POST' });
      const data = await resp.json();
      gameId = data.id;
    }

    const joinResp = await fetch(`/games/${gameId}/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    const joinData = await joinResp.json();
    if (!joinResp.ok) {
      el('lobby-error').textContent = joinData.error || 'failed to join';
      return;
    }
  } catch (err) {
    el('lobby-error').textContent = 'could not reach server';
    return;
  }

  playerName = name;
  el('game-id-display').textContent = gameId;
  el('lobby').hidden = true;
  el('game').hidden = false;

  socket = io();
  socket.on('disconnect', () => {
    socket.disconnect();
    gameId = null;
    playerName = null;
    fuseTurn = null;
    boomUntil = 0;
    boomPlayer = null;
    renderFuse();
    el('game').hidden = true;
    el('lobby').hidden = false;
    el('game-over').hidden = true;
    el('log').innerHTML = '';
    el('lobby-error').textContent = 'You left the game. Join again to play.';
  });

  socket.on('room_update', renderRoomState);
  socket.on('game_started', renderRoomState);
  socket.on('turn_update', renderRoomState);

  socket.on('word_submitted', (data) => {
    logLine(`${data.player} played "${data.word}" (prompt was "${data.prompt}")`);
  });

  socket.on('invalid_word', (data) => {
    if (data.already_used) {
      el('word-error').textContent = `"${data.word}" was already used this game`;
    } else {
      el('word-error').textContent = `"${data.word}" is invalid (real word: ${data.is_real_word}, contains "${data.prompt}": ${data.contains_prompt})`;
    }
  });

  socket.on('turn_timeout', (data) => {
    boomPlayer = data.player;
    boomUntil = Date.now() + 1000;
    renderFuse();
    if (data.eliminated) {
      logLine(`${data.player} ran out of time and is eliminated!`);
    } else {
      logLine(`${data.player} ran out of time (${data.lives_left} ${data.lives_left === 1 ? 'life' : 'lives'} left)`);
    }
  });

  socket.on('game_over', (data) => {
    fuseTurn = null;
    renderFuse();
    el('status').textContent = 'finished';
    el('turn-info').hidden = true;
    el('start-btn').hidden = true;
    el('word-input').disabled = true;
    el('word-form').querySelector('button').disabled = true;
    el('game-over').hidden = false;
    el('winner-text').textContent = `${data.winner} wins!`;
    logLine(`${data.winner} wins the game!`);
  });

  socket.on('error', (data) => {
    logLine(`error: ${data.error}`);
  });

  socket.emit('join', { game_id: gameId, player_name: playerName });
}

el('join-btn').addEventListener('click', joinGame);
el('leave-btn').addEventListener('click', () => socket.disconnect());

el('start-btn').addEventListener('click', () => {
  socket.emit('start_game', { game_id: gameId });
});

el('word-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const word = el('word-input').value.trim();
  if (!word) return;
  el('word-error').textContent = '';
  socket.emit('submit_word', { game_id: gameId, player_name: playerName, word });
  el('word-input').value = '';
});
