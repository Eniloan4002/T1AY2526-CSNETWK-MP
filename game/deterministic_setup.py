
import hashlib


WONDER_BOARDS = [
    "Alexandria",
    "Babylon",
    "Ephesos",
    "Gizah",
    "Halikarnassus",
    "Olympia",
    "Rhodes"
]

GUILD_CARDS = [
    "Builders Guild",
    "Craftsmens Guild",
    "Magistrates Guild",
    "Philosophers Guild",
    "Scientists Guild",
    "Shipowners Guild",
    "Spies Guild",
    "Strategists Guild",
    "Traders Guild",
    "Workers Guild"
]


# Age I card counts for 3, 4, 5, 6, and 7 players.
# Each tuple follows that exact player-count order.
AGE_I_CARDS = {
    "Clay Pit": (1, 1, 1, 1, 1),
    "Clay Pool": (1, 1, 2, 2, 2),
    "Excavation": (0, 1, 1, 1, 1),
    "Forest Cave": (0, 0, 1, 1, 1),
    "Lumber Yard": (1, 2, 2, 2, 2),
    "Mine": (0, 0, 0, 1, 1),
    "Ore Vein": (1, 2, 2, 2, 2),
    "Stone Pit": (1, 1, 2, 2, 2),
    "Timber Yard": (1, 1, 1, 1, 1),
    "Tree Farm": (0, 0, 0, 1, 1),

    "Glassworks": (1, 1, 1, 2, 2),
    "Loom": (1, 1, 1, 2, 2),
    "Press": (1, 1, 1, 2, 2),

    "East Trading Post": (1, 1, 1, 1, 2),
    "Marketplace": (1, 1, 1, 2, 2),
    "Tavern": (0, 1, 2, 2, 3),
    "West Trading Post": (1, 1, 1, 1, 2),

    "Altar": (1, 1, 2, 2, 2),
    "Baths": (1, 1, 1, 1, 2),
    "Pawnshop": (0, 1, 1, 1, 2),
    "Theater": (1, 1, 1, 2, 2),

    "Apothecary": (1, 1, 2, 2, 2),
    "Scriptorium": (1, 2, 2, 2, 2),
    "Workshop": (1, 1, 1, 1, 2),

    "Barracks": (1, 1, 2, 2, 2),
    "Guard Tower": (1, 2, 2, 2, 2),
    "Stockade": (1, 1, 1, 1, 2)
}


# Age II card counts for 3, 4, 5, 6, and 7 players.
AGE_II_CARDS = {
    "Brickyard": (1, 2, 2, 2, 2),
    "Foundry": (1, 2, 2, 2, 2),
    "Quarry": (1, 2, 2, 2, 2),
    "Sawmill": (1, 2, 2, 2, 2),

    "Glassworks": (1, 1, 2, 2, 2),
    "Loom": (1, 1, 2, 2, 2),
    "Press": (1, 1, 2, 2, 2),

    "Bazar": (0, 1, 1, 1, 2),
    "Caravansery": (1, 1, 2, 3, 3),
    "Forum": (1, 1, 1, 2, 3),
    "Vineyard": (1, 1, 1, 2, 2),

    "Aqueduct": (1, 1, 1, 1, 2),
    "Courthouse": (1, 1, 2, 2, 2),
    "Statue": (1, 1, 1, 1, 2),
    "Temple": (1, 1, 1, 2, 2),

    "Dispensary": (1, 2, 2, 2, 2),
    "Laboratory": (1, 1, 2, 2, 2),
    "Library": (1, 1, 1, 2, 2),
    "School": (1, 1, 1, 1, 2),

    "Archery Range": (1, 1, 1, 2, 2),
    "Stables": (1, 1, 2, 2, 2),
    "Training Ground": (0, 1, 1, 2, 3),
    "Walls": (1, 1, 1, 1, 2)
}


# Age III card counts for 3, 4, 5, 6, and 7 players.
# Guild cards are added separately.
AGE_III_CARDS = {
    "Arena": (1, 1, 2, 2, 3),
    "Chamber of Commerce": (0, 1, 1, 2, 2),
    "Haven": (1, 2, 2, 2, 2),
    "Lighthouse": (1, 1, 1, 2, 2),

    "Gardens": (1, 2, 2, 2, 2),
    "Palace": (1, 1, 1, 1, 2),
    "Pantheon": (1, 1, 1, 2, 2),
    "Senate": (1, 1, 2, 2, 2),
    "Town Hall": (1, 1, 2, 3, 3),

    "Academy": (1, 1, 1, 1, 2),
    "Lodge": (1, 1, 1, 2, 2),
    "Observatory": (1, 1, 1, 1, 2),
    "Study": (1, 1, 2, 2, 2),
    "University": (1, 2, 2, 2, 2),

    "Arsenal": (1, 2, 2, 2, 3),
    "Circus": (0, 1, 2, 3, 3),
    "Fortifications": (1, 1, 1, 1, 2),
    "Siege Workshop": (1, 1, 2, 2, 2)
}


