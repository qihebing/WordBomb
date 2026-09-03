let gameId = null;
let playerName = null;
let socket = null;
let deadline = null;

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
    el('current-player').textContent = state.current_player;
    deadline = state.deadline;
  } else {
    deadline = null;
  }

  const myTurn = isMyTurn(state);
  el('word-input').disabled = !myTurn;
  el('word-form').querySelector('button').disabled = !myTurn;
  if (myTurn) {
    el('word-input').focus();
  }
}

setInterval(() => {
  if (deadline === null) {
    el('countdown').textContent = '-';
    return;
  }
  const remaining = Math.max(0, deadline - Date.now() / 1000);
  el('countdown').textContent = remaining.toFixed(1);
}, 200);

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
    if (data.eliminated) {
      logLine(`${data.player} ran out of time and is eliminated!`);
    } else {
      logLine(`${data.player} ran out of time (${data.lives_left} ${data.lives_left === 1 ? 'life' : 'lives'} left)`);
    }
  });

  socket.on('game_over', (data) => {
    deadline = null;
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
