#!/usr/bin/env python3
"""Single source of truth for canonical Einstellung positions.

Every gate script imports from here instead of embedding FENs. This exists
because a hard-coded FEN in ``forced_mate_gate.py`` survived the C3 revision
and produced a spurious ``Nxe6`` failure: the run tested a superseded board
under a current label.

Design rules enforced by this module:

* FEN is the primary key. IDs are conveniences.
* Positions are data, not literals.
* A line that does not replay to checkmate is a bug, not a puzzle.

Usage as a library::

    from load_positions import load, get

    pos = get("C1")
    board = pos.board                      # fresh chess.Board from the FEN
    attacker = pos.attacker                # chess.WHITE / chess.BLACK
    for key, line in pos.lines.items():
        ...

Usage as a CLI::

    python load_positions.py --validate
    python load_positions.py --list
    python load_positions.py --fen C3
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator, Literal, Sequence

try:
    import chess
except ImportError:  # pragma: no cover
    sys.exit("Missing dependency: pip install 'chess>=1.10'")

__all__ = [
    "Line",
    "Position",
    "GraveyardEntry",
    "Corpus",
    "Issue",
    "load",
    "get",
    "by_fen",
    "iter_positions",
    "validate",
    "POSITIONS_FILE",
]

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

# Load from the same directory as this file, or repo root if in scripts/
THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent
POSITIONS_FILE = THIS_DIR / "positions" / "canonical.json"

SideToMove = Literal["white", "black"]

SEVERITY_ERROR = "ERROR"
SEVERITY_WARN = "WARN"


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


class CorpusError(RuntimeError):
    """Raised when the corpus cannot be loaded at all."""


class UnknownPosition(KeyError):
    """Raised when an ID or FEN is not present in the corpus."""


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Line:
    """A single solution line: SAN sequence plus its mate distance in moves."""

    key: str
    length: int | None
    san: tuple[str, ...]
    note: str | None = None
    expect_mate: bool = True  # C3 support: probes that should NOT mate

    @property
    def plies(self) -> int:
        return len(self.san)

    @property
    def expected_plies(self) -> int | None:
        """Mate in N moves means 2N-1 plies (attacker moves last)."""
        return None if self.length is None else 2 * self.length - 1

    @property
    def first_move(self) -> str | None:
        return self.san[0] if self.san else None


@dataclass(frozen=True)
class Position:
    """A canonical position. Immutable; derive boards on demand."""

    id: str
    name: str
    fen: str
    side_to_move: SideToMove
    status: str
    first_move: str | None
    lines: dict[str, Line]
    gate_results: dict[str, Any]
    notes: str | None = None

    # -- derived helpers ---------------------------------------------------

    @property
    def board(self) -> chess.Board:
        """A fresh board for this FEN. Never mutate a shared board."""
        return chess.Board(self.fen)

    @property
    def attacker(self) -> chess.Color:
        """Colour that delivers mate. Use with ``score.pov(pos.attacker)``."""
        return chess.WHITE if self.side_to_move == "white" else chess.BLACK

    @property
    def defender(self) -> chess.Color:
        return not self.attacker

    @property
    def short_line(self) -> Line | None:
        return self.lines.get("short")

    @property
    def familiar_line(self) -> Line | None:
        return self.lines.get("familiar")

    @property
    def is_verified(self) -> bool:
        return self.status == "verified"

    def line(self, key: str) -> Line:
        try:
            return self.lines[key]
        except KeyError:
            raise UnknownPosition(
                f"{self.id} has no line {key!r}; available: {sorted(self.lines)}"
            ) from None

    def replay(self, key: str) -> chess.Board:
        """Replay a named line and return the final board.

        Raises ValueError if the line does not replay to checkmate. This is
        the layer-1 replay gate, available to every consumer.
        """
        line = self.line(key)
        board = self.board
        for ply, san in enumerate(line.san, start=1):
            try:
                board.push_san(san)
            except ValueError as exc:
                raise ValueError(
                    f"{self.id}/{key}: ply {ply} ({san}) illegal: {exc}"
                ) from None
        if not board.is_checkmate():
            raise ValueError(f"{self.id}/{key}: does not end in checkmate")
        return board


@dataclass(frozen=True)
class GraveyardEntry:
    id: str
    name: str
    fen: str
    cause_of_death: str
    lesson: str
    postmortem_note: str | None = None


@dataclass(frozen=True)
class Corpus:
    schema_version: int
    updated: str
    positions: tuple[Position, ...]
    graveyard: tuple[GraveyardEntry, ...]
    open_items: tuple[dict[str, Any], ...]
    raw: dict[str, Any]

    def by_id(self, position_id: str) -> Position:
        for pos in self.positions:
            if pos.id == position_id:
                return pos
        raise UnknownPosition(f"No position with id {position_id!r}")

    def by_fen(self, fen: str) -> Position:
        # Normalise whitespace so trivial formatting differences still match.
        target = " ".join(fen.split())
        for pos in self.positions:
            if " ".join(pos.fen.split()) == target:
                return pos
        raise UnknownPosition(f"No position with FEN {fen!r}")

    def where(self, status: str | None = None) -> Iterator[Position]:
        for pos in self.positions:
            if status is None or pos.status == status:
                yield pos


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def _parse_line(key: str, blob: dict[str, Any] | None) -> Line | None:
    if blob is None:
        return None
    san = blob.get("san") or []
    return Line(
        key=key,
        length=blob.get("length"),
        san=tuple(san),
        note=blob.get("note"),
        expect_mate=blob.get("expect_mate", True),  # C3 support
    )


def _parse_position(blob: dict[str, Any]) -> Position:
    lines: dict[str, Line] = {}
    for key, line_blob in (blob.get("lines") or {}).items():
        parsed = _parse_line(key, line_blob)
        if parsed is not None:
            lines[key] = parsed
    return Position(
        id=blob["id"],
        name=blob.get("name", ""),
        fen=blob["fen"],
        side_to_move=blob.get("side_to_move", "white"),
        status=blob.get("status", "untested"),
        first_move=blob.get("first_move"),
        lines=lines,
        gate_results=blob.get("gate_results") or {},
        notes=blob.get("notes"),
    )


@lru_cache(maxsize=1)
def load(path: Path | str | None = None) -> Corpus:
    """Load and cache the canonical corpus."""
    target = Path(path) if path is not None else POSITIONS_FILE
    if not target.is_file():
        raise CorpusError(f"Positions file not found: {target}")
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CorpusError(f"{target} is not valid JSON: {exc}") from None

    positions = tuple(_parse_position(p) for p in raw.get("positions", []))
    graveyard = tuple(
        GraveyardEntry(
            id=g["id"],
            name=g.get("name", ""),
            fen=g["fen"],
            cause_of_death=g.get("cause_of_death", ""),
            lesson=g.get("lesson", ""),
            postmortem_note=g.get("postmortem_note"),
        )
        for g in raw.get("graveyard", [])
    )
    return Corpus(
        schema_version=raw.get("schema_version", 0),
        updated=raw.get("updated", ""),
        positions=positions,
        graveyard=graveyard,
        open_items=tuple(raw.get("open_items", [])),
        raw=raw,
    )


def get(position_id: str) -> Position:
    """Fetch a position by canonical ID."""
    return load().by_id(position_id)


def by_fen(fen: str) -> Position:
    """Fetch a position by FEN. The primary key."""
    return load().by_fen(fen)


def iter_positions(status: str | None = None) -> Iterator[Position]:
    return load().where(status)


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Issue:
    severity: str
    subject: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.subject}: {self.message}"

    @property
    def is_error(self) -> bool:
        return self.severity == SEVERITY_ERROR


def _check_fen(subject: str, fen: str) -> tuple[chess.Board | None, list[Issue]]:
    issues: list[Issue] = []
    try:
        board = chess.Board(fen)
    except ValueError as exc:
        issues.append(Issue(SEVERITY_ERROR, subject, f"unparseable FEN: {exc}"))
        return None, issues
    if not board.is_valid():
        issues.append(
            Issue(SEVERITY_ERROR, subject, f"invalid position: {board.status()!r}")
        )
        return None, issues
    return board, issues


def _check_line(pos: Position, line: Line) -> list[Issue]:
    issues: list[Issue] = []
    subject = f"{pos.id}/{line.key}"

    if not line.san:
        issues.append(Issue(SEVERITY_WARN, subject, "no SAN sequence recorded"))
        return issues

    # Mate distance vs ply count: mate in N moves is 2N-1 plies.
    if line.expected_plies is not None and line.plies != line.expected_plies:
        issues.append(
            Issue(
                SEVERITY_ERROR,
                subject,
                f"declared mate in {line.length} implies {line.expected_plies} "
                f"plies but {line.plies} recorded",
            )
        )

    # Shared first move is the experimental property; check per line too.
    if pos.first_move and line.first_move != pos.first_move:
        issues.append(
            Issue(
                SEVERITY_ERROR,
                subject,
                f"starts with {line.first_move!r} but position declares "
                f"first_move={pos.first_move!r}",
            )
        )

    # Replay gate.
    board = pos.board
    for ply, san in enumerate(line.san, start=1):
        try:
            board.push_san(san)
        except ValueError as exc:
            issues.append(
                Issue(SEVERITY_ERROR, subject, f"ply {ply} ({san}) illegal: {exc}")
            )
            return issues

    if not board.is_checkmate():
        issues.append(
            Issue(
                SEVERITY_ERROR,
                subject,
                f"final position is not checkmate (turn={board.turn}, "
                f"check={board.is_check()})",
            )
        )
    elif not line.san[-1].endswith("#"):
        issues.append(
            Issue(
                SEVERITY_WARN,
                subject,
                f"ends in checkmate but SAN {line.san[-1]!r} lacks '#' suffix",
            )
        )
    return issues


def validate(corpus: Corpus | None = None) -> list[Issue]:
    """Run every structural check. Returns issues; empty list means clean."""
    corpus = corpus or load()
    issues: list[Issue] = []

    if corpus.schema_version != 1:
        issues.append(
            Issue(
                SEVERITY_WARN,
                "corpus",
                f"unexpected schema_version {corpus.schema_version}",
            )
        )

    # Uniqueness of IDs and FENs.
    seen_ids: dict[str, str] = {}
    seen_fens: dict[str, str] = {}
    for pos in corpus.positions:
        if pos.id in seen_ids:
            issues.append(
                Issue(SEVERITY_ERROR, pos.id, f"duplicate ID (also {seen_ids[pos.id]})")
            )
        seen_ids[pos.id] = pos.name
        norm = " ".join(pos.fen.split())
        if norm in seen_fens:
            issues.append(
                Issue(
                    SEVERITY_ERROR,
                    pos.id,
                    f"duplicate FEN (also {seen_fens[norm]})",
                )
            )
        seen_fens[norm] = pos.id

    for pos in corpus.positions:
        board, fen_issues = _check_fen(pos.id, pos.fen)
        issues.extend(fen_issues)
        if board is None:
            continue

        # side_to_move must agree with the FEN's active colour.
        actual = "white" if board.turn == chess.WHITE else "black"
        if actual != pos.side_to_move:
            issues.append(
                Issue(
                    SEVERITY_ERROR,
                    pos.id,
                    f"side_to_move={pos.side_to_move!r} but FEN says {actual!r}",
                )
            )

        # Declared first move must be legal.
        if pos.first_move:
            try:
                board.parse_san(pos.first_move)
            except ValueError as exc:
                issues.append(
                    Issue(
                        SEVERITY_ERROR,
                        pos.id,
                        f"first_move {pos.first_move!r} illegal: {exc}",
                    )
                )

        for line in pos.lines.values():
            issues.extend(_check_line(pos, line))

        # The load-bearing property: both solutions share move one.
        short, familiar = pos.short_line, pos.familiar_line
        if short and familiar and short.first_move != familiar.first_move:
            issues.append(
                Issue(
                    SEVERITY_ERROR,
                    pos.id,
                    f"short line starts {short.first_move!r} but familiar line "
                    f"starts {familiar.first_move!r} — the shared-first-move "
                    "property is violated",
                )
            )

        # Status honesty: verified implies gates recorded as passing.
        if pos.status == "verified":
            for gate in ("replay", "engine_root", "tree_gate"):
                value = str(pos.gate_results.get(gate, "")).lower()
                if "pass" not in value and not value.startswith("#+"):
                    issues.append(
                        Issue(
                            SEVERITY_WARN,
                            pos.id,
                            f"status=verified but gate {gate!r} records {value!r}",
                        )
                    )

    # Graveyard FENs should still parse, so the archive stays usable.
    for entry in corpus.graveyard:
        _, fen_issues = _check_fen(entry.id, entry.fen)
        issues.extend(fen_issues)

    return issues


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _cmd_validate(args: argparse.Namespace) -> int:
    corpus = load(args.file)
    issues = validate(corpus)
    errors = [i for i in issues if i.is_error]
    warnings = [i for i in issues if not i.is_error]

    print(f"Validating {len(corpus.positions)} positions "
          f"({len(corpus.graveyard)} graveyard entries)")
    print("-" * 72)
    if not issues:
        print("Clean. All structural checks passed.")
    for issue in issues:
        print(issue)
    print("-" * 72)
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


def _cmd_list(args: argparse.Namespace) -> int:
    corpus = load(args.file)
    width = max((len(p.id) for p in corpus.positions), default=2)
    for pos in corpus.where(args.status):
        print(f"{pos.id:<{width}}  {pos.status:<16}  {pos.name}")
        print(f"{'':<{width}}  {pos.fen}")
    return 0


def _cmd_fen(args: argparse.Namespace) -> int:
    pos = load(args.file).by_id(args.id)
    print(pos.fen)
    return 0


def _cmd_json(args: argparse.Namespace) -> int:
    corpus = load(args.file)
    if args.id:
        payload: Any = next(
            (p for p in corpus.raw["positions"] if p["id"] == args.id), None
        )
        if payload is None:
            raise UnknownPosition(args.id)
    else:
        payload = corpus.raw
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="load_positions",
        description="Load and validate the canonical Einstellung corpus.",
    )
    parser.add_argument("--file", type=Path, default=None,
                        help="override positions file (default: positions/canonical.json)")
    sub = parser.add_subparsers(dest="command")

    p_val = sub.add_parser("validate", help="run structural checks (default)")
    p_val.set_defaults(func=_cmd_validate)

    p_list = sub.add_parser("list", help="list positions")
    p_list.add_argument("--status", default=None,
                        help="filter by status, e.g. verified or untested")
    p_list.set_defaults(func=_cmd_list)

    p_fen = sub.add_parser("fen", help="print the FEN for an ID")
    p_fen.add_argument("id")
    p_fen.set_defaults(func=_cmd_fen)

    p_json = sub.add_parser("json", help="dump raw JSON for an ID or the corpus")
    p_json.add_argument("id", nargs="?", default=None)
    p_json.set_defaults(func=_cmd_json)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        args = parser.parse_args(["validate"] + (argv or []))

    try:
        return int(args.func(args))
    except (CorpusError, UnknownPosition) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
