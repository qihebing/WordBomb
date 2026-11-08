import unittest
from unittest.mock import patch

from app import app, socketio, sockets
from app.game_state import (
    advance_turn, current_player, record_timeout, rooms, start_game, sync_players,
)
from app.prompt_difficulty import build_prompt_tiers, get_prompt_tiers


def suffix(number):
    letters = []
    for _ in range(8):
        letters.append('xyz'[number % 3])
        number //= 3
    return ''.join(letters)


class PromptCatalogTests(unittest.TestCase):
    def tearDown(self):
        get_prompt_tiers.cache_clear()

    def test_frequency_boundaries_and_prompt_lengths(self):
        examples = [('ab', 2000), ('cd', 1999), ('ef', 500), ('gh', 499),
                    ('ij', 100), ('kl', 99), ('mn', 25), ('op', 24)]
        words = [prompt + suffix(i) for prompt, count in examples for i in range(count)]
        tiers = build_prompt_tiers(words)
        for index, prompts in enumerate([('ab',), ('cd', 'ef'), ('gh', 'ij'), ('kl', 'mn')]):
            for prompt in prompts:
                self.assertIn(prompt, tiers[index])
        self.assertNotIn('op', {p for tier in tiers for p in tier})
        self.assertTrue(all(len(p) in (2, 3) and p.isascii() and p.isalpha()
                            for tier in tiers for p in tier))

    def test_repeated_occurrences_count_as_one_answer(self):
        words = ['abab' + suffix(i) for i in range(24)]
        tiers = build_prompt_tiers(words + ['ccc' + suffix(100)])
        self.assertNotIn('ab', {p for tier in tiers for p in tier})
        tiers = build_prompt_tiers(words + ['ABAB' + suffix(100)])
        self.assertIn('ab', {p for tier in tiers for p in tier})
        self.assertIn('aba', {p for tier in tiers for p in tier})

    def test_empty_or_too_small_dictionary_is_rejected(self):
        for words in [[], ['cat', 'dog']]:
            with self.assertRaises(ValueError):
                build_prompt_tiers(words)

    def test_catalog_is_read_once_and_cached(self):
        get_prompt_tiers.cache_clear()
        with patch('app.prompt_difficulty.get_connection') as db:
            cursor = db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
            cursor.__iter__.return_value = iter([('ab' + suffix(i),) for i in range(25)])
            first = get_prompt_tiers()
            self.assertIs(get_prompt_tiers(), first)
            db.assert_called_once()
            cursor.execute.assert_called_once_with('SELECT word FROM words')


