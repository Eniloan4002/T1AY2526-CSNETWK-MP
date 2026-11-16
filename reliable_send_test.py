
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

    # Prepare a message
    message = Packet(
        message_type=5,
        session_id=session_id,
        sender_peer_id=1,
        sequence_number=0,
        ack_number=0,
        payload={"message": "Hello Player 2!"}
    )

    # Send using the new method
    sequence = player1.send_reliable_packet(
        message,
        outgoing,
        player2_address
    )

    print("Assigned sequence:", sequence)
    print("Pending messages:", list(outgoing.pending_messages.keys()))

    # Player 2 receives the message
    received, player1_address = player2.receive_packet()

    delivered = player2.process_received_packet(
        received,
        ReliableChannel(),
        incoming,
        2,
        player1_address
    )

    print("\nPlayer 2 received:", delivered[0].payload)
    print("ACK pending:", incoming.ack_pending)

finally:
    player1.close()
    player2.close()