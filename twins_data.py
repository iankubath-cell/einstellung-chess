"""twins_data.py v0.1 -- position data for the four Base44 twin fixtures."""

TWINS = [
    {
        "id": "T-B44-01",
        "name": "The Tangled Rook",
        "fen": "3r2k1/1p3ppp/8/1Q5r/8/8/8/4R1K1 w - - 0 1",
        "roots": [
            {"role": "familiar", "move": "Re8+", "branches": {
                "Rxe8": ["Re8+", "Rxe8", "Qxe8#"]}},
            {"role": "twin", "move": "Qe8+", "branches": {
                "Rxe8": ["Qe8+", "Rxe8", "Rxe8#"]}},
        ],
    },
    {
        "id": "T-B44-02",
        "name": "The f7 Key",
        "fen": "rn4k1/5ppp/8/5NN1/1r6/1Q6/8/6K1 w - - 0 1",
        "roots": [
            {"role": "familiar", "move": "Qxf7+", "branches": {
                "Kh8": ["Qxf7+", "Kh8", "Qxg7#"]}},
            {"role": "twin", "move": "Ne7+", "branches": {
                "Kh8": ["Ne7+", "Kh8", "Nxf7#"],
                "Kf8": ["Ne7+", "Kf8", "Qxf7#"]}},
        ],
    },
    {
        "id": "T-B44-03",
        "name": "The Distant Attacker",
        "fen": "3r2k1/5ppp/p7/8/Q6r/8/8/4R1K1 w - - 0 1",
        "roots": [
            {"role": "familiar", "move": "Re8+", "branches": {
                "Rxe8": ["Re8+", "Rxe8", "Qxe8#"]}},
            {"role": "twin", "move": "Qe8+", "branches": {
                "Rxe8": ["Qe8+", "Rxe8", "Rxe8#"]}},
        ],
    },
    {
        "id": "T-B44-04",
        "name": "The Knight's Screen",
        "fen": "rn4k1/5ppp/2p5/5NN1/1rQ5/8/8/6K1 w - - 0 1",
        "roots": [
            {"role": "familiar", "move": "Qxf7+", "branches": {
                "Kh8": ["Qxf7+", "Kh8", "Qxg7#"]}},
            {"role": "twin", "move": "Ne7+", "branches": {
                "Kh8": ["Ne7+", "Kh8", "Nxf7#"],
                "Kf8": ["Ne7+", "Kf8", "Qxf7#"]}},
        ],
    },
]