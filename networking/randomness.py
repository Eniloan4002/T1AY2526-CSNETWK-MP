
import hashlib
import secrets
import threading
import time

from networking.packet import Packet


SEED_COMMIT = 0x07
SEED_REVEAL = 0x08

T_SEED_TIMEOUT = 10
MIN_PLAYERS = 3


class RandomnessCeremony:
    def __init__(self, transport, session_id, local_peer_id):
        self.transport = transport
        self.session_id = session_id
        self.local_peer_id = local_peer_id

        # Generate a random 256-bit nonce for this player.
        self.nonce = secrets.token_bytes(32)

        # Create the SHA-256 commitment.
        self.commitment = hashlib.sha256(self.nonce).hexdigest()

        # Store commitments and revealed nonces from other players.
        self.commitments = {
            local_peer_id: self.commitment
        }

        self.reveals = {
            local_peer_id: self.nonce
        }

        self.lock = threading.Lock()
        self.active_peer_ids = [local_peer_id]
        self.shared_seed = None

    def handle_message(self, message, peer_id):
        with self.lock:
            if message.message_type == SEED_COMMIT:
                commitment = message.payload.get("commitment")

                if not isinstance(commitment, str) or len(commitment) != 64:
                    print("Invalid commitment from Player", peer_id)
                    return

                self.commitments[peer_id] = commitment

            elif message.message_type == SEED_REVEAL:
                nonce_hex = message.payload.get("nonce")

                if not isinstance(nonce_hex, str):
                    print("Invalid reveal from Player", peer_id)
                    return

                try:
                    nonce = bytes.fromhex(nonce_hex)
                except ValueError:
                    print("Invalid nonce from Player", peer_id)
                    return

                if len(nonce) != 32:
                    print("Incorrect nonce length from Player", peer_id)
                    return

                self.reveals[peer_id] = nonce

    def broadcast(self, message_type, payload):
        for peer_id in self.active_peer_ids:
            if peer_id == self.local_peer_id:
                continue

            peer = self.transport.peers.get(peer_id)

            if peer is None:
                continue

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
        deadline = time.monotonic() + T_SEED_TIMEOUT

        while time.monotonic() < deadline:
            with self.lock:
                if all(
                    peer_id in received_messages
                    for peer_id in self.active_peer_ids
                ):
                    return True

            time.sleep(0.05)

        return False

    def start(self):
        # Register the message handler for each connected player.
        for peer_id, peer in self.transport.peers.items():
            peer["on_message"] = (
                lambda message, player_id=peer_id:
                self.handle_message(message, player_id)
            )

        # Include the local player in the participant list.
        self.active_peer_ids = sorted(
            [self.local_peer_id] + list(self.transport.peers.keys())
        )

        print("\n========== RANDOMNESS CEREMONY ==========")
        print("Players participating:", self.active_peer_ids)

        # PHASE 1: Broadcast commitments.
        self.broadcast(
            SEED_COMMIT,
            {"commitment": self.commitment}
        )

        print("Player", self.local_peer_id, "sent SEED_COMMIT.")

        self.wait_for_players(self.commitments)

        # Remove players whose commitments were not received.
        with self.lock:
            self.active_peer_ids = [
                peer_id for peer_id in self.active_peer_ids
                if peer_id in self.commitments
            ]

        if len(self.active_peer_ids) < MIN_PLAYERS:
            print("Not enough players for the randomness ceremony.")
            return False

        # PHASE 2: Reveal the nonce.
        self.broadcast(
            SEED_REVEAL,
            {"nonce": self.nonce.hex()}
        )

        print("Player", self.local_peer_id, "sent SEED_REVEAL.")

        self.wait_for_players(self.reveals)

        # Remove players whose reveals were not received.
        with self.lock:
            self.active_peer_ids = [
                peer_id for peer_id in self.active_peer_ids
                if peer_id in self.reveals
            ]

        if len(self.active_peer_ids) < MIN_PLAYERS:
            print("Not enough players after the reveal phase.")
            return False

        # PHASE 3: Verify every revealed nonce.
        valid_nonces = {}

        with self.lock:
            for peer_id in self.active_peer_ids:
                nonce = self.reveals[peer_id]
                expected_commitment = self.commitments[peer_id]

                actual_commitment = hashlib.sha256(
                    nonce
                ).hexdigest()

                if actual_commitment != expected_commitment:
                    print("Commitment mismatch from Player", peer_id)
                    return False

                valid_nonces[peer_id] = nonce

        # PHASE 4: Calculate the shared seed.
        combined_nonces = b""

        for peer_id in sorted(valid_nonces):
            combined_nonces += valid_nonces[peer_id]

        self.shared_seed = hashlib.sha256(
            combined_nonces
        ).digest()

        print("All commitments verified.")
        print("Shared seed:", self.shared_seed.hex())
        print("Active players:", self.active_peer_ids)
        print("Randomness ceremony completed!")

        return True