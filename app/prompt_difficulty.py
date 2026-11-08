"""Dictionary-derived prompt pools, cached for the lifetime of the server."""
from collections import Counter
from functools import lru_cache

from app.db import get_connection

# Minimum number of matching dictionary words, easiest tier first.
TIER_MIN_MATCHES = (2000, 500, 100, 25)


def build_prompt_tiers(words):
    counts = Counter()
    for word in words:
        word = word.strip().lower()
        # Repeated occurrences in one word still represent only one answer.
        prompts = {
            word[index:index + length]
            for length in (2, 3)
            for index in range(len(word) - length + 1)
            if word[index:index + length].isascii()
            and word[index:index + length].isalpha()
        }
        counts.update(prompts)

    tiers = [[] for _ in TIER_MIN_MATCHES]
    for prompt, count in sorted(counts.items()):
        for index, minimum in enumerate(TIER_MIN_MATCHES):
            if count >= minimum:
                tiers[index].append(prompt)
                break
    # Small/custom dictionaries may not populate every tier.
    pools = tuple(tuple(tier) for tier in tiers if tier)
    if not pools:
        raise ValueError('The dictionary needs a prompt with at least 25 matching words.')
    return pools


@lru_cache(maxsize=1)
def get_prompt_tiers():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT word FROM words')
            return build_prompt_tiers(row[0] for row in cur)
