
import time
import threading

from networking.packet import Packet
from networking.udp import UDPTransport


# Create three players
players = {
    1: UDPTransport(),
    2: UDPTransport(),
    3: UDPTransport()
}

session_id = b"1234567890123456"

# Track which players received their messages
received_events = {
    1: threading.Event(),
    2: threading.Event(),
    3: threading.Event()
}


def make_handler(player_id):
    def handle_message(packet):
        print(
            f"\nPlayer {player_id} received:",
            packet.payload
        )
        received_events[player_id].set()

    return handle_message


try:
    # Get each player's UDP address
    addresses = {
        player_id: player.get_address()
        for player_id, player in players.items()
    }

    # Register every other player as a peer
    for player_id, player in players.items():

        for other_id in players:

            if player_id != other_id:
                player.add_peer(
                    other_id,
                    addresses[other_id],
                    0x05,
                    make_handler(player_id)
                )

    # Start one network loop per player
    for player_id, player in players.items():
        player.start_network_loop(
            session_id,
            player_id
        )

    print("All three network loops started.")

    # Send a message from one player to another
    def send_message(sender_id, receiver_id, message_text):

        packet = Packet(
            message_type=0x05,
            session_id=session_id,
            sender_peer_id=sender_id,
            sequence_number=0,
            ack_number=0,
            payload={"message": message_text}
        )

        peer = players[sender_id].peers[receiver_id]

        players[sender_id].send_reliable_packet(
            packet,
            peer["outgoing_channel"],
            peer["address"]
        )

        print(
            f"Player {sender_id} sent a message to Player {receiver_id}."
        )

    # Send messages in a circle
    send_message(1, 2, "Hello, Player 2!")
    send_message(2, 3, "Hello, Player 3!")
    send_message(3, 1, "Hello, Player 1!")

    # Wait for all players to receive their messages
    all_received = all(
        event.wait(timeout=3)
        for event in received_events.values()
    )

    if not all_received:
        print("\nFAILED: Not all players received their messages.")

    else:
        # Wait for all messages to be acknowledged
        start_time = time.monotonic()

        while time.monotonic() - start_time < 3:

            all_acknowledged = all(
                not peer["outgoing_channel"].pending_messages
                for player in players.values()
                for peer in player.peers.values()
            )

            if all_acknowledged:
                break

            time.sleep(0.01)

        if all_acknowledged:
            print("\nSUCCESS! Three-player communication works.")
            print("All messages were received and acknowledged.")

        else:
            print("\nFAILED: Some messages are still waiting for ACKs.")

finally:
    for player in players.values():
        player.close()