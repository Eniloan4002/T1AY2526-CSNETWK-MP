from game.card_database import get_card_by_name

class PlayerState:
    def __init__(self, peer_id, seat, wonder_board, wonder_side):
        self.peer_id = peer_id
        self.seat = seat
        self.wonder_board = wonder_board
        self.wonder_side = wonder_side

        # Starting player information
        self.coins = 3
        self.built_cards = []
        self.wonder_stages = 0
        self.military_shields = 0
        self.military_tokens = 0

        # Resources produced by the player's board and built cards
        self.resources = {
            "WOOD": 0,
            "ORE": 0,
            "CLAY": 0,
            "STONE": 0,
            "GLASS": 0,
            "PAPYRUS": 0,
            "TEXTILE": 0
        }


class GameState:
    def __init__(self, players):
        self.players = {}

        for player in players:
            peer_id = player["peer_id"]

            self.players[peer_id] = PlayerState(
                peer_id,
                player["seat"],
                player["wonder_board"],
                player["wonder_side"]
            )

        self.current_age = 1
        self.current_turn = 1
        self.public_log = []

    def get_player(self, peer_id):
        return self.players.get(peer_id)


    def complete_wonder_stage(self, peer_id, stage_index):
        player = self.get_player(peer_id)

        if player is None:
            raise ValueError("Player does not exist.")

        player.wonder_stages += 1

        self.public_log.append({
            "peer_id": peer_id,
            "action": "WONDER_STAGE",
            "stage_index": stage_index
        })

    def discard_card(self, peer_id):
        player = self.get_player(peer_id)

        if player is None:
            raise ValueError("Player does not exist.")

        player.coins += 3

        self.public_log.append({
            "peer_id": peer_id,
            "action": "DISCARD"
        })

    
    def can_afford_card(self, peer_id, card_name):
        player = self.get_player(peer_id)
        card = get_card_by_name(card_name, self.current_age)

        if player is None or card is None:
            return False

        required_coins = card["cost"]["coins"]

        return player.coins >= required_coins

    def build_card(self, peer_id, card_name, cost_paid=None):
        player = self.get_player(peer_id)
        card = get_card_by_name(card_name, self.current_age)

        if player is None:
            raise ValueError("Player does not exist.")

        if card is None:
            raise ValueError("Card does not exist in the current Age.")

        if card_name in player.built_cards:
            raise ValueError("Player has already built this card.")

        if not self.can_afford_card(peer_id, card_name):
            raise ValueError("Player cannot afford this card.")

        player.coins -= card["cost"]["coins"]
        player.built_cards.append(card)

        self.public_log.append({
            "peer_id": peer_id,
            "action": "BUILD",
            "card_id": card_name,
            "cost_paid": cost_paid
        })
