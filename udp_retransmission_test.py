
import time

from networking.udp import UDPTransport
from networking.packet import Packet, FLAG_RETRANSMIT
from networking.reliability import ReliableChannel


player1 = UDPTransport()
player2 = UDPTransport()

channel = ReliableChannel()
session_id = b"\x01" * 16

try:
    player2_address = player2.get_address()

    # Prepare the original message
    sequence = channel.get_next_sequence()

    message = Packet(
        message_type=5,
        session_id=session_id,
        sender_peer_id=1,
        sequence_number=sequence,
        ack_number=0,
        payload={"message": "Hello Player 2!"}
    )

    channel.track_message(sequence, message)

    # Send the original message
    player1.send_packet(message, player2_address)

    original, _ = player2.receive_packet()
    print("Original message received:", original.payload)

    # Wait for the message's timeout
    time.sleep(channel.rto + 0.1)

    # Resend the timed-out message
    player1.retransmit_messages(channel, player2_address)

    # Receive the retransmitted message
    resent, _ = player2.receive_packet()

    print("\nRetransmitted message received:", resent.payload)
    print("Sequence number:", resent.sequence_number)
    print("RETRANSMIT flag set:", bool(resent.flags & FLAG_RETRANSMIT))

finally:
    player1.close()
    player2.close()