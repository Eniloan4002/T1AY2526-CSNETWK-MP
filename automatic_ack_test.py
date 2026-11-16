
from networking.udp import UDPTransport
from networking.packet import Packet
from networking.reliability import ReliableChannel


# Create two UDP peers
player1 = UDPTransport()
player2 = UDPTransport()

# Create separate channels for each direction
p1_to_p2 = ReliableChannel()
p2_to_p1 = ReliableChannel()

p1_from_p2 = ReliableChannel()
p2_from_p1 = ReliableChannel()

session_id = b"\x01" * 16

try:
    player2_address = player2.get_address()

    # Player 1 prepares and tracks a message
    sequence = p1_to_p2.get_next_sequence()

    message = Packet(
        message_type=5,
        session_id=session_id,
        sender_peer_id=1,
        sequence_number=sequence,
        ack_number=0,
        payload={"message": "Hello Player 2!"}
    )

    p1_to_p2.track_message(sequence, message)

    # Player 1 sends the message
    player1.send_packet(message, player2_address)

    # Player 2 receives and processes the message
    received, player1_address = player2.receive_packet()

    delivered = player2.process_received_packet(
        received,
        p2_to_p1,
        p2_from_p1,
        2,
        player1_address
    )

    print("\nPlayer 2 delivered:", delivered[0].payload)

    # Player 1 receives the automatically generated ACK
    ack, _ = player1.receive_packet()

    player1.process_received_packet(
        ack,
        p1_to_p2,
        p1_from_p2,
        1,
        player2_address
    )

    print("\nPlayer 1 received ACK:", ack.ack_number)
    print("Pending messages:", p1_to_p2.pending_messages)

finally:
    player1.close()
    player2.close()