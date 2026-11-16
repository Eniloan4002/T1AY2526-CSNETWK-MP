
from networking.udp import UDPTransport
from networking.packet import Packet
from networking.reliability import ReliableChannel


# Create two UDP peers
player1 = UDPTransport()
player2 = UDPTransport()

channel1 = ReliableChannel()

session_id = b"\x01" * 16

try:
    # Get Player 2's address
    player2_address = player2.get_address()

    # Player 1 prepares a message
    sequence = channel1.get_next_sequence()

    message = Packet(
        message_type=5,
        session_id=session_id,
        sender_peer_id=1,
        sequence_number=sequence,
        ack_number=0,
        payload={},
    )

    channel1.track_message(sequence, message)

    # Player 1 sends the message
    player1.send_packet(message, player2_address)

    # Player 2 receives the message
    received, player1_address = player2.receive_packet()

    print("\nPlayer 2 received message:", received.message_type)

    # Player 2 sends an ACK
    player2.send_ack(
        session_id,
        2,
        received.sequence_number,
        player1_address,
        received.message_type
    )

    # Player 1 receives the ACK
    ack, _ = player1.receive_packet()

    print("\nPlayer 1 received ACK:", ack.ack_number)

    # Process the ACK
    is_ack = player1.process_ack(ack, channel1)

    print("Is ACK packet:", is_ack)
    print("Pending messages:", channel1.pending_messages)

finally:
    player1.close()
    player2.close()