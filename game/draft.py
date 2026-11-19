import hashlib
import secrets
import time
import threading

from networking.packet import Packet


VALID_ACTIONS = ["BUILD", "WONDER_STAGE", "DISCARD"]

CARD_COMMIT = 0x0A
CARD_REVEAL = 0x0B
HAND_PASS = 0x0D

RESOURCE_QUERY = 0x0E
RESOURCE_OFFER = 0x0F
RESOURCE_BUY = 0x10

T_TURN_TIMEOUT = 8
T_RESOURCE_TIMEOUT = 5


def create_card_commitment(card_id, action):
    if action not in VALID_ACTIONS:
        raise ValueError("Invalid player action.")

    # Generate a fresh 256-bit nonce for this turn.
    nonce = secrets.token_bytes(32)

    # Convert the card ID and action into bytes.
    card_data = card_id.encode("utf-8")
    action_data = action.encode("utf-8")

    # Create the SHA-256 commitment.
    commitment = hashlib.sha256(
        card_data + action_data + nonce
    ).hexdigest()

    return {
        "commitment": commitment,
        "nonce": nonce.hex()
    }


def verify_card_commitment(card_id, action, nonce, commitment):
    if action not in VALID_ACTIONS:
        return False

    try:
        nonce_bytes = bytes.fromhex(nonce)
    except ValueError:
        return False

    if len(nonce_bytes) != 32:
        return False

    card_data = card_id.encode("utf-8")
    action_data = action.encode("utf-8")

    calculated_commitment = hashlib.sha256(
        card_data + action_data + nonce_bytes
    ).hexdigest()

    return calculated_commitment == commitment


def create_card_reveal(card_id, action, nonce):
    if action not in VALID_ACTIONS:
        raise ValueError("Invalid player action.")

    reveal = {
        "action": action,
        "nonce": nonce
    }

    # Only BUILD reveals the selected card.
    if action == "BUILD":
        reveal["card_id"] = card_id

    return reveal


def verify_card_reveal(reveal, commitment):
    action = reveal.get("action")
    nonce = reveal.get("nonce")

    if action not in VALID_ACTIONS:
        return False

    try:
        nonce_bytes = bytes.fromhex(nonce)
    except (ValueError, TypeError):
        return False

    if len(nonce_bytes) != 32:
        return False

    # BUILD reveals its card ID, so its commitment
    # can be fully verified.
    if action == "BUILD":
        card_id = reveal.get("card_id")

        if not card_id:
            return False

        return verify_card_commitment(
            card_id,
            action,
            nonce,
            commitment
        )

    # WONDER_STAGE and DISCARD do not reveal the card ID.
    return True

def create_resource_query(resource, qty):
    return {
        "resource": resource,
        "qty": qty
    }


def create_resource_offer(resource, qty_available, price_per_unit):
    return {
        "resource": resource,
        "qty_available": qty_available,
        "price_per_unit": price_per_unit
    }


def create_resource_buy(resource, qty, price_per_unit):
    return {
        "resource": resource,
        "qty": qty,
        "coins": qty * price_per_unit
    }

