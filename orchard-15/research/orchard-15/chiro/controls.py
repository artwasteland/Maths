"""Sourced control incidence structures for chirosat.py.

Point labels are normalized to 0 through v-1 and blocks are sorted.  The two
STS(13) lists and the (16,37) list are transcribed from Kühne, Szemberg and
Tutaj-Gasinska, arXiv:2401.14766v1, pages 7 and 8.

KANTOR_10 is Grünbaum's configuration (10_3)_4.  The incidence table is in
Configurations of Points and Lines, Graduate Studies in Mathematics 103,
AMS, 2009, Figure 1.2.2 and the configuration table discussed in Section 2.2.
The same drawing is Figure 1 (center) of Bokowski and Pilaud,
"Enumerating topological (n_k)-configurations", arXiv:1210.0306.
"""

from __future__ import annotations

import itertools

from chirosat import PTS


def pts(v: int, blocks: list[tuple[int, int, int]]) -> PTS:
    return PTS(v, tuple(sorted(blocks)))


FANO = pts(
    7,
    [
        (0, 1, 2), (0, 3, 4), (0, 5, 6), (1, 3, 5),
        (1, 4, 6), (2, 3, 6), (2, 4, 5),
    ],
)

PAPPUS = pts(
    9,
    [
        (0, 1, 2), (0, 4, 6), (0, 5, 7), (1, 3, 6), (1, 5, 8),
        (2, 3, 7), (2, 4, 8), (3, 4, 5), (6, 7, 8),
    ],
)

# Points are the ten 2-subsets of a 5-set.  Blocks are the three 2-subsets
# contained in each 3-subset, the standard combinatorial Desargues model.
_PAIRS_5 = list(itertools.combinations(range(5), 2))
DESARGUES = pts(
    10,
    [
        tuple(_PAIRS_5.index(pair) for pair in itertools.combinations(three, 2))
        for three in itertools.combinations(range(5), 3)
    ],
)

KANTOR_10 = pts(
    10,
    [
        (0, 4, 6), (0, 5, 7), (0, 8, 9), (1, 2, 3), (1, 4, 5),
        (1, 6, 7), (2, 4, 8), (2, 5, 9), (3, 6, 8), (3, 7, 9),
    ],
)

STS13_A = pts(
    13,
    [
        (0, 1, 2), (0, 3, 4), (0, 5, 6), (0, 7, 8), (0, 9, 10),
        (0, 11, 12), (1, 3, 5), (1, 4, 7), (1, 6, 8), (1, 9, 11),
        (1, 10, 12), (2, 3, 9), (2, 4, 5), (2, 6, 10), (2, 7, 12),
        (2, 8, 11), (3, 6, 11), (3, 7, 10), (3, 8, 12), (4, 6, 12),
        (4, 8, 9), (4, 10, 11), (5, 7, 11), (5, 8, 10), (5, 9, 12),
        (6, 7, 9),
    ],
)

STS13_B = pts(
    13,
    [
        (0, 1, 2), (0, 3, 4), (0, 5, 6), (0, 7, 8), (0, 9, 10),
        (0, 11, 12), (1, 3, 5), (1, 4, 7), (1, 6, 8), (1, 9, 11),
        (1, 10, 12), (2, 3, 9), (2, 4, 5), (2, 6, 10), (2, 7, 11),
        (2, 8, 12), (3, 6, 11), (3, 7, 12), (3, 8, 10), (4, 6, 12),
        (4, 8, 9), (4, 10, 11), (5, 7, 10), (5, 8, 11), (5, 9, 12),
        (6, 7, 9),
    ],
)


def zero_sum_mod_15() -> PTS:
    blocks = [
        triple
        for triple in itertools.combinations(range(15), 3)
        if sum(triple) % 15 == 0
    ]
    assert len(blocks) == 31
    return pts(15, blocks)


PEGG_15_31 = zero_sum_mod_15()

KUHNE_16_37 = pts(
    16,
    [
        (0, 7, 8), (0, 6, 9), (0, 5, 10), (0, 4, 11), (0, 3, 12),
        (0, 2, 13), (0, 1, 14), (1, 6, 8), (1, 5, 9), (1, 4, 10),
        (1, 3, 11), (1, 2, 12), (1, 7, 15), (2, 6, 7), (2, 5, 8),
        (2, 4, 9), (2, 3, 10), (2, 11, 15), (3, 5, 7), (3, 4, 8),
        (3, 13, 14), (3, 9, 15), (4, 5, 6), (4, 12, 14), (4, 13, 15),
        (5, 12, 13), (5, 11, 14), (6, 11, 13), (6, 10, 14), (6, 12, 15),
        (7, 11, 12), (7, 10, 13), (7, 9, 14), (8, 10, 12), (8, 9, 13),
        (8, 14, 15), (9, 10, 11),
    ],
)


CONTROLS = {
    "fano": (FANO, "no-pseudoline"),
    "pappus": (PAPPUS, "pseudoline"),
    "desargues": (DESARGUES, "pseudoline"),
    "kantor10": (KANTOR_10, "pseudoline"),
    "sts13-a": (STS13_A, "no-pseudoline"),
    "sts13-b": (STS13_B, "no-pseudoline"),
    "pegg15": (PEGG_15_31, "pseudoline"),
    "kuhne16": (KUHNE_16_37, "pseudoline"),
}
