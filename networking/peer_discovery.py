import time
import threading

from networking.packet import Packet
from networking.udp import UDPTransport


HELLO = 0x05
HELLO_ACK = 0x06

T_JOIN_TIMEOUT = 10


class PeerDiscovery:
    def __init__(self, transport, session_id, local_peer_id, manifest):
        self.transport = transport
        self.session_id = session_id
        self.local_peer_id = local_peer_id
        self.manifest = manifest

        self.received_hello = set()
        self.received_hello_ack = set()

        self.lock = threading.Lock()

    def handle_message(self, message, peer_id):
        if message.message_type == HELLO:
            with self.lock:
                self.received_hello.add(peer_id)

            peer = self.transport.peers[peer_id]

            response = Packet(
                message_type=HELLO_ACK,
                session_id=self.session_id,
                sender_peer_id=self.local_peer_id,
                sequence_number=0,
                ack_number=0,
                payload={}
            )

            self.transport.send_reliable_packet(
                response,
                peer["outgoing_channel"],
                peer["address"],
                peer["incoming_channel"]
            )

        elif message.message_type == HELLO_ACK:
            with self.lock:
                self.received_hello_ack.add(peer_id)

    def start(self):
        # Register every other player.
        for player in self.manifest:
            peer_id = player["peer_id"]

            if peer_id == self.local_peer_id:
                continue

            peer_address = (
                player["host"],
                player["port"]
            )

            self.transport.add_peer(
                peer_id,
                peer_address,
                ack_message_type=HELLO,
                on_message=lambda message, peer_id=peer_id:
                    self.handle_message(message, peer_id)
            )

        # Start receiving and processing network messages.
        self.transport.start_network_loop(
            self.session_id,
            self.local_peer_id
        )

        # Send HELLO to every other player.
        for peer_id, peer in self.transport.peers.items():
            hello = Packet(
                message_type=HELLO,
                session_id=self.session_id,
                sender_peer_id=self.local_peer_id,
                sequence_number=0,
                ack_number=0,
                payload={}
            )

            self.transport.send_reliable_packet(
                hello,
                peer["outgoing_channel"],
                peer["address"],
                peer["incoming_channel"]
            )

        print("HELLO messages sent to all players.")

        # Wait for the other players to complete the handshake.
        deadline = time.monotonic() + T_JOIN_TIMEOUT

        while time.monotonic() < deadline:
            with self.lock:
                ready_players = []

                for peer_id, peer in self.transport.peers.items():
                    hello_received = peer_id in self.received_hello
                    ack_received = peer_id in self.received_hello_ack
                    channel_ready = not peer["outgoing_channel"].pending_messages

                    if hello_received and ack_received and channel_ready:
                        ready_players.append(peer_id)

            if len(ready_players) == len(self.transport.peers):
                break

            time.sleep(0.05)

        # Keep only players who completed the handshake.
        with self.lock:
            ready_players = [
                peer_id
                for peer_id, peer in self.transport.peers.items()
                if peer_id in self.received_hello
                and peer_id in self.received_hello_ack
                and not peer["outgoing_channel"].pending_messages
            ]

        for peer_id in list(self.transport.peers):
            if peer_id not in ready_players:
                del self.transport.peers[peer_id]
                print("Player", peer_id, "did not respond.")

        total_players = len(ready_players) + 1

        print("Players successfully connected:", total_players)

        if total_players < 3:
            print("Not enough players. The game session must be aborted.")
            return False

        print("Peer discovery completed!")
        return True