// Exhaustive census of pawnless n x n positions: 2 kings + k non-king pieces (Q,R,B,N of either colour), WHITE to move.
// Strict duel predicate (my reading of the description -- see report):
//   no root mates in 1;  no LOUD root (check or capture) forces mate within 2;
//   at least one QUIET root forces mate in exactly 2;  at least one CHECKING root forces mate in exactly 3.
// Raw counts are over all positions (no symmetry quotient): white-king orbit representatives x orbit size.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#ifndef MAXSQ
#define MAXSQ 36
#endif
typedef struct { int8_t sq[MAXSQ]; } Board;
typedef struct { int8_t from, to; } Move;
static int N, NS, K;
static const int KD[8][2] = {{1,0},{-1,0},{0,1},{0,-1},{1,1},{1,-1},{-1,1},{-1,-1}};
static const int ND[8][2] = {{1,2},{2,1},{-1,2},{-2,1},{1,-2},{2,-1},{-1,-2},{-2,-1}};

static inline int onb(int r, int c) { return r >= 0 && r < N && c >= 0 && c < N; }

static int attacked(const Board *b, int s, int by) { // is square s attacked by colour `by` (+1 white, -1 black)
    int r = s / N, c = s % N;
    for (int i = 0; i < 8; i++) {
        int rr = r + ND[i][0], cc = c + ND[i][1];
        if (onb(rr, cc) && b->sq[rr * N + cc] == by * 5) return 1;
        rr = r + KD[i][0]; cc = c + KD[i][1];
        if (onb(rr, cc) && b->sq[rr * N + cc] == by * 1) return 1;
    }
    for (int i = 0; i < 8; i++) {
        int rr = r + KD[i][0], cc = c + KD[i][1];
        while (onb(rr, cc)) {
            int p = b->sq[rr * N + cc];
            if (p) {
                int t = p * by;                      // >0 iff our colour
                if (t > 0) {
                    if (t == 2) return 1;
                    if (i < 4 && t == 3) return 1;   // rook on orthogonal
                    if (i >= 4 && t == 4) return 1;  // bishop on diagonal
                }
                break;
            }
            rr += KD[i][0]; cc += KD[i][1];
        }
    }
    return 0;
}
static int ksq(const Board *b, int side) {
    for (int s = 0; s < NS; s++) if (b->sq[s] == side) return s;
    return -1;
}
static int in_check(const Board *b, int side) { return attacked(b, ksq(b, side), -side); }

static void apply(Board *b, Move m) { b->sq[m.to] = b->sq[m.from]; b->sq[m.from] = 0; }

static int gen_legal(const Board *b, int side, Move *out) {
    int n = 0;
    for (int s = 0; s < NS; s++) {
        int p = b->sq[s];
        if (!p || p * side < 0) continue;
        int t = p * side, r = s / N, c = s % N;
        int lo = 0, hi = 0, slide = 0, knight = 0;
        if (t == 1) { lo = 0; hi = 8; }
        else if (t == 2) { lo = 0; hi = 8; slide = 1; }
        else if (t == 3) { lo = 0; hi = 4; slide = 1; }
        else if (t == 4) { lo = 4; hi = 8; slide = 1; }
        else knight = 1;
        for (int i = lo; i < (knight ? 8 : hi); i++) {
            int dr = knight ? ND[i][0] : KD[i][0], dc = knight ? ND[i][1] : KD[i][1];
            int rr = r + dr, cc = c + dc;
            while (onb(rr, cc)) {
                int q = b->sq[rr * N + cc];
                if (q * side > 0) break;                       // own piece
                if (!(q && (q < 0 ? -q : q) == 1)) {           // never "capture" a king
                    Move m = {(int8_t)s, (int8_t)(rr * N + cc)};
                    Board d = *b; apply(&d, m);
                    if (!in_check(&d, side)) out[n++] = m;
                }
                if (q || !slide) break;
                rr += dr; cc += dc;
            }
        }
    }
    return n;
}

