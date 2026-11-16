
import hashlib
import secrets
import socket
import threading
import time

from networking.packet import Packet


LOBBY_PORT = 7777

MIN_PLAYERS = 3
MAX_PLAYERS = 7

LOBBY_ANNOUNCE_INTERVAL = 2
LOBBY_STALE = 6
LOBBY_QUIET = 3
LOBBY_TIMEOUT = 120

LOBBY_PRESENCE = 0x01
LOBBY_LEAVE = 0x02
LOBBY_START_VOTE = 0x03
LOBBY_START_ACK = 0x04

LOBBY_SENDER_ID = 0xFFFF


def create_lobby_id(room_code):
    return hashlib.sha256(
        room_code.encode("utf-8")
    ).digest()[:16]


def create_lobby_peer_id():
    return secrets.token_bytes(16)


class Lobby:
    def __init__(self, room_code, display_name, game_host, game_port,
                 broadcast_address="255.255.255.255"):

        self.lobby_id = create_lobby_id(room_code)
        self.lobby_peer_id = create_lobby_peer_id()

        self.display_name = display_name
        self.game_host = game_host
        self.game_port = game_port
        self.broadcast_address = broadcast_address

        self.socket = None
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()

        self.roster = {}
        self.roster_lock = threading.Lock()
        self.last_roster_change = time.monotonic()

        self.start_vote = None
        self.start_acks = set()
        self.game_started = False
        self.session_manifest = None

    def start(self):
        if self.running:
            return

        self.socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        self.socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        self.socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_BROADCAST,
            1
        )

        self.socket.bind(("", LOBBY_PORT))
        self.socket.settimeout(0.2)

        # Add ourselves to our own lobby roster
        self.roster[self.lobby_peer_id.hex()] = {
            "display_name": self.display_name,
            "host": self.game_host,
            "port": self.game_port,
            "lobby_address": None,
            "last_seen": time.monotonic()
        }

        self.running = True
        self.stop_event.clear()

        self.thread = threading.Thread(
            target=self._lobby_loop,
            daemon=True
        )

        self.thread.start()

        print("Lobby discovery started.")

    def broadcast_presence(self):
        packet = Packet(
            message_type=LOBBY_PRESENCE,
            session_id=self.lobby_id,
            sender_peer_id=LOBBY_SENDER_ID,
            sequence_number=0,
            ack_number=0,
            payload={
                "lobby_peer_id": self.lobby_peer_id.hex(),
                "display_name": self.display_name,
                "host": self.game_host,
                "port": self.game_port
            }
        )

        self.socket.sendto(
            packet.encode(),
            (self.broadcast_address, LOBBY_PORT)
        )

    
    
    def _receive_presence(self):
        try:
            data, address = self.socket.recvfrom(1200)
            packet = Packet.decode(data)

            if packet.session_id != self.lobby_id:
                return

            if packet.sender_peer_id != LOBBY_SENDER_ID:
                return

            payload = packet.payload

            if not isinstance(payload, dict):
                return

            if packet.message_type == LOBBY_PRESENCE:
                lobby_peer_id = payload.get("lobby_peer_id")

                if not isinstance(lobby_peer_id, str):
                    return

                if len(bytes.fromhex(lobby_peer_id)) != 16:
                    return

                if lobby_peer_id == self.lobby_peer_id.hex():
                    return

                if not isinstance(payload.get("display_name"), str):
                    return

                if not isinstance(payload.get("host"), str):
                    return

                if not isinstance(payload.get("port"), int):
                    return

                with self.roster_lock:
                    is_new_player = lobby_peer_id not in self.roster

                    self.roster[lobby_peer_id] = {
                        "display_name": payload["display_name"],
                        "host": payload["host"],    
                        "port": payload["port"],    
                        "lobby_address": address[0],    
                        "last_seen": time.monotonic()        
                    }

                    if is_new_player:
                        self.last_roster_change = time.monotonic()
                        self.start_vote = None
                        self.start_acks = set()

            elif packet.message_type == LOBBY_LEAVE:
                lobby_peer_id = payload.get("lobby_peer_id")

                if not isinstance(lobby_peer_id, str):
                    return

                if len(bytes.fromhex(lobby_peer_id)) != 16:
                    return

                with self.roster_lock:
                    if lobby_peer_id in self.roster:
                        del self.roster[lobby_peer_id]
                        self.last_roster_change = time.monotonic()
                        self.start_vote = None
                        self.start_acks = set()

            elif packet.message_type == LOBBY_START_VOTE:
                self.handle_start_vote(payload.get("participants"))

            elif packet.message_type == LOBBY_START_ACK:
                self.handle_start_ack(
                    payload.get("participants_hash"),
                    address
                )

        except socket.timeout:
            pass
        except (ValueError, KeyError, TypeError):
            print("Ignored an invalid lobby message.")



    def _remove_stale_players(self):
        current_time = time.monotonic()

        with self.roster_lock:
            stale_players = [
                peer_id
                for peer_id, player in self.roster.items()
                if peer_id != self.lobby_peer_id.hex()
                and current_time - player["last_seen"] > LOBBY_STALE
            ]

            for peer_id in stale_players:
                del self.roster[peer_id]

            if stale_players:
                self.last_roster_change = current_time
                self.start_vote = None
                self.start_acks = set()

    
    def _lobby_loop(self):
        next_announcement = 0
        next_vote = 0

        while not self.stop_event.is_set():
            current_time = time.monotonic()

            # Announce presence every 2 seconds.
            if current_time >= next_announcement:
                try:
                    self.broadcast_presence()
                except OSError as error:
                    print("Lobby broadcast error:", error)

                next_announcement = current_time + LOBBY_ANNOUNCE_INTERVAL

            # Automatically propose starting after the roster
            # has remained unchanged for 3 seconds.
            if not self.game_started:
                roster_size = len(self.get_roster())

                if MIN_PLAYERS <= roster_size <= MAX_PLAYERS:
                    quiet_time = current_time - self.last_roster_change

                    if quiet_time >= LOBBY_QUIET and current_time >= next_vote:
                        try:
                            self.broadcast_start_vote()
                        except OSError as error:
                            print("Start vote error:", error)

                        # Repeat the proposal if agreement is incomplete.
                        next_vote = current_time + LOBBY_QUIET

            self._receive_presence()
            self._remove_stale_players()

    def get_roster(self):
        with self.roster_lock:
            return {
                peer_id: {
                    "display_name": player["display_name"],
                    "host": player["host"],
                    "port": player["port"]
                }
                for peer_id, player in self.roster.items()
            }

    
    def create_participants_hash(self, participants):
        participants_text = "".join(participants)
        return hashlib.sha256(
            participants_text.encode("utf-8")
        ).hexdigest()


    def broadcast_start_vote(self):
        participants = sorted(self.get_roster().keys())

        if len(participants) < MIN_PLAYERS or len(participants) > MAX_PLAYERS:
            return

        # Only reset acknowledgments if the participant list changed.
        if participants != self.start_vote:
            self.start_vote = participants
            self.start_acks = {self.lobby_peer_id.hex()}

        packet = Packet(
            message_type=LOBBY_START_VOTE,
            session_id=self.lobby_id,
            sender_peer_id=LOBBY_SENDER_ID,
            sequence_number=0,
            ack_number=0,
            payload={"participants": participants}
        )

        self.socket.sendto(
            packet.encode(),
            (self.broadcast_address, LOBBY_PORT)
        )


    def broadcast_start_ack(self, participants):
        participants_hash = self.create_participants_hash(participants)

        packet = Packet(
            message_type=LOBBY_START_ACK,
            session_id=self.lobby_id,
            sender_peer_id=LOBBY_SENDER_ID,
            sequence_number=0,
            ack_number=0,
            payload={"participants_hash": participants_hash}
        )

        self.socket.sendto(
            packet.encode(),
            (self.broadcast_address, LOBBY_PORT)
        )


    def handle_start_vote(self, participants):
        if not isinstance(participants, list):
            return

        current_participants = sorted(self.get_roster().keys())

        if participants != current_participants:
            return

        if len(participants) < MIN_PLAYERS or len(participants) > MAX_PLAYERS:
            return

        # Record the same vote locally.
        if participants != self.start_vote:
            self.start_vote = participants
            self.start_acks = {self.lobby_peer_id.hex()}

        # Send our acknowledgment.
        self.broadcast_start_ack(participants)


    def handle_start_ack(self, participants_hash, address):
        if self.start_vote is None:
            return

        expected_hash = self.create_participants_hash(self.start_vote)

        if participants_hash != expected_hash:
            return

        # Identify the player using the IP address recorded
        # when their lobby presence packet was received.
        with self.roster_lock:
            for peer_id, player in self.roster.items():
                if player["lobby_address"] == address[0]:
                    if peer_id in self.start_vote:
                        self.start_acks.add(peer_id)
                    break

        # Check whether every participant has acknowledged.
        if set(self.start_vote).issubset(self.start_acks):
            if not self.game_started:
                self.game_started = True
                print("All players agreed. Lobby closed!")

    def create_session_manifest(self):
        if not self.game_started:
            raise RuntimeError("The lobby has not reached agreement yet.")

        if self.session_manifest is not None:
            return self.session_manifest

        participants = sorted(self.start_vote)
        manifest = []

        with self.roster_lock:
            for peer_id, lobby_peer_id in enumerate(participants, start=1):
                player = self.roster.get(lobby_peer_id)

                if player is None:
                    raise RuntimeError("A participant is missing from the roster.")

                manifest.append({
                    "peer_id": peer_id,
                    "display_name": player["display_name"],
                    "host": player["host"],
                    "port": player["port"]
                })

        self.session_manifest = manifest

        return self.session_manifest

    def get_session_id(self):
        if not self.game_started:
            raise RuntimeError("The lobby has not reached agreement yet.")

        return self.lobby_id

    def get_local_peer_id(self):
        if not self.game_started:
            raise RuntimeError("The lobby has not reached agreement yet.")

        participants = sorted(self.start_vote)

        return participants.index(self.lobby_peer_id.hex()) + 1


    def stop(self):
        if not self.running:
            return

        # Tell other players that we are leaving
        leave_packet = Packet(
            message_type=LOBBY_LEAVE,
            session_id=self.lobby_id,
            sender_peer_id=LOBBY_SENDER_ID,
            sequence_number=0,
            ack_number=0,
            payload={
                "lobby_peer_id": self.lobby_peer_id.hex()
            }
        )

        try:
            self.socket.sendto(
                leave_packet.encode(),
                (self.broadcast_address, LOBBY_PORT)
            )
        except OSError:
            pass

        self.stop_event.set()

        if self.thread:
            self.thread.join(timeout=1)

        self.socket.close()

        self.running = False
        self.thread = None

        print("Lobby discovery stopped.")
