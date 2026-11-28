# corner_window v0.1 findings

Input: duels_ondisk5.json  positions: 3  windows classified: 34

Gate passed: every identity window is DUEL under this script's reading of the predicate.

## Per-position verdicts

| verdict | count |
|---|---|
| ANCHORED_CORNER | 3 |

## Positions that do NOT survive in any corner window with w < 8 (recorded as findings)

None: every position has a surviving corner window with w < 8.

A position failing corner survival is a result about that position's geometry, not a defect in its certification.  Pooled rates by window size and class are in pooled_by_window.csv.
