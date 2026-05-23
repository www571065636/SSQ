from __future__ import annotations

from collections import Counter


PRIME_NUMBERS = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31}


def odd_even_ratio(numbers: list[int]) -> str:
    odd = sum(1 for value in numbers if value % 2 == 1)
    return f"{odd}:{len(numbers) - odd}"


def big_small_ratio(numbers: list[int], split: int = 16) -> str:
    small = sum(1 for value in numbers if value <= split)
    return f"{small}:{len(numbers) - small}"


def zone_ratio(numbers: list[int]) -> str:
    zone1 = sum(1 for value in numbers if 1 <= value <= 11)
    zone2 = sum(1 for value in numbers if 12 <= value <= 22)
    zone3 = len(numbers) - zone1 - zone2
    return f"{zone1}:{zone2}:{zone3}"


def consecutive_pair_count(numbers: list[int]) -> int:
    ordered = sorted(numbers)
    return sum(1 for index in range(len(ordered) - 1) if ordered[index + 1] - ordered[index] == 1)


def span_value(numbers: list[int]) -> int:
    ordered = sorted(numbers)
    return ordered[-1] - ordered[0]


def ac_value(numbers: list[int]) -> int:
    ordered = sorted(numbers)
    differences = {
        ordered[right] - ordered[left]
        for left in range(len(ordered) - 1)
        for right in range(left + 1, len(ordered))
    }
    return len(differences) - (len(ordered) - 1)


def repeat_count(numbers: list[int], reference: list[int] | None) -> int:
    if not reference:
        return 0
    return len(set(numbers) & set(reference))


def tail_variety(numbers: list[int]) -> int:
    return len({value % 10 for value in numbers})


def prime_composite_ratio(numbers: list[int]) -> str:
    prime_count = sum(1 for value in numbers if value in PRIME_NUMBERS)
    return f"{prime_count}:{len(numbers) - prime_count}"


def route_012_ratio(numbers: list[int]) -> str:
    counts = Counter(value % 3 for value in numbers)
    return f"{counts.get(0, 0)}:{counts.get(1, 0)}:{counts.get(2, 0)}"


def feature_map(numbers: list[int], previous_numbers: list[int] | None = None) -> dict[str, int | str]:
    return {
        "odd_even": odd_even_ratio(numbers),
        "big_small": big_small_ratio(numbers),
        "zones": zone_ratio(numbers),
        "consecutive_pairs": consecutive_pair_count(numbers),
        "span": span_value(numbers),
        "ac": ac_value(numbers),
        "repeat_with_prev": repeat_count(numbers, previous_numbers),
        "tail_variety": tail_variety(numbers),
        "prime_composite": prime_composite_ratio(numbers),
        "route_012": route_012_ratio(numbers),
    }