class DifficultyProgressionTests(unittest.TestCase):
    def setUp(self):
        rooms.clear()
        self.tiers = (('ab',), ('cd',), ('ef',), ('gh',))
        sync_players(1, ['Alice', 'Bob'])
        start_game(1, self.tiers)

    def tearDown(self):
        rooms.clear()

    def test_three_answers_each_promotes_the_next_turn(self):
        for _ in range(5):
            advance_turn(1)
            self.assertEqual(rooms[1]['difficulty'], 0)
            self.assertEqual(rooms[1]['prompt'], 'ab')
        advance_turn(1)
        self.assertEqual(rooms[1]['difficulty'], 1)
        self.assertEqual(rooms[1]['prompt'], 'cd')
        self.assertEqual(rooms[1]['answers_since_loss'], {'Alice': 0, 'Bob': 0})

    def test_three_players_need_nine_answers(self):
        sync_players(1, ['Alice', 'Bob', 'Cara'])
        start_game(1, self.tiers)
        for _ in range(8):
            advance_turn(1)
        self.assertEqual(rooms[1]['difficulty'], 0)
        advance_turn(1)
        self.assertEqual(rooms[1]['difficulty'], 1)

    def test_timeout_resets_progress_without_lowering_difficulty(self):
        for _ in range(10):
            advance_turn(1)
        self.assertEqual(rooms[1]['difficulty'], 1)
        player = current_player(1)
        self.assertEqual(record_timeout(1), (False, None))
        self.assertEqual(rooms[1]['lives'][player], 2)
        self.assertEqual(rooms[1]['difficulty'], 1)
        self.assertTrue(all(count == 0 for count in rooms[1]['answers_since_loss'].values()))
        for _ in range(5):
            advance_turn(1)
        self.assertEqual(rooms[1]['difficulty'], 1)
        advance_turn(1)
        self.assertEqual(rooms[1]['difficulty'], 2)

    def test_elimination_uses_only_surviving_players(self):
        sync_players(1, ['Alice', 'Bob', 'Cara'])
        start_game(1, self.tiers)
        rooms[1]['lives']['Alice'] = 1
        self.assertEqual(record_timeout(1), (True, None))
        self.assertEqual(rooms[1]['alive'], ['Bob', 'Cara'])
        for _ in range(6):
            advance_turn(1)
        self.assertEqual(rooms[1]['difficulty'], 1)

    def test_hardest_tier_is_capped_and_games_are_independent(self):
        sync_players(2, ['Dan', 'Eve'])
        start_game(2, self.tiers)
        for _ in range(30):
            advance_turn(1)
        self.assertEqual(rooms[1]['difficulty'], 3)
        self.assertEqual(rooms[1]['prompt'], 'gh')
        self.assertEqual(rooms[2]['difficulty'], 0)

    def test_missing_dictionary_does_not_mutate_room(self):
        sync_players(2, ['Dan', 'Eve'])
        with patch('app.game_state.get_prompt_tiers', side_effect=ValueError('empty')):
            with self.assertRaises(ValueError):
                start_game(2)
        self.assertEqual(rooms[2]['status'], 'waiting')


class DifficultySocketTests(unittest.TestCase):
    def setUp(self):
        rooms.clear()
        sockets.connections.clear()
        self.db = patch('app.sockets.get_connection').start()
        patch('app.sockets._fetch_players', return_value=['Alice', 'Bob', 'Cara']).start()
        patch('app.sockets.get_prompt_tiers', return_value=(('ab',), ('cd',))).start()
        patch('app.sockets.eventlet.spawn_after').start()
        self.clients = []
        for name in ['Alice', 'Bob', 'Cara']:
            client = socketio.test_client(app)
            client.emit('join', {'game_id': 1, 'player_name': name})
            self.clients.append(client)
        self.clients[0].emit('start_game', {'game_id': 1})

    def tearDown(self):
        for client in self.clients:
            if client.is_connected():
                client.disconnect()
        patch.stopall()
        rooms.clear()
        sockets.connections.clear()

    def test_invalid_and_reused_words_do_not_count(self):
        with patch('app.sockets.check_word', return_value={'valid': False}):
            self.clients[0].emit('submit_word', {'game_id': 1, 'player_name': 'Alice', 'word': 'bad'})
        self.assertEqual(rooms[1]['answers_since_loss']['Alice'], 0)
        rooms[1]['used_words'].add('abc')
        with patch('app.sockets.check_word', return_value={'valid': True, 'word': 'abc'}):
            self.clients[0].emit('submit_word', {'game_id': 1, 'player_name': 'Alice', 'word': 'abc'})
        self.assertEqual(rooms[1]['answers_since_loss']['Alice'], 0)

    def test_departure_resets_progress_and_remaining_players_can_advance(self):
        advance_turn(1)
        self.clients[2].disconnect()
        self.assertEqual(rooms[1]['answers_since_loss'], {'Alice': 0, 'Bob': 0})
        for _ in range(6):
            advance_turn(1)
        self.assertEqual(rooms[1]['difficulty'], 1)

    def test_valid_socket_answers_promote_after_three_per_person(self):
        names = ['Alice', 'Bob', 'Cara']
        for index in range(9):
            name = names[index % 3]
            word = 'answer' + str(index)
            with patch('app.sockets.check_word', return_value={'valid': True, 'word': word}):
                self.clients[index % 3].emit('submit_word', {
                    'game_id': 1, 'player_name': name, 'word': word,
                })
        self.assertEqual(rooms[1]['difficulty'], 1)
        self.assertEqual(rooms[1]['prompt'], 'cd')


if __name__ == '__main__':
    unittest.main()
