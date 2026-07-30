from app.db import get_connection


def is_real_word(word):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM words WHERE word = %s", (word,))
            return cur.fetchone() is not None


def check_word(word, prompt):
    word = word.lower().strip()
    prompt = prompt.lower()
    contains_prompt = prompt in word
    real_word = is_real_word(word)
    return {
        'word': word,
        'prompt': prompt,
        'valid': contains_prompt and real_word,
        'contains_prompt': contains_prompt,
        'is_real_word': real_word,
    }
