from networking.udp import UDPTransport
from networking.packet import Packet
from networking.logger import MessageLogger


# Enable verbose mode
logger = MessageLogger(verbose=True)

# Create two UDP sockets
player1 = UDPTransport(logger=logger)
player2 = UDPTransport(logger=logger)

try:
    # Get Player 2's address
    player2_address = player2.get_address()

    # Create a message from Player 1
    packet = Packet(
        message_type=1,
        session_id=b"\x01" * 16,
        sender_peer_id=1,
        sequence_number=1,
        ack_number=0,
        payload={"message": "Hello Player 2!"}
    )

    # Player 1 sends the message
    player1.send_packet(packet, player2_address)

    # Player 2 receives the message
    received_packet, sender_address = player2.receive_packet()

    print("\n========== RESULT ==========")
    print("Received message:", received_packet.payload)
    print("Sender address:", sender_address)
    print("============================")

finally:
    player1.close()
    player2.close()