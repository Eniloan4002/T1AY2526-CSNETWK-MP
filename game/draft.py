
import hashlib
import secrets
import time
import threading

from networking.packet import Packet


VALID_ACTIONS = ["BUILD", "WONDER_STAGE", "DISCARD"]

CARD_COMMIT = 0x0A
CARD_REVEAL = 0x0B

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

        self.lock = threading.Lock()

    def handle_message(self, message, peer_id):
        with self.lock:
            if message.message_type == CARD_COMMIT:
                self.commitments[peer_id] = message.payload["commitment"]

            elif message.message_type == CARD_REVEAL:
                self.reveals[peer_id] = message.payload

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

    def wait_for_players(self, received_messages):
        deadline = time.monotonic() + T_TURN_TIMEOUT

        while time.monotonic() < deadline:
            with self.lock:
                if all(
                    peer_id in received_messages
                    for peer_id in self.active_players
                ):
                    return True

            time.sleep(0.05)

        return False

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

        if not self.wait_for_players(self.commitments):
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

        if not self.wait_for_players(self.reveals):
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
        return True