#!/usr/bin/env python3
"""Independent re-implementation of census.c (different structure on purpose):
dict boards, legality by generating the opponent's pseudo-moves, full raw enumeration (no symmetry shortcut),
single recursive 'mates' function.  Prints the same category counts as census.c.
usage: census_py.py N K [WORKERS]"""
import itertools
import sys
from multiprocessing import Pool

N = int(sys.argv[1]); K = int(sys.argv[2])
ORTH = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
KN = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
SQS = [(r, c) for r in range(N) for c in range(N)]


def pseudo(board, side):
    """pseudo-legal moves (frm, to) for `side` ('w'/'b'); kings are never captured here."""
    for (r, c), (col, t) in list(board.items()):
        if col != side:
            continue
        if t == 'K':
            dirs, slide = ORTH + DIAG, False
        elif t == 'Q':
            dirs, slide = ORTH + DIAG, True
        elif t == 'R':
            dirs, slide = ORTH, True
        elif t == 'B':
            dirs, slide = DIAG, True
        else:
            dirs, slide = KN, False
        for dr, dc in dirs:
            rr, cc = r + dr, c + dc
            while 0 <= rr < N and 0 <= cc < N:
                o = board.get((rr, cc))
                if o is not None:
                    if o[0] != side and o[1] != 'K':
                        yield (r, c), (rr, cc)
                    break
                yield (r, c), (rr, cc)
                if not slide:
                    break
                rr += dr; cc += dc


def kpos(board, side):
    for sq, (col, t) in board.items():
        if col == side and t == 'K':
            return sq


def attacks_king(board, attacker):
    """does `attacker` attack the other king?  generate attacker's moves INCLUDING onto the king square."""
    target = kpos(board, 'b' if attacker == 'w' else 'w')
    for (r, c), (col, t) in board.items():
        if col != attacker:
            continue
        if t == 'K':
            if max(abs(r - target[0]), abs(c - target[1])) == 1:
                return True
            continue
        if t == 'N':
            if (target[0] - r, target[1] - c) in KN:
                return True
            continue
        dirs = {'Q': ORTH + DIAG, 'R': ORTH, 'B': DIAG}[t]
        for dr, dc in dirs:
            rr, cc = r + dr, c + dc
            while 0 <= rr < N and 0 <= cc < N:
                if (rr, cc) == target:
                    return True
                if (rr, cc) in board:
                    break
                rr += dr; cc += dc
    return False


def play(board, mv):
    b = dict(board)
    b[mv[1]] = b.pop(mv[0])
    return b


def legal(board, side):
    other = 'b' if side == 'w' else 'w'
    res = []
    for mv in pseudo(board, side):
        nb = play(board, mv)
        if not attacks_king(nb, other):
            res.append((mv, nb))
    return res


def mates(board, side, n):
    """white to move at side=='w' with n white moves left; True iff white forces mate."""
    if side == 'w':
        if n == 0:
            return False
        for mv, nb in legal(board, 'w'):
            if mates(nb, 'b', n):
                return True
        return False
    replies = legal(board, 'b')
    if not replies:
        return attacks_king(board, 'w')        # mated (True) or stalemated (False)
    if n == 1:
        return False
    return all(mates(nb, 'w', n - 1) for _, nb in replies)


def classify(board):
    if attacks_king(board, 'w') or attacks_king(board, 'b'):
        return None                              # black king capturable / white to move in check: excluded
    roots = legal(board, 'w')
    if not roots:
        return 'degenerate'
    info = []
    for mv, nb in roots:
        info.append((board.get(mv[1]) is not None, attacks_king(nb, 'w'), nb))   # capture, check, board after
    if any(mates(nb, 'b', 1) for _, _, nb in info):
        return 'mate1'
    quiet2 = loud2 = False
    for cap, chk, nb in info:
        if mates(nb, 'b', 2):
            if cap or chk: loud2 = True
            else: quiet2 = True
    if loud2:
        return 'loud2+'
    if not quiet2:
        return 'nomate2'
    if any(chk and mates(nb, 'b', 3) for cap, chk, nb in info):
        return 'duel+'
    return 'nocheck3'


def work(wk):
    cnt = {}
    anym2 = 0
    for bk in SQS:
        if bk == wk or max(abs(bk[0] - wk[0]), abs(bk[1] - wk[1])) < 2:
            continue
        free = [s for s in SQS if s != wk and s != bk]
        for combo in itertools.combinations(free, K):
            for labels in itertools.product([(c, t) for c in 'wb' for t in 'QRBN'], repeat=K):
                board = {wk: ('w', 'K'), bk: ('b', 'K')}
                for s, l in zip(combo, labels):
                    board[s] = l
                r = classify(board)
                if r is None:
                    continue
                cnt['legal'] = cnt.get('legal', 0) + 1
                cnt[r] = cnt.get(r, 0) + 1
                if r in ('loud2+', 'duel+', 'nocheck3'):
                    anym2 += 1
    cnt['any_mate2'] = anym2
    return cnt


if __name__ == '__main__':
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    with Pool(workers) as p:
        parts = p.map(work, SQS)
    tot = {}
    for c in parts:
        for k, v in c.items():
            tot[k] = tot.get(k, 0) + v
    print(f"n={N} k={K}  legal={tot.get('legal',0)}  mate_in_1_exists={tot.get('mate1',0)}  loud_mate_in_2={tot.get('loud2+',0)}  "
          f"no_mate_in_2_at_all={tot.get('nomate2',0)}  quiet_m2_but_no_check_m3={tot.get('nocheck3',0)}  "
          f"DUELS={tot.get('duel+',0)}  degenerate={tot.get('degenerate',0)}  any_mate_in_2={tot.get('any_mate2',0)}")