class DraftManager:
    def __init__(self, transport, session_id, local_peer_id, active_players, game_state=None):
        self.transport = transport
        self.session_id = session_id
        self.local_peer_id = local_peer_id
        self.active_players = active_players
        self.game_state = game_state

        self.commitments = {}
        self.reveals = {}
        self.resource_offers = {}
        self.resource_queries = {}
        self.sent_resource_offers = {}

        self.hand = None
        self.neighbors = None

        self.received_hand = None
        self.hand_pass_age = None
        self.hand_pass_turn = None
        self.hand_pass_sender = None

        self.lock = threading.Lock()

    def set_hand(self, cards):
        if len(cards) != 7:
            raise ValueError("A player's starting hand must contain 7 cards.")

        self.hand = list(cards)

        print(
            "Player", self.local_peer_id,
            "received starting hand:", self.hand
        )

    def set_neighbors(self, neighbors):
        self.neighbors = neighbors

        print(
            "Player", self.local_peer_id,
            "| Left:", neighbors["left"],
            "| Right:", neighbors["right"]
        )


    def remove_selected_card(self, card_id):
        if self.hand is None:
            raise ValueError("Player hand has not been assigned.")

        if card_id not in self.hand:
            raise ValueError("Selected card is not in the player's hand.")

        self.hand.remove(card_id)

        print(
            "Player", self.local_peer_id,
            "removed:", card_id,
            "| Remaining cards:", len(self.hand)
        )


    def handle_resource_query(self, payload, peer_id):
        if self.game_state is None:
            return

        resource = payload.get("resource")
        qty = payload.get("qty")

        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            return

        try:
            offer = self.game_state.create_resource_offer(
                peer_id,
                self.local_peer_id,
                resource
            )

            self.sent_resource_offers[(peer_id, resource)] = offer

            self.send_directed_message(
                peer_id,
                RESOURCE_OFFER,
                offer
            )

            print(
                "Player", self.local_peer_id,
                "sent RESOURCE_OFFER to Player", peer_id,
                "| Offer:", offer
            )

        except ValueError:
            print(
                "Player", self.local_peer_id,
                "cannot offer", resource,
                "to Player", peer_id
            )


    def handle_resource_offer(self, payload, peer_id):
        resource = payload.get("resource")
        qty_available = payload.get("qty_available")
        price_per_unit = payload.get("price_per_unit")

        query_key = (peer_id, resource)

        if query_key not in self.resource_queries:
            return

        if (
            not isinstance(qty_available, int)
            or isinstance(qty_available, bool)
            or qty_available <= 0
        ):
            return

        if (
            not isinstance(price_per_unit, int)
            or isinstance(price_per_unit, bool)
            or price_per_unit <= 0
        ):
            return

        self.resource_offers[query_key] = payload

        print(
            "Player", self.local_peer_id,
            "received RESOURCE_OFFER from Player", peer_id,
            "| Offer:", payload
        )

    
    def get_resource_offers(self, resource):
        offers = []

        with self.lock:
            for (peer_id, offered_resource), offer in self.resource_offers.items():
                if offered_resource == resource:
                    offers.append({
                        "seller_id": peer_id,
                        "resource": resource,
                        "qty_available": offer["qty_available"],
                        "price_per_unit": offer["price_per_unit"]
                    })

        # Show the cheapest offer first.
        offers.sort(key=lambda offer: offer["price_per_unit"])

        return offers

    
    def buy_resource_from_neighbors(self, resource, qty):
        if self.game_state is None:
            raise ValueError("Game state has not been assigned.")

        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ValueError("Quantity must be a positive integer.")

        offers = self.get_resource_offers(resource)

        if not offers:
            raise ValueError("No resource offers are available.")

        buyer = self.game_state.get_player(self.local_peer_id)

        if buyer is None:
            raise ValueError("Buyer does not exist.")

        # Calculate how much each seller can contribute.
        remaining_qty = qty
        total_cost = 0
        purchase_plan = []

        for offer in offers:
            if remaining_qty <= 0:
                break

            purchase_qty = min(
                remaining_qty,
                offer["qty_available"]
            )

            cost = purchase_qty * offer["price_per_unit"]

            purchase_plan.append({
                "seller_id": offer["seller_id"],
                "qty": purchase_qty,
                "cost": cost
            })

            remaining_qty -= purchase_qty
            total_cost += cost

        # Make sure the combined offers can cover the purchase.
        if remaining_qty > 0:
            raise ValueError("Neighbors cannot provide the required quantity.")

        # Check affordability before sending any purchases.
        if buyer.coins < total_cost:
            raise ValueError("Not enough coins for the resource purchase.")

        # Purchase from each seller.
        for purchase in purchase_plan:
            self.buy_resource_from_neighbor(
                purchase["seller_id"],
                resource,
                purchase["qty"]
            )

        print(
            "Player", self.local_peer_id,
            "completed split purchase of", qty, resource,
            "| Total coins paid:", total_cost
        )

        return total_cost


    def handle_resource_buy(self, payload, peer_id):
        if self.game_state is None:
            return

        resource = payload.get("resource")
        qty = payload.get("qty")
        coins = payload.get("coins")

        offer_key = (peer_id, resource)
        offer = self.sent_resource_offers.get(offer_key)

        if offer is None:
            return

        if (
            not isinstance(qty, int)
            or isinstance(qty, bool)
            or qty <= 0
            or qty > offer["qty_available"]
        ):
            return

        expected_coins = qty * offer["price_per_unit"]

        if coins != expected_coins:
            return

        seller = self.game_state.get_player(self.local_peer_id)

        if seller is None:
            return

        seller.coins += coins

        offer["qty_available"] -= qty

        print(
            "Player", self.local_peer_id,
            "received RESOURCE_BUY from Player", peer_id,
            "| Resource:", resource,
            "| Quantity:", qty,
            "| Coins received:", coins
        )

    def handle_message(self, message, peer_id):
        with self.lock:
            if message.message_type == CARD_COMMIT:
                print(
                    "Player", self.local_peer_id,
                    "received CARD_COMMIT from Player", peer_id
                )
                self.commitments[peer_id] = message.payload["commitment"]

            elif message.message_type == CARD_REVEAL:
                print(
                    "Player", self.local_peer_id,
                    "received CARD_REVEAL from Player", peer_id
                )
                self.reveals[peer_id] = message.payload

            elif message.message_type == HAND_PASS:
                payload = message.payload

                print(
                    "Player", self.local_peer_id,
                    "received HAND_PASS from Player", peer_id
                )

                self.received_hand = payload["cards"]
                self.hand_pass_age = payload["age"]
                self.hand_pass_turn = payload["turn"]
                self.hand_pass_sender = peer_id

            elif message.message_type == RESOURCE_QUERY:
                self.handle_resource_query(message.payload, peer_id)

            elif message.message_type == RESOURCE_OFFER:
                self.handle_resource_offer(message.payload, peer_id)

            elif message.message_type == RESOURCE_BUY:
                self.handle_resource_buy(message.payload, peer_id)


    def query_resource(self, seller_id, resource, qty):
        if self.game_state is None:
            raise ValueError("Game state has not been assigned.")

        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ValueError("Quantity must be a positive integer.")

        neighbors = self.game_state.get_neighbors(self.local_peer_id)

        if seller_id not in [neighbors["left"], neighbors["right"]]:
            raise ValueError("Resource seller must be a neighbor.")

        query_key = (seller_id, resource)

        with self.lock:
            self.resource_queries[query_key] = qty
            self.resource_offers.pop(query_key, None)

        self.send_directed_message(
            seller_id,
            RESOURCE_QUERY,
            create_resource_query(resource, qty)
        )

        print(
            "Player", self.local_peer_id,
            "sent RESOURCE_QUERY to Player", seller_id,
            "| Resource:", resource,
            "| Quantity needed:", qty
        )

    def wait_for_resource_offer(self, seller_id, resource):
        query_key = (seller_id, resource)

        for attempt in range(2):
            deadline = time.monotonic() + T_RESOURCE_TIMEOUT

            print(
                "Player", self.local_peer_id,
                "waiting for RESOURCE_OFFER from Player", seller_id,
                "| Attempt:", attempt + 1
            )

            while time.monotonic() < deadline:
                with self.lock:
                    offer = self.resource_offers.get(query_key)

                    if offer is not None:
                        print(
                            "Player", self.local_peer_id,
                            "received resource offer from Player", seller_id
                        )
                        return offer

                time.sleep(0.05)

            # Retry the RESOURCE_QUERY once if no offer arrived.
            if attempt == 0:
                print(
                    "Player", self.local_peer_id,
                    "timed out waiting for Player", seller_id,
                    "| Resending RESOURCE_QUERY."
                )

                qty = self.resource_queries.get(query_key)

                if qty is not None:
                    self.send_directed_message(
                        seller_id,
                        RESOURCE_QUERY,
                        create_resource_query(resource, qty)
                    )

        print(
            "Player", self.local_peer_id,
            "received no RESOURCE_OFFER from Player", seller_id,
            "after retry."
        )

        return None

    
    
    def query_available_neighbors(self, resource, qty, choices_by_peer=None):
        if self.game_state is None:
            raise ValueError("Game state has not been assigned.")

        if choices_by_peer is None:
            choices_by_peer = {}

        neighbors = self.game_state.get_neighbors(self.local_peer_id)
        eligible_neighbors = []

        for seller_id in [neighbors["left"], neighbors["right"]]:
            available = self.game_state.calculate_resources(
                seller_id,
                choices_by_peer.get(seller_id)
            )

            # A neighbor is eligible if they can provide
            # at least one unit of the requested resource.
            if available.get(resource, 0) > 0:
                eligible_neighbors.append(seller_id)

        if not eligible_neighbors:
            print(
                "No neighbor can provide", resource,
                "to Player", self.local_peer_id
            )
            return []

        for seller_id in eligible_neighbors:
            self.query_resource(seller_id, resource, qty)

        return eligible_neighbors

    
    def query_resource_with_fallback(self, resource, qty, choices_by_peer=None):
        if self.game_state is None:
            raise ValueError("Game state has not been assigned.")

        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ValueError("Quantity must be a positive integer.")

        if choices_by_peer is None:
            choices_by_peer = {}

        neighbors = self.game_state.get_neighbors(self.local_peer_id)
        remaining_qty = qty

        # Clear previous offers for this resource.
        with self.lock:
            for seller_id in [neighbors["left"], neighbors["right"]]:
                self.resource_offers.pop((seller_id, resource), None)
                self.resource_queries.pop((seller_id, resource), None)

        # Check the left neighbor first, then the right neighbor.
        for seller_id in [neighbors["left"], neighbors["right"]]:
            available = self.game_state.calculate_resources(
                seller_id,
                choices_by_peer.get(seller_id)
            )

            # Skip neighbors that cannot produce this resource.
            if available.get(resource, 0) <= 0:
                continue

            print(
                "Player", self.local_peer_id,
                "trying Player", seller_id,
                "for", remaining_qty, resource
            )

            self.query_resource(seller_id, resource, remaining_qty)

            offer = self.wait_for_resource_offer(seller_id, resource)

            if offer is None:
                print(
                    "Player", seller_id,
                    "did not respond. Trying the other neighbor."
                )
                continue

            received_qty = min(
                remaining_qty,
                offer["qty_available"]
            )

            remaining_qty -= received_qty

            print(
                "Player", self.local_peer_id,
                "can obtain", received_qty, resource,
                "from Player", seller_id,
                "| Still needed:", remaining_qty
            )

            if remaining_qty == 0:
                print("SUCCESS! Enough resources have been offered.")
                return True

        if remaining_qty > 0:
            print(
                "Player", self.local_peer_id,
                "could not obtain enough", resource,
                "| Still needed:", remaining_qty
            )
            return False

        return True


    def buy_resource_from_neighbor(self, seller_id, resource, qty):
        if self.game_state is None:
            raise ValueError("Game state has not been assigned.")

        query_key = (seller_id, resource)

        with self.lock:
            offer = self.resource_offers.get(query_key)
            requested_qty = self.resource_queries.get(query_key)

            if offer is None or requested_qty is None:
                raise ValueError("No resource offer is available.")

            if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
                raise ValueError("Quantity must be a positive integer.")

            if qty > requested_qty or qty > offer["qty_available"]:
                raise ValueError("Purchase exceeds the requested or offered quantity.")

            total_cost = qty * offer["price_per_unit"]

            buyer = self.game_state.get_player(self.local_peer_id)

            if buyer is None or buyer.coins < total_cost:
                raise ValueError("Not enough coins.")

            self.send_directed_message(
                seller_id,
                RESOURCE_BUY,
                create_resource_buy(
                    resource,
                    qty,
                    offer["price_per_unit"]
                )
            )

            buyer.coins -= total_cost

            offer["qty_available"] -= qty
            self.resource_queries[query_key] -= qty

            print(
                "Player", self.local_peer_id,
                "bought", qty, resource,
                "from Player", seller_id,
                "| Coins paid:", total_cost
            )

            return total_cost


    def register_callbacks(self):
        for peer_id, peer in self.transport.peers.items():
            previous_callback = peer["on_message"]

            def callback(message, peer_id=peer_id,
                         previous_callback=previous_callback):
                if previous_callback:
                    previous_callback(message)

                self.handle_message(message, peer_id)

            peer["on_message"] = callback

    def broadcast_message(self, message_type, payload):
        for peer_id, peer in list(self.transport.peers.items()):
            packet = Packet(
                message_type=message_type,
                session_id=self.session_id,
                sender_peer_id=self.local_peer_id,
                sequence_number=0,
                ack_number=0,
                payload=payload
            )

            self.transport.send_reliable_packet(
                packet,
                peer["outgoing_channel"],
                peer["address"],
                peer["incoming_channel"]
            )

    def send_directed_message(self, peer_id, message_type, payload):
        if peer_id not in self.transport.peers:
            raise ValueError("Peer is not connected.")

        peer = self.transport.peers[peer_id]

        packet = Packet(
            message_type=message_type,
            session_id=self.session_id,
            sender_peer_id=self.local_peer_id,
            sequence_number=0,
            ack_number=0,
            payload=payload
        )

        self.transport.send_reliable_packet(
            packet,
            peer["outgoing_channel"],
            peer["address"],
            peer["incoming_channel"]
        )

    def prepare_hand_pass(self, age, turn):
        with self.lock:
            self.received_hand = None
            self.hand_pass_age = None
            self.hand_pass_turn = None
            self.hand_pass_sender = None

        print(
            "Player", self.local_peer_id,
            "is ready to receive HAND_PASS for Age", age,
            "| Turn:", turn
        )

    def pass_hand(self, age, turn):
        if self.hand is None:
            raise ValueError("Player hand has not been assigned.")

        if self.neighbors is None:
            raise ValueError("Player neighbors have not been assigned.")

        if age == 2:
            target_peer_id = self.neighbors["right"]
            expected_sender_id = self.neighbors["left"]

        elif age in [1, 3]:
            target_peer_id = self.neighbors["left"]
            expected_sender_id = self.neighbors["right"]

        else:
            raise ValueError("Invalid Age.")

        # On Turn 6, silently discard the last unplayed card.
        if turn == 6:
            if len(self.hand) != 1:
                raise ValueError("Turn 6 must have exactly one remaining card.")

            self.hand.clear()
            print("Player", self.local_peer_id, "silently discarded the final card.")

        # Save the remaining hand for this exchange.
        cards_to_send = list(self.hand)

        payload = {
            "age": age,
            "turn": turn,
            "cards": cards_to_send
        }

        # Send the hand directly to the correct neighbor.
        peer = self.transport.peers[target_peer_id]

        packet = Packet(
            message_type=HAND_PASS,
            session_id=self.session_id,
            sender_peer_id=self.local_peer_id,
            sequence_number=0,
            ack_number=0,
            payload=payload
        )

        self.transport.send_reliable_packet(
            packet,
            peer["outgoing_channel"],
            peer["address"],
            peer["incoming_channel"]
        )

        print(
            "Player", self.local_peer_id,
            "sent HAND_PASS to Player", target_peer_id,
            "| Cards:", cards_to_send
        )

        # Wait until the expected neighbor sends their hand.
        deadline = time.monotonic() + T_TURN_TIMEOUT

        while time.monotonic() < deadline:
            with self.lock:
                if (
                    self.received_hand is not None
                    and self.hand_pass_age == age
                    and self.hand_pass_turn == turn
                    and self.hand_pass_sender == expected_sender_id
                ):
                    self.hand = list(self.received_hand)

                    print(
                        "Player", self.local_peer_id,
                        "received new hand from Player", expected_sender_id,
                        "| Cards:", self.hand
                    )

                    return True

            time.sleep(0.05)

        print(
            "Player", self.local_peer_id,
            "timed out waiting for HAND_PASS from Player",
            expected_sender_id
        )

        return False

    def wait_for_players(self, received_messages, phase):
        deadline = time.monotonic() + T_TURN_TIMEOUT

        while time.monotonic() < deadline:
            with self.lock:
                received_ids = sorted(received_messages.keys())
                expected_ids = sorted(self.active_players)

                if all(
                    peer_id in received_messages
                    for peer_id in self.active_players
                ):
                    print(
                        "Player", self.local_peer_id,
                        "completed", phase,
                        "| Received:", received_ids
                    )
                    return True

            time.sleep(0.05)

        with self.lock:
            print(
                "Player", self.local_peer_id,
                "timed out during", phase,
                "| Expected:", expected_ids,
                "| Received:", sorted(received_messages.keys())
            )

        return False

    def prepare_draft_turn(self):
        with self.lock:
            self.commitments.clear()
            self.reveals.clear()

        print("Player", self.local_peer_id, "is ready for a new draft turn.")

    def run_turn(self, card_id, action):
        print("\nPlayer", self.local_peer_id, "starting draft turn.")

        # PHASE 1: CARD COMMIT
        result = create_card_commitment(card_id, action)

        with self.lock:
            self.commitments[self.local_peer_id] = result["commitment"]

        self.broadcast_message(
            CARD_COMMIT,
            {"commitment": result["commitment"]}
        )

        print("Player", self.local_peer_id, "sent CARD_COMMIT.")

        if not self.wait_for_players(self.commitments, "CARD_COMMIT"):
            print("Player", self.local_peer_id, "timed out waiting for commitments.")
            return False

        print("Player", self.local_peer_id, "received all commitments.")

        # PHASE 2: CARD REVEAL

        reveal = create_card_reveal(
            card_id,
            action,
            result["nonce"]
        )

        with self.lock:
            self.reveals[self.local_peer_id] = reveal

        self.broadcast_message(CARD_REVEAL, reveal)

        print("Player", self.local_peer_id, "sent CARD_REVEAL.")

        if not self.wait_for_players(self.reveals, "CARD_REVEAL"):
            print("Player", self.local_peer_id, "timed out waiting for reveals.")
            return False

        print("Player", self.local_peer_id, "received all reveals.")

        # PHASE 3: VERIFY REVEALS

        with self.lock:
            for peer_id in self.active_players:
                if not verify_card_reveal(
                    self.reveals[peer_id],
                    self.commitments[peer_id]
                ):
                    print("Invalid reveal from Player", peer_id)
                    return False

        print("Player", self.local_peer_id, "verified all reveals.")

        # Remove the selected card after a successful draft.
        self.remove_selected_card(card_id)

        return True

    
    
    def run_turn_and_resolve(self, game_state, card_id, action):
        success = self.run_turn(card_id, action)

        if not success:
            return False

        with self.lock:
            turn_reveals = dict(self.reveals)

        try:
            game_state.resolve_draft_actions(turn_reveals)
            return True

        except (ValueError, KeyError) as error:
            print("Could not resolve turn:", error)
            return False

