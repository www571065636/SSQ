from __future__ import annotations

import random


def create_rng(seed: int | None = None) -> random.Random:
    return random.Random(seed)

