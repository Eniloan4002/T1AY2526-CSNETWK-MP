from game.card_database import get_card_by_name
from game.wonder_database import get_wonder_stages

RAW_MATERIALS = ["WOOD", "ORE", "CLAY", "STONE"]
MANUFACTURED_GOODS = ["GLASS", "PAPYRUS", "TEXTILE"]
WONDER_STARTING_RESOURCES = {
    "Alexandria": "GLASS",
    "Babylon": "CLAY",
    "Ephesos": "PAPYRUS",
    "Giza": "STONE",
    "Gizah": "STONE",
    "Halikarnassus": "TEXTILE",
    "Olympia": "WOOD",
    "Rhodes": "ORE",
    "Rhodos": "ORE"
}


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

        self.resources = {
            "WOOD": 0,
            "ORE": 0,
            "CLAY": 0,
            "STONE": 0,
            "GLASS": 0,
            "PAPYRUS": 0,
            "TEXTILE": 0
        }

        self.wonder_vp = 0
        self.wonder_abilities = []
        self.action_log = []

        starting_resource = WONDER_STARTING_RESOURCES.get(wonder_board)

        if starting_resource:
            self.resources[starting_resource] += 1


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

    
    def get_neighbors(self, peer_id):
        player = self.get_player(peer_id)

        if player is None:
            raise ValueError("Player does not exist.")

        ordered_players = sorted(
            self.players.values(),
            key=lambda player: player.seat
        )

        player_count = len(ordered_players)

        if player_count < 3:
            raise ValueError("A game requires at least 3 players.")

        player_index = next(
            index for index, current_player in enumerate(ordered_players)
            if current_player.peer_id == peer_id
        )

        left_neighbor = ordered_players[
            (player_index - 1) % player_count
        ]

        right_neighbor = ordered_players[
            (player_index + 1) % player_count
        ]

        return {
            "left": left_neighbor.peer_id,
            "right": right_neighbor.peer_id
        }


    def get_resource_price(self, buyer_id, seller_id, resource):
        buyer = self.get_player(buyer_id)

        if buyer is None or self.get_player(seller_id) is None:
            raise ValueError("Player does not exist.")

        neighbors = self.get_neighbors(buyer_id)

        if seller_id not in [neighbors["left"], neighbors["right"]]:
            raise ValueError("Player is not a neighbor.")

        if resource not in RAW_MATERIALS + MANUFACTURED_GOODS:
            raise ValueError("Invalid resource.")

        price = 2

        if resource in RAW_MATERIALS:
            if seller_id == neighbors["left"]:
                if any(card["name"] == "West Trading Post"
                       for card in buyer.built_cards):
                    price = 1

            elif seller_id == neighbors["right"]:
                if any(card["name"] == "East Trading Post"
                       for card in buyer.built_cards):
                    price = 1

        elif resource in MANUFACTURED_GOODS:
            if any(card["name"] == "Marketplace"
                   for card in buyer.built_cards):
                price = 1

        # Olympia Wonder Side B, first stage discount.
        if (resource in RAW_MATERIALS
                and buyer.wonder_board == "Olympia"
                and buyer.wonder_side == "B"
                and buyer.wonder_stages >= 1):
            price = 1

        return price

    def create_resource_offer(self, buyer_id, seller_id, resource, choices=None):
        buyer = self.get_player(buyer_id)
        seller = self.get_player(seller_id)

        if buyer is None or seller is None:
            raise ValueError("Player does not exist.")

        if resource not in RAW_MATERIALS + MANUFACTURED_GOODS:
            raise ValueError("Invalid resource.")

        # Check how many units the seller can produce.
        seller_resources = self.calculate_resources(seller_id, choices)
        qty_available = seller_resources.get(resource, 0)

        if qty_available <= 0:
            raise ValueError("Seller does not produce this resource.")

        # The price depends on the BUYER's discounts.
        price_per_unit = self.get_resource_price(
            buyer_id,
            seller_id,
            resource
        )

        return {
            "resource": resource,
            "qty_available": qty_available,
            "price_per_unit": price_per_unit
        }

    
    
    def check_trade_plan(self, buyer_id, trades, seller_choices=None):
        buyer = self.get_player(buyer_id)

        if buyer is None:
            raise ValueError("Player does not exist.")

        if seller_choices is None:
            seller_choices = {}

        total_cost = 0
        purchased_resources = {}
        seller_requirements = {}

        for trade in trades:
            seller_id = trade["seller_id"]
            resource = trade["resource"]
            amount = trade["amount"]

            if not isinstance(amount, int) or amount <= 0:
                return False

            if resource not in RAW_MATERIALS + MANUFACTURED_GOODS:
                return False

            if seller_id not in self.players:
                return False

            neighbors = self.get_neighbors(buyer_id)

            if seller_id not in [neighbors["left"], neighbors["right"]]:
                return False

            if seller_id not in seller_requirements:
                seller_requirements[seller_id] = {}

            if resource not in seller_requirements[seller_id]:
                seller_requirements[seller_id][resource] = 0

            seller_requirements[seller_id][resource] += amount

            price = self.get_resource_price(
                buyer_id, seller_id, resource
            )

            total_cost += price * amount

            if resource not in purchased_resources:
                purchased_resources[resource] = 0

            purchased_resources[resource] += amount

        for seller_id, requirements in seller_requirements.items():
            available = self.calculate_resources(
                seller_id,
                seller_choices.get(seller_id)
            )

            for resource, amount in requirements.items():
                if available.get(resource, 0) < amount:
                    return False

        if buyer.coins < total_cost:
            return False

        return {
            "total_cost": total_cost,
            "resources": purchased_resources
        }
    
    

    def buy_resource(self, buyer_id, seller_id, resource, choices=None, qty=1):
        buyer = self.get_player(buyer_id)
        seller = self.get_player(seller_id)

        if buyer is None or seller is None:
            raise ValueError("Player does not exist.")

        if resource not in RAW_MATERIALS + MANUFACTURED_GOODS:
            raise ValueError("Invalid resource.")

        if not isinstance(qty, int) or qty <= 0:
            raise ValueError("Quantity must be a positive integer.")

        seller_resources = self.calculate_resources(seller_id, choices)

        if seller_resources.get(resource, 0) < qty:
            raise ValueError("Neighbor does not produce enough resources.")

        price = self.get_resource_price(buyer_id, seller_id, resource)
        total_cost = price * qty

        if buyer.coins < total_cost:
            raise ValueError("Not enough coins.")

        buyer.coins -= total_cost
        seller.coins += total_cost

        return total_cost


    def complete_wonder_stage(
        self, peer_id, choices=None, trades=None, seller_choices=None
    ):
        player = self.get_player(peer_id)

        if player is None:
            return False

        if trades is None:
            trades = []

        if not self.can_afford_wonder_stage(
            peer_id, choices, trades, seller_choices
        ):
            return False

        stages = get_wonder_stages(
            player.wonder_board, player.wonder_side
        )

        stage = stages[player.wonder_stages]
        trade_plan = self.check_trade_plan(
            peer_id, trades, seller_choices
        )

        # Pay the sellers for purchased resources.
        player.coins -= trade_plan["total_cost"]

        for trade in trades:
            seller = self.get_player(trade["seller_id"])
            price = self.get_resource_price(
                peer_id, trade["seller_id"], trade["resource"]
            )
            seller.coins += price * trade["amount"]

        # Complete the Wonder stage.
        player.wonder_stages += 1

        # Apply basic stage rewards.
        reward = stage["reward"]

        player.wonder_vp += reward.get("vp", 0)
        player.coins += reward.get("coins", 0)
        player.military_shields += reward.get("shields", 0)

        if "special" in reward:
            player.wonder_abilities.append(reward["special"])

        self.public_log.append({
            "action": "WONDER_STAGE",
            "peer_id": peer_id,
            "wonder_board": player.wonder_board,
            "wonder_side": player.wonder_side,
            "stage": player.wonder_stages,
            "reward": reward,
            "trades": trades
        })

        return True

    def discard_card(self, peer_id):
        player = self.get_player(peer_id)

        if player is None:
            raise ValueError("Player does not exist.")

        player.coins += 3

        self.public_log.append({
            "peer_id": peer_id,
            "action": "DISCARD"
        })

    
    
    
    
    def can_afford_card(self, peer_id, card_name, choices=None,
                        trades=None, seller_choices=None):
        player = self.get_player(peer_id)
        card = get_card_by_name(card_name, self.current_age)

        if player is None or card is None:
            return False

        if trades is None:
            trades = []

        trade_plan = self.check_trade_plan(
            peer_id, trades, seller_choices
        )

        if trade_plan is False:
            return False

        required_coins = card["cost"]["coins"] + trade_plan["total_cost"]

        if player.coins < required_coins:
            return False

        available_resources = self.calculate_resources(peer_id, choices)

        for resource, amount in trade_plan["resources"].items():
            available_resources[resource] += amount

        for resource, amount in card["cost"]["resources"].items():
            if available_resources.get(resource, 0) < amount:
                return False

        return True

    
    
    def build_card(self, peer_id, card_name, cost_paid=None,
                   choices=None, trades=None, seller_choices=None):
        player = self.get_player(peer_id)
        card = get_card_by_name(card_name, self.current_age)

        if player is None:
            raise ValueError("Player does not exist.")

        if card is None:
            raise ValueError("Card does not exist in the current Age.")

        if card_name in [built_card["name"] for built_card in player.built_cards]:
            raise ValueError("Card has already been built.")

        if trades is None:
            trades = []

        trade_plan = self.check_trade_plan(
            peer_id, trades, seller_choices
        )

        if trade_plan is False:
            raise ValueError("Invalid trade plan.")

        if not self.can_afford_card(
            peer_id, card_name, choices, trades, seller_choices
        ):
            raise ValueError("Player cannot afford this card.")

        player.coins -= card["cost"]["coins"] + trade_plan["total_cost"]

        for trade in trades:
            seller = self.get_player(trade["seller_id"])
            price = self.get_resource_price(
                peer_id, trade["seller_id"], trade["resource"]
            )
            seller.coins += price * trade["amount"]

        player.built_cards.append(card)

        self.public_log.append({
            "peer_id": peer_id,
            "action": "BUILD",
            "card_id": card_name,
            "cost_paid": cost_paid,
            "trades": trades
        })

    
    def calculate_resources(self, peer_id, choices=None):
        player = self.get_player(peer_id)

        if player is None:
            raise ValueError("Player does not exist.")

        resources = player.resources.copy()

        for card in player.built_cards:
            production = card.get("production", {})

            fixed = production.get("fixed", {})

            for resource, amount in fixed.items():
                resources[resource] += amount

            for options in production.get("choices", []):
                selected_resource = None

                if choices:
                    selected_resource = choices.get(card["name"])

                if selected_resource not in options:
                    continue

                resources[selected_resource] += 1

        return resources

    def can_afford_wonder_stage(
        self, peer_id, choices=None, trades=None, seller_choices=None
    ):
        player = self.get_player(peer_id)

        if player is None:
            return False

        stages = get_wonder_stages(
            player.wonder_board, player.wonder_side
        )

        if stages is None or player.wonder_stages >= len(stages):
            return False

        if trades is None:
            trades = []

        trade_plan = self.check_trade_plan(
            peer_id, trades, seller_choices
        )

        if trade_plan is False:
            return False

        available_resources = self.calculate_resources(peer_id, choices)

        for resource, amount in trade_plan["resources"].items():
            available_resources[resource] += amount

        next_stage = stages[player.wonder_stages]

        for resource, amount in next_stage["cost"].items():
            if available_resources.get(resource, 0) < amount:
                return False

        if player.coins < trade_plan["total_cost"]:
            return False

        return True

    
    def apply_action(
        self, peer_id, action, card_id=None,
        choices=None, trades=None, seller_choices=None
    ):
        if action == "BUILD":
            if card_id is None:
                raise ValueError("A card ID is required for BUILD.")

            self.build_card(
                peer_id,
                card_id,
                choices=choices,
                trades=trades,
                seller_choices=seller_choices
            )

            return True

        elif action == "WONDER_STAGE":
            return self.complete_wonder_stage(
                peer_id,
                choices,
                trades,
                seller_choices
            )

        elif action == "DISCARD":
            self.discard_card(peer_id)
            return True

        else:
            raise ValueError("Invalid player action.")

    
    def resolve_draft_actions(self, reveals):
        if set(reveals.keys()) != set(self.players.keys()):
            raise ValueError("Actions from all players are required.")

        # Check all actions before changing the game state.
        for peer_id, reveal in reveals.items():
            action = reveal.get("action")
            card_id = reveal.get("card_id")

            if action == "BUILD":
                if card_id is None:
                    raise ValueError("BUILD requires a card ID.")

                if not self.can_afford_card(peer_id, card_id):
                    raise ValueError(
                        "Player cannot afford the selected card."
                    )

            elif action == "WONDER_STAGE":
                if not self.can_afford_wonder_stage(peer_id):
                    raise ValueError(
                        "Player cannot afford the next Wonder stage."
                    )

            elif action != "DISCARD":
                raise ValueError("Invalid player action.")

        # Apply actions in seating order for consistent processing.
        ordered_players = sorted(
            self.players.values(),
            key=lambda player: player.seat
        )

        for player in ordered_players:
            reveal = reveals[player.peer_id]

            self.apply_action(
                player.peer_id,
                reveal["action"],
                card_id=reveal.get("card_id")
            )

        return True
