import time

from networking.udp import UDPTransport
from networking.packet import Packet
from networking.reliability import ReliableChannel


player1 = UDPTransport()
player2 = UDPTransport()

outgoing = ReliableChannel()
incoming = ReliableChannel()

session_id = b"\x01" * 16

try:
    player2_address = player2.get_address()

    # Player 1 sends a message
    sequence = outgoing.get_next_sequence()

    message = Packet(
        message_type=5,
        session_id=session_id,
        sender_peer_id=1,
        sequence_number=sequence,
        ack_number=0,
        payload={"message": "Hello Player 2!"}
    )

    outgoing.track_message(sequence, message)
    player1.send_packet(message, player2_address)

    # Player 2 receives and processes the message
    received, player1_address = player2.receive_packet()

    player2.process_received_packet(
        received,
        ReliableChannel(),
        incoming,
        2,
        player1_address
    )

    print("ACK pending:", incoming.ack_pending)
    print("ACK due immediately:", incoming.is_ack_due())

    # Wait until the 50 ms deadline passes
    time.sleep(0.06)

    print("ACK due after 60 ms:", incoming.is_ack_due())

    # Player 2 sends the delayed ACK
    player2.send_pending_ack(
        incoming,
        session_id,
        2,
        player1_address,
        received.message_type
    )

    # Player 1 receives the ACK
    ack, _ = player1.receive_packet()

    print("ACK received:", ack.ack_number)
    print("ACK still pending:", incoming.ack_pending)

finally:
    player1.close()
    player2.close()