static int white_mates_within(const Board *b, int n) { // white to move; can white force mate within n white moves?
    Move ms[256]; int m = gen_legal(b, +1, ms);
    for (int i = 0; i < m; i++) {
        Board c = *b; apply(&c, ms[i]);
        Move bm[256]; int k = gen_legal(&c, -1, bm);
        if (k == 0) { if (in_check(&c, -1)) return 1; continue; }
        if (n > 1) {
            int all = 1;
            for (int j = 0; j < k && all; j++) { Board d = c; apply(&d, bm[j]); if (!white_mates_within(&d, n - 1)) all = 0; }
            if (all) return 1;
        }
    }
    return 0;
}
static int after_mates_within(const Board *c, int n) { // black to move after a white root move
    Move bm[256]; int k = gen_legal(c, -1, bm);
    if (k == 0) return in_check(c, -1);
    if (n < 2) return 0;
    for (int j = 0; j < k; j++) { Board d = *c; apply(&d, bm[j]); if (!white_mates_within(&d, n - 1)) return 0; }
    return 1;
}

typedef struct { long long legal, degenerate, mate1, loud2, noquiet_or_nomate2, nocheck3, duel, any_mate2, any_mate3_root; } Stats;
static Stats ST; static int WEIGHT; static int shown = 0, SHOW = 0;
static int LASTCAT;  // 0 illegal,1 degenerate,2 mate1,3 loud2,4 no mate2,5 quiet2 but no check3,6 duel
typedef struct { int8_t r[8], c[8], p[8]; int n; } Pos;
static Pos *STORE; static long NSTORE; static int DOSTORE;

static void show(const Board *b) {
    const char *g = ".KQRBN";
    for (int r = N - 1; r >= 0; r--) { for (int c = 0; c < N; c++) { int p = b->sq[r * N + c]; putchar(!p ? '.' : p > 0 ? g[p] : g[-p] + 32); } putchar('\n'); }
    putchar('\n');
}

static void classify(const Board *b) {
    LASTCAT = 0;
    int bk = ksq(b, -1), wk = ksq(b, +1);
    if (attacked(b, bk, +1)) return;       // black king capturable: illegal with white to move
    if (attacked(b, wk, -1)) return;       // simplification: white to move and in check excluded
    int dk = abs(bk / N - wk / N) > abs(bk % N - wk % N) ? abs(bk / N - wk / N) : abs(bk % N - wk % N);
    if (dk < 2) return;
    ST.legal += WEIGHT;
    Move ms[256]; int m = gen_legal(b, +1, ms);
    if (m == 0) { LASTCAT = 1; ST.degenerate += WEIGHT; return; }
    Board after[256]; int chk[256], cap[256];
    for (int i = 0; i < m; i++) {
        after[i] = *b; cap[i] = b->sq[ms[i].to] != 0; apply(&after[i], ms[i]);
        chk[i] = in_check(&after[i], -1);
    }
    for (int i = 0; i < m; i++) if (after_mates_within(&after[i], 1)) { LASTCAT = 2; ST.mate1 += WEIGHT; return; }
    int quiet2 = 0, loud2 = 0;
    for (int i = 0; i < m; i++) if (after_mates_within(&after[i], 2)) { if (chk[i] || cap[i]) loud2 = 1; else quiet2 = 1; }
    if (loud2 || quiet2) ST.any_mate2 += WEIGHT;
    if (loud2) { LASTCAT = 3; ST.loud2 += WEIGHT; return; }
    if (!quiet2) { LASTCAT = 4; ST.noquiet_or_nomate2 += WEIGHT; return; }
    int c3 = 0;
    for (int i = 0; i < m && !c3; i++) if (chk[i] && after_mates_within(&after[i], 3)) c3 = 1;
    if (!c3) { LASTCAT = 5; ST.nocheck3 += WEIGHT; return; }
    LASTCAT = 6; ST.duel += WEIGHT;
    if (DOSTORE) { Pos *q = &STORE[NSTORE++]; q->n = 0; for (int s = 0; s < NS; s++) if (b->sq[s]) { q->r[q->n] = s / N; q->c[q->n] = s % N; q->p[q->n] = b->sq[s]; q->n++; } }
    if (shown < SHOW) { shown++; printf("duel example (white to move):\n"); show(b); }
}

