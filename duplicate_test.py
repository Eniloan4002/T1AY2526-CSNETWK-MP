
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

    # Prepare the original message
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

    # Send and receive the original message
    player1.send_packet(message, player2_address)
    received, player1_address = player2.receive_packet()

    first_delivery = player2.process_received_packet(
        received,
        ReliableChannel(),
        incoming,
        2,
        player1_address
    )

    print("First delivery:", len(first_delivery))
    
    # Wait for timeout and retransmit
    time.sleep(outgoing.rto + 0.1)
    player1.retransmit_messages(outgoing, player2_address)

    # Receive the retransmitted message
    resent, player1_address = player2.receive_packet()

    second_delivery = player2.process_received_packet(
        resent,
        ReliableChannel(),
        incoming,
        2,
        player1_address
    )

    print("Second delivery:", len(second_delivery))
    print("ACK number:", incoming.get_ack_number())

    # Receive both ACKs sent by Player 2
    first_ack, _ = player1.receive_packet()
    second_ack, _ = player1.receive_packet()

    print("First ACK:", first_ack.ack_number)
    print("Second ACK:", second_ack.ack_number)

finally:
    player1.close()
    player2.close()