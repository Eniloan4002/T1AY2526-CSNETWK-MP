
from networking.udp import UDPTransport
from networking.packet import Packet, FLAG_ACK
from networking.reliability import ReliableChannel


player1 = UDPTransport()
player2 = UDPTransport()

p1_to_p2 = ReliableChannel()
p2_to_p1 = ReliableChannel()

p1_from_p2 = ReliableChannel()
p2_from_p1 = ReliableChannel()

session_id = b"\x01" * 16

try:
    player1_address = player1.get_address()
    player2_address = player2.get_address()

    # Player 1 sends a message
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

    # Player 2 receives and processes it
    received1, _ = player2.receive_packet()

    player2.process_received_packet(
        received1,
        p2_to_p1,
        p2_from_p1,
        2,
        player1_address
    )

    print("Player 2 has pending ACK:", p2_from_p1.ack_pending)

    # Player 2 prepares a reply
    seq2 = p2_to_p1.get_next_sequence()

    message2 = Packet(
        message_type=5,
        session_id=session_id,
        sender_peer_id=2,
        sequence_number=seq2,
        ack_number=0,
        payload={"message": "Hello Player 1!"}
    )

    p2_to_p1.track_message(seq2, message2)

    # Send the reply with the pending ACK attached
    player2.send_packet_with_ack(
        message2,
        player1_address,
        p2_from_p1
    )

    # Player 1 receives the reply
    received2, _ = player1.receive_packet()

    print("\nPlayer 1 received:", received2.payload)
    print("ACK flag set:", bool(received2.flags & FLAG_ACK))
    print("Piggybacked ACK number:", received2.ack_number)
    print("Player 2 pending ACK:", p2_from_p1.ack_pending)

    # Player 1 processes the piggybacked ACK
    player1.process_received_packet(
        received2,
        p1_to_p2,
        p1_from_p2,
        1,
        player2_address
    )

    print("Player 1 pending messages:", p1_to_p2.pending_messages)

finally:
    player1.close()
    player2.close()