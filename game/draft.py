
import hashlib
import secrets
import time
import threading

from networking.packet import Packet


VALID_ACTIONS = ["BUILD", "WONDER_STAGE", "DISCARD"]

CARD_COMMIT = 0x0A
CARD_REVEAL = 0x0B
HAND_PASS = 0x0D

T_TURN_TIMEOUT = 8


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


class DraftManager:
    def __init__(self, transport, session_id, local_peer_id, active_players):
        self.transport = transport
        self.session_id = session_id
        self.local_peer_id = local_peer_id
        self.active_players = active_players

        self.commitments = {}
        self.reveals = {}

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

