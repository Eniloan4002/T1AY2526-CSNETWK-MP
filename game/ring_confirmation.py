
import threading
import time

from networking.packet import Packet


RING_CONFIRM = 0x09
ERROR = 0x14


class RingConfirmation:
    def __init__(self, transport, session_id, local_peer_id, setup):
        self.transport = transport
        self.session_id = session_id
        self.local_peer_id = local_peer_id
        self.setup = setup

        self.confirmed_players = set()
        self.confirmed_players.add(local_peer_id)

        self.lock = threading.Lock()
        self.completed = threading.Event()
        self.error = None

        # The information this player calculated for itself.
        self.local_assignment = setup["wonder_assignments"][local_peer_id]

    def send_to_all(self, message_type, payload):
        for peer_id, peer in self.transport.peers.items():
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

    def send_error(self, offending_peer, code, detail):
        payload = {
            "code": code,
            "offending_peer": offending_peer,
            "detail": detail
        }

        print("\nPROTOCOL VIOLATION:", detail)
        self.send_to_all(ERROR, payload)

    def handle_message(self, message, peer_id):
        if message.message_type == RING_CONFIRM:
            self.handle_ring_confirm(message, peer_id)

        elif message.message_type == ERROR:
            print(
                "\nERROR received from Player",
                peer_id,
                ":",
                message.payload
            )
            self.error = message.payload
            self.completed.set()

    def handle_ring_confirm(self, message, peer_id):
        payload = message.payload

        if not isinstance(payload, dict):
            self.error = "Invalid RING_CONFIRM payload."
            self.completed.set()
            self.send_error(
                peer_id,
                "MALFORMED_MESSAGE",
                self.error
            )
            return

        expected_assignment = self.setup["wonder_assignments"].get(peer_id)

        if expected_assignment is None:
            self.error = "Unknown player sent RING_CONFIRM."
            self.completed.set()
            self.send_error(
                peer_id,
                "RING_MISMATCH",
                self.error
            )
            return

        expected_seat = expected_assignment["seat"]
        expected_board = expected_assignment["wonder_board"]
        expected_side = expected_assignment["wonder_side"]

        received_seat = payload.get("seat")
        received_board = payload.get("wonder_board")
        received_side = payload.get("wonder_side")

        if (
            received_seat != expected_seat
            or received_board != expected_board
            or received_side != expected_side
        ):
            self.error = (
                "Player " + str(peer_id)
                + " has an inconsistent seating or Wonder assignment."
            )

            self.completed.set()

            self.send_error(
                peer_id,
                "RING_MISMATCH",
                self.error
            )
            return

        with self.lock:
            self.confirmed_players.add(peer_id)

            print("RING_CONFIRM verified from Player", peer_id)

            if len(self.confirmed_players) == len(self.setup["seating_order"]):
                self.completed.set()

    def start(self, timeout=10):
        # Register the message handler for every connected peer.
        for peer_id, peer in self.transport.peers.items():
            peer["on_message"] = (
                lambda message, player_id=peer_id:
                self.handle_message(message, player_id)
            )

        payload = {
            "seat": self.local_assignment["seat"],
            "wonder_board": self.local_assignment["wonder_board"],
            "wonder_side": self.local_assignment["wonder_side"]
        }

        print("\n========== RING CONFIRMATION ==========")
        print("Your seat:", payload["seat"])
        print("Your Wonder:", payload["wonder_board"])
        print("Your Wonder side:", payload["wonder_side"])

        # Broadcast this player's own assignment.
        self.send_to_all(RING_CONFIRM, payload)

        print("RING_CONFIRM sent to all players.")

        # Wait until every player has been verified.
        if not self.completed.wait(timeout):
            self.error = "Timed out waiting for RING_CONFIRM messages."
            print(self.error)
            return False

        if self.error:
            return False

        print("\nAll player assignments verified!")
        print("Ring confirmation completed.")

        return True