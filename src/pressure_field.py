"""Pressure field computation for the attentional-distance audit (G10)."""

from dataclasses import dataclass
from typing import Dict

import chess


@dataclass
class SquarePressure:
    white_attackers: int
    black_attackers: int
    net_pressure: int


def compute_pressure_field(board: chess.Board) -> Dict[int, SquarePressure]:
    """Count attackers of each colour on every square."""
    field: Dict[int, SquarePressure] = {}
    for sq in chess.SQUARES:
        w = len(board.attackers(chess.WHITE, sq))
        b = len(board.attackers(chess.BLACK, sq))
        field[sq] = SquarePressure(w, b, w - b)
    return field


def net_pressure(board: chess.Board) -> Dict[int, int]:
    field = compute_pressure_field(board)
    return {sq: p.net_pressure for sq, p in field.items()}


def pressure_in_region(board: chess.Board, squares) -> int:
    total = 0
    for sq in squares:
        if 0 <= sq < 64:
            total += len(board.attackers(chess.WHITE, sq))
            total += len(board.attackers(chess.BLACK, sq))
    return total


def is_low_pressure_zone(board: chess.Board, sq: int, threshold: int = 2) -> bool:
    field = compute_pressure_field(board)
    if sq not in field:
        return False
    return abs(field[sq].net_pressure) <= threshold