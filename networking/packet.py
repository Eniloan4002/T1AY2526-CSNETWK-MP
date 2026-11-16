
import json
import struct


PROTOCOL_VERSION = 1
HEADER_FORMAT = "!BBBB16sHHII"
HEADER_SIZE = 32
MAX_DATAGRAM_SIZE = 1200

FLAG_ACK = 0b00000001
FLAG_RETRANSMIT = 0b00000010


class Packet:
    def __init__(self, message_type, session_id, sender_peer_id,
                 sequence_number, ack_number, payload=None, flags=0):

        self.message_type = message_type
        self.session_id = session_id
        self.sender_peer_id = sender_peer_id
        self.sequence_number = sequence_number
        self.ack_number = ack_number
        self.payload = payload
        self.flags = flags

    def encode(self):
        if len(self.session_id) != 16:
            raise ValueError("Session ID must be 16 bytes.")

        if self.flags & 0b11111100:
            raise ValueError("Reserved flag bits must be zero.")

        if self.payload is None:
            payload_data = b""
        else:
            payload_data = json.dumps(self.payload).encode("utf-8")

        header = struct.pack(
            HEADER_FORMAT,
            PROTOCOL_VERSION,
            self.message_type,
            self.flags,
            0,
            self.session_id,
            self.sender_peer_id,
            len(payload_data),
            self.sequence_number,
            self.ack_number
        )

        packet_data = header + payload_data

        if len(packet_data) > MAX_DATAGRAM_SIZE:
            raise ValueError("Packet exceeds 1200 bytes.")

        return packet_data

    @staticmethod
    def decode(packet_data):
        if len(packet_data) < HEADER_SIZE:
            raise ValueError("Packet header is incomplete.")

        if len(packet_data) > MAX_DATAGRAM_SIZE:
            raise ValueError("Packet exceeds 1200 bytes.")

        header = struct.unpack(
            HEADER_FORMAT,
            packet_data[:HEADER_SIZE]
        )

        version = header[0]
        message_type = header[1]
        flags = header[2]
        session_id = header[4]
        sender_peer_id = header[5]
        payload_length = header[6]
        sequence_number = header[7]
        ack_number = header[8]

        if version != PROTOCOL_VERSION:
            raise ValueError("Unsupported protocol version.")

        payload_data = packet_data[HEADER_SIZE:]

        if len(payload_data) != payload_length:
            raise ValueError("Incorrect payload length.")

        if payload_data:
            payload = json.loads(payload_data.decode("utf-8"))
        else:
            payload = None

        return Packet(
            message_type,
            session_id,
            sender_peer_id,
            sequence_number,
            ack_number,
            payload,
            flags
        )