static void place(Board *b, const int *free_sq, int nfree, int start, int left) {
    if (left == 0) { classify(b); return; }
    for (int i = start; i <= nfree - left; i++) {
        int s = free_sq[i];
        for (int t = 2; t <= 5; t++) for (int col = -1; col <= 1; col += 2) {
            b->sq[s] = (int8_t)(t * col);
            place(b, free_sq, nfree, i + 1, left - 1);
        }
        b->sq[s] = 0;
    }
}

static int canon_sq(int s, int *orbit) { // dihedral orbit of square s; returns min image; *orbit = orbit size
    int r = s / N, c = s % N, best = s, imgs[8], ni = 0;
    int cand[8][2] = {{r,c},{r,N-1-c},{N-1-r,c},{N-1-r,N-1-c},{c,r},{c,N-1-r},{N-1-c,r},{N-1-c,N-1-r}};
    for (int i = 0; i < 8; i++) {
        int v = cand[i][0] * N + cand[i][1], seen = 0;
        for (int j = 0; j < ni; j++) if (imgs[j] == v) seen = 1;
        if (!seen) imgs[ni++] = v;
        if (v < best) best = v;
    }
    *orbit = ni; return best;
}


int main(int argc, char **argv) {
    N = atoi(argv[1]); K = atoi(argv[2]); int N1 = argc > 3 ? atoi(argv[3]) : 0; SHOW = 0; NS = N * N;
    if (N1 == 0) { fprintf(stderr, "usage: census2 N K N1\n"); return 1; }
    DOSTORE = 1; STORE = malloc(sizeof(Pos) * 4000000L); NSTORE = 0; WEIGHT = 1;
    // phase 1: ALL raw duels on the n x n board (no orbit shortcut, weight 1)
    for (int w = 0; w < NS; w++)
        for (int bks = 0; bks < NS; bks++) {
            if (bks == w) continue;
            Board b; memset(&b, 0, sizeof b); b.sq[w] = 1; b.sq[bks] = -1;
            int fr[MAXSQ], nf = 0;
            for (int s = 0; s < NS; s++) if (s != w && s != bks) fr[nf++] = s;
            place(&b, fr, nf, 0, K);
        }
    printf("phase 1: %dx%d k=%d  raw duels = %ld\n", N, N, K, NSTORE);
    DOSTORE = 0; int N0 = N; long cat[8] = {0}, trials = 0, offc[16][16][8]; memset(offc, 0, sizeof offc);
    N = N1; NS = N * N; int span = N1 - N0;
    for (long i = 0; i < NSTORE; i++)
        for (int dr = 0; dr <= span; dr++) for (int dc = 0; dc <= span; dc++) {
            Board b; memset(&b, 0, sizeof b);
            for (int j = 0; j < STORE[i].n; j++) b.sq[(STORE[i].r[j] + dr) * N + (STORE[i].c[j] + dc)] = STORE[i].p[j];
            classify(&b); cat[LASTCAT]++; trials++; offc[dr][dc][LASTCAT]++;
        }
    printf("phase 2: embedded into %dx%d at all %d offsets: %ld trials\n", N1, N1, (span + 1) * (span + 1), trials);
    const char *nm[7] = {"illegal(king capturable / white in check)", "degenerate", "mate in 1 appears", "loud mate in 2 appears",
                         "no forced mate in 2 left", "quiet m2 but no checking m3", "STILL A DUEL"};
    for (int c = 0; c < 7; c++) printf("   %-44s %9ld  %6.2f%%\n", nm[c], cat[c], 100.0 * cat[c] / trials);
    for (int dr = 0; dr <= span; dr++) { printf("   row offset %d, survivors by column offset:", dr); for (int dc = 0; dc <= span; dc++) printf(" %ld", offc[dr][dc][6]); printf("\n"); }
    return 0;
}
