import json
from pathlib import Path


CARD_DATABASE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "card_database.json"
)


def load_card_database():
    with open(CARD_DATABASE_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def get_cards_by_age(age):
    cards = load_card_database()
    return cards["age_cards"].get(str(age), [])


def get_card_by_name(card_name, age=None):
    cards = load_card_database()
    
    if age is not None:
        card_list = cards["age_cards"].get(str(age), [])
        
        for card in card_list:
            if card["name"].lower() == card_name.lower():
                return card
        
        return None

    for card_list in cards["age_cards"].values():
        for card in card_list:
            if card["name"].lower() == card_name.lower():
                return card

    return None


def get_cards_by_color(color, age):
    card_list = get_cards_by_age(age)

    return [
        card for card in card_list
        if card["color"].upper() == color.upper()
    ]




if __name__ == "__main__":
    age_one_cards = get_cards_by_age(1)
    clay_pit = get_card_by_name("Clay Pit")
    brown_cards = get_cards_by_color("BROWN", 1)

    print("Age I cards:", len(age_one_cards))
    print("\nClay Pit:")
    print(clay_pit)

    print("\nBrown cards in Age I:")
    for card in brown_cards:
        print("-", card["name"])