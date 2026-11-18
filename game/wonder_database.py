import json
from pathlib import Path

WONDER_DATABASE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "wonder_database.json"
)


def load_wonder_database():
    with open(WONDER_DATABASE_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def get_wonder_stages(wonder_board, wonder_side):
    database = load_wonder_database()

    board = database.get(wonder_board)

    if board is None:
        return None

    return board.get(wonder_side, {}).get("stages")