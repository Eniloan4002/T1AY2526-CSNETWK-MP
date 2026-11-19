from networking.udp import UDPTransport
from networking.packet import Packet, FLAG_ACK
from networking.reliability import ReliableChannel


player1 = UDPTransport()
player2 = UDPTransport()

# Separate channels for each direction
p1_to_p2 = ReliableChannel()
p2_to_p1 = ReliableChannel()

p1_from_p2 = ReliableChannel()
p2_from_p1 = ReliableChannel()

session_id = b"\x01" * 16

try:
    player1_address = player1.get_address()
    player2_address = player2.get_address()

    # Player 1 sends its first message
    seq1 = p1_to_p2.get_next_sequence()

    message1 = Packet(
        message_type=5,
        session_id=session_id,
        sender_peer_id=1,
        sequence_number=seq1,
        ack_number=0,
        payload={"message": "Hello Player 2!"}
    )

    p1_to_p2.track_message(seq1, message1)
    player1.send_packet(message1, player2_address)

    # Player 2 receives the message
    received1, _ = player2.receive_packet()

    # Player 2 replies while acknowledging Player 1's message
    seq2 = p2_to_p1.get_next_sequence()

    message2 = Packet(
        message_type=5,
        session_id=session_id,
        sender_peer_id=2,
        sequence_number=seq2,
        ack_number=received1.sequence_number,
        payload={"message": "Hello Player 1!"},
        flags=FLAG_ACK
    )

    p2_to_p1.track_message(seq2, message2)
    player2.send_packet(message2, player1_address)

    # Player 1 receives and processes the piggybacked ACK
    received2, _ = player1.receive_packet()

    delivered = player1.process_received_packet(
        received2,
        p1_to_p2,
        p1_from_p2,
        1,
        player2_address
    )

    print("\nPlayer 1 received:", delivered[0].payload)
    print("Piggybacked ACK number:", received2.ack_number)
    print("Player 1 pending messages:", p1_to_p2.pending_messages)

finally:
    player1.close()
    player2.close()