def hash_data(data):
    return hashlib.sha256(data).digest()


def create_game_setup(seed, peer_ids, both_sides=True):
    if len(seed) != 32:
        raise ValueError("The shared seed must be 32 bytes.")

    if not 3 <= len(peer_ids) <= 7:
        raise ValueError("The game must have 3 to 7 players.")

    if len(set(peer_ids)) != len(peer_ids):
        raise ValueError("Peer IDs must be unique.")

    if any(not isinstance(peer_id, int) or not 1 <= peer_id <= 255
           for peer_id in peer_ids):
        raise ValueError("Peer IDs must be integers from 1 to 255.")

    # 1. Determine seating order.
    seating_order = sorted(
        peer_ids,
        key=lambda peer_id: hash_data(
            seed + peer_id.to_bytes(1, "big")
        )
    )

    # 2. Determine Wonder board order.
    wonder_order = sorted(
        WONDER_BOARDS,
        key=lambda board: hash_data(
            seed + board.encode("utf-8")
        )
    )

    # Assign one Wonder board to each player in seat order.
    wonder_assignments = {}

    for seat, peer_id in enumerate(seating_order):
        board = wonder_order[seat]

        # 3. Determine Wonder side.
        if both_sides:
            side_hash = hash_data(
                seed + board.encode("utf-8") + b"side"
            )
            side = "B" if side_hash[-1] & 1 else "A"
        else:
            side = "A"

        wonder_assignments[peer_id] = {
            "seat": seat,
            "wonder_board": board,
            "wonder_side": side
        }

    # 4. Determine the Guild cards for Age III.
    guild_order = sorted(
        GUILD_CARDS,
        key=lambda card: hash_data(
            seed + card.encode("utf-8")
        )
    )

    selected_guilds = guild_order[:len(peer_ids) + 2]

    # 5. Determine each player's neighbors.
    neighbors = {}

    player_count = len(seating_order)

    for seat, peer_id in enumerate(seating_order):
        left_peer = seating_order[(seat - 1) % player_count]
        right_peer = seating_order[(seat + 1) % player_count]

        neighbors[peer_id] = {
            "left": left_peer,
            "right": right_peer
        }

    return {
        "seating_order": seating_order,
        "wonder_assignments": wonder_assignments,
        "guild_cards": selected_guilds,
        "neighbors": neighbors
    }


class DeterministicRandom:
    """
    A deterministic random generator using SHA-256 counter mode.

    Every player starts with the same seed and generates the same
    sequence of random bytes.
    """

    def __init__(self, seed):
        if len(seed) != 32:
            raise ValueError("The seed must be 32 bytes.")

        self.seed = seed
        self.counter = 0
        self.buffer = b""

    def get_bytes(self, count):
        while len(self.buffer) < count:
            counter_bytes = self.counter.to_bytes(8, "big")

            random_block = hashlib.sha256(
                self.seed + counter_bytes
            ).digest()

            self.buffer += random_block
            self.counter += 1

        result = self.buffer[:count]
        self.buffer = self.buffer[count:]

        return result

    def randbelow(self, limit):
        if limit <= 0:
            raise ValueError("Limit must be positive.")

        byte_count = (limit.bit_length() + 7) // 8
        maximum = 1 << (byte_count * 8)
        cutoff = maximum - (maximum % limit)

        while True:
            value = int.from_bytes(
                self.get_bytes(byte_count),
                "big"
            )

            if value < cutoff:
                return value % limit

    def shuffle(self, items):
        shuffled = list(items)

        for i in range(len(shuffled) - 1, 0, -1):
            j = self.randbelow(i + 1)

            shuffled[i], shuffled[j] = (
                shuffled[j],
                shuffled[i]
            )

        return shuffled


def build_age_one_deck(seed, player_count):
    if not 3 <= player_count <= 7:
        raise ValueError("The game must have 3 to 7 players.")

    cards = []

    # Select the correct quantity for the player count.
    count_index = player_count - 3

    for card_name, counts in AGE_I_CARDS.items():
        card_count = counts[count_index]

        for _ in range(card_count):
            cards.append(card_name)

    expected_count = player_count * 7

    if len(cards) != expected_count:
        raise ValueError(
            "Incorrect Age I deck size. Expected "
            + str(expected_count)
            + ", got "
            + str(len(cards))
        )

    # Shuffle using the shared deterministic seed.
    generator = DeterministicRandom(seed)
    shuffled_deck = generator.shuffle(cards)

    return shuffled_deck


def build_age_two_deck(seed, player_count):
    if not 3 <= player_count <= 7:
        raise ValueError("The game must have 3 to 7 players.")

    cards = []

    # Select the correct quantity for the player count.
    count_index = player_count - 3

    for card_name, counts in AGE_II_CARDS.items():
        card_count = counts[count_index]

        for _ in range(card_count):
            cards.append(card_name)

    expected_count = player_count * 7

    if len(cards) != expected_count:
        raise ValueError(
            "Incorrect Age II deck size. Expected "
            + str(expected_count)
            + ", got "
            + str(len(cards))
        )

    # Shuffle using the shared deterministic seed.
    generator = DeterministicRandom(seed)
    shuffled_deck = generator.shuffle(cards)

    return shuffled_deck


def build_age_three_deck(seed, player_count, selected_guilds):
    if not 3 <= player_count <= 7:
        raise ValueError("The game must have 3 to 7 players.")

    if len(selected_guilds) != player_count + 2:
        raise ValueError(
            "Age III must contain player_count + 2 Guild cards."
        )

    cards = []

    # Select the correct quantity for the player count.
    count_index = player_count - 3

    for card_name, counts in AGE_III_CARDS.items():
        card_count = counts[count_index]

        for _ in range(card_count):
            cards.append(card_name)

    # Add the Guild cards selected during game setup.
    cards.extend(selected_guilds)

    expected_count = player_count * 7

    if len(cards) != expected_count:
        raise ValueError(
            "Incorrect Age III deck size. Expected "
            + str(expected_count)
            + ", got "
            + str(len(cards))
        )

    # Shuffle using the shared deterministic seed.
    generator = DeterministicRandom(seed)
    shuffled_deck = generator.shuffle(cards)

    return shuffled_deck


def build_all_age_decks(seed, player_count, selected_guilds):
    if not 3 <= player_count <= 7:
        raise ValueError("The game must have 3 to 7 players.")

    if len(selected_guilds) != player_count + 2:
        raise ValueError("Incorrect number of Guild cards.")

    # Use one generator for all three Ages.
    generator = DeterministicRandom(seed)

    count_index = player_count - 3

    # Build the regular cards for each Age.
    age_one_cards = []
    for card_name, counts in AGE_I_CARDS.items():
        for _ in range(counts[count_index]):
            age_one_cards.append(card_name)

    age_two_cards = []
    for card_name, counts in AGE_II_CARDS.items():
        for _ in range(counts[count_index]):
            age_two_cards.append(card_name)

    age_three_cards = []
    for card_name, counts in AGE_III_CARDS.items():
        for _ in range(counts[count_index]):
            age_three_cards.append(card_name)

    # Add the selected Guild cards to Age III.
    age_three_cards.extend(selected_guilds)

    expected_count = player_count * 7

    if (
        len(age_one_cards) != expected_count
        or len(age_two_cards) != expected_count
        or len(age_three_cards) != expected_count
    ):
        raise ValueError("One or more Age decks have an incorrect size.")

    # Shuffle all Ages using the same generator, in order.
    age_one_deck = generator.shuffle(age_one_cards)
    age_two_deck = generator.shuffle(age_two_cards)
    age_three_deck = generator.shuffle(age_three_cards)

    return {
        "age_one": age_one_deck,
        "age_two": age_two_deck,
        "age_three": age_three_deck
    }

print("\n========== DETERMINISTIC SHUFFLE TEST ==========")

test_seed = bytes.fromhex(
    "ccdd2abe" + "11" * 28
)

cards = [
    "Card A",
    "Card B",
    "Card C",
    "Card D",
    "Card E",
    "Card F",
    "Card G"
]

shuffled_decks = []

for player_id in [1, 2, 3]:
    generator = DeterministicRandom(test_seed)

    shuffled = generator.shuffle(cards)

    shuffled_decks.append(shuffled)

    print("\nPlayer", player_id, "shuffled deck:")
    print(shuffled)

if (
    shuffled_decks[0] == shuffled_decks[1]
    == shuffled_decks[2]
):
    print("\nSUCCESS! All players shuffled the same deck.")
else:
    print("\nFAILED! Players shuffled different decks.")

if sorted(shuffled_decks[0]) == sorted(cards):
    print("SUCCESS! No cards were lost or duplicated.")
else:
    print("FAILED! The shuffled deck has incorrect cards.")



def deal_hand(deck, seat, player_count):
    if not 3 <= player_count <= 7:
        raise ValueError("The game must have 3 to 7 players.")

    if not 0 <= seat < player_count:
        raise ValueError("Invalid player seat.")

    if len(deck) != player_count * 7:
        raise ValueError("Incorrect deck size.")

    start_index = seat * 7
    end_index = start_index + 7

    return deck[start_index:end_index]