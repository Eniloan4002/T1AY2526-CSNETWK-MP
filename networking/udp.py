import socket
import copy
import threading
import time

from networking.packet import Packet, MAX_DATAGRAM_SIZE, FLAG_ACK, FLAG_RETRANSMIT
from networking.logger import MessageLogger
from networking.reliability import ReliableChannel


class UDPTransport:
    def __init__(self, host="127.0.0.1", port=0, logger=None):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((host, port))
        self.socket.settimeout(5)

        self.logger = logger
        self.running = False
        self.receiver_thread = None
        self.stop_event = threading.Event()

        self.peers = {}
        self.local_peer_id = None
        self.session_id = None

    def get_address(self):
        return self.socket.getsockname()

    def send_packet(self, packet, address):
        data = packet.encode()

        self.socket.sendto(data, address)

        if self.logger:
            self.logger.log_sent(
                packet.message_type,
                packet.sender_peer_id,
                packet.payload
            )

    
    def send_packet_with_ack(self, packet, address, incoming_channel):
        if incoming_channel.ack_pending:
            packet.flags |= FLAG_ACK
            packet.ack_number = incoming_channel.get_ack_number()

            self.send_packet(packet, address)

            incoming_channel.ack_pending = False
            incoming_channel.ack_deadline = None
        else:
            self.send_packet(packet, address)


    
    def send_reliable_packet(self, packet, outgoing_channel, address,
                            incoming_channel=None):

        # Assign the next sequence number
        sequence = outgoing_channel.get_next_sequence()
        packet.sequence_number = sequence

        # Check if this method attaches a pending ACK
        ack_included = False

        if incoming_channel and incoming_channel.ack_pending:
            packet.flags |= FLAG_ACK
            packet.ack_number = incoming_channel.get_ack_number()
            ack_included = True

        # Track the message until it is acknowledged
        outgoing_channel.track_message(sequence, packet)

        # Send the packet
        self.send_packet(packet, address)

        # Clear the pending ACK only if this method attached it
        if ack_included:
            incoming_channel.ack_pending = False
            incoming_channel.ack_deadline = None

        return sequence



    
    def retransmit_messages(self, channel, address):
        messages_to_resend = channel.check_timeouts()

        for sequence, packet in messages_to_resend:
            retransmitted_packet = copy.copy(packet)
            retransmitted_packet.flags |= FLAG_RETRANSMIT

            self.send_packet(retransmitted_packet, address)


    def send_pending_ack(self, channel, session_id, local_peer_id,
                        address, message_type):
        if channel.is_ack_due():
            self.send_ack(
                session_id,
                local_peer_id,
                channel.get_ack_number(),
                address,
                message_type
            )

            channel.ack_pending = False
            channel.ack_deadline = None


    def send_ack(self, session_id, sender_peer_id, ack_number, address, message_type):
        packet = Packet(
            message_type=message_type,
            session_id=session_id,
            sender_peer_id=sender_peer_id,
            sequence_number=0,
            ack_number=ack_number,
            payload=None,
            flags=FLAG_ACK
        )

        self.send_packet(packet, address)

    
    def process_ack(self, packet, channel):
        if packet.flags & FLAG_ACK:
            channel.acknowledge(packet.ack_number)

            # Only treat an empty ACK packet as ACK-only
            return packet.payload is None

        return False


    def process_received_packet(self, packet, outgoing_channel, incoming_channel, local_peer_id, address):

        # Process the acknowledgment information first
        is_ack = self.process_ack(packet, outgoing_channel)

        # ACK-only packets do not need another ACK
        if is_ack:
            return []

        # Process the message in the correct sequence order
        delivered_messages = incoming_channel.receive(
            packet.sequence_number,
            packet
        )

        # Schedule an ACK to be sent after 50 milliseconds
        incoming_channel.schedule_ack()
        
        return delivered_messages


    def receive_packet(self):
        data, address = self.socket.recvfrom(MAX_DATAGRAM_SIZE)

        packet = Packet.decode(data)

        if self.logger:
            self.logger.log_received(
                packet.message_type,
                packet.sender_peer_id,
                packet.payload
            )

        return packet, address
    
    def add_peer(self, peer_id, peer_address, ack_message_type=0x05,
                on_message=None):

        if peer_id in self.peers:
            raise ValueError("Peer is already registered.")

        self.peers[peer_id] = {
            "address": peer_address,
            "outgoing_channel": ReliableChannel(),
            "incoming_channel": ReliableChannel(),
            "ack_message_type": ack_message_type,
            "on_message": on_message
        }


    def start_network_loop(self, session_id, local_peer_id):

        if self.running:
            print("The network loop is already running.")
            return

        self.session_id = session_id
        self.local_peer_id = local_peer_id

        self.running = True
        self.stop_event.clear()

        self.socket.settimeout(0.05)

        self.receiver_thread = threading.Thread(
            target=self._network_loop,
            daemon=True
        )

        self.receiver_thread.start()


    def _network_loop(self):

        while not self.stop_event.is_set():

            # Receive incoming packets
            try:
                packet, address = self.receive_packet()

                peer = self.peers.get(packet.sender_peer_id)

                # Check whether the packet belongs to a registered peer
                if (peer and
                        address == peer["address"] and
                        packet.session_id == self.session_id):

                    delivered_messages = self.process_received_packet(
                        packet,
                        peer["outgoing_channel"],
                        peer["incoming_channel"],
                        self.local_peer_id,
                        address
                    )

                    # Pass delivered messages to the game
                    for message in delivered_messages:
                        if peer["on_message"]:
                            peer["on_message"](message)
                        else:
                            print("Message received:", message.payload)

                else:
                    print(
                        "REJECTED PACKET:",
                        "| Local Player:", self.local_peer_id,
                        "| Sender:", packet.sender_peer_id,
                        "| Received Address:", address,
                        "| Expected Address:",
                        peer["address"] if peer else "Unknown peer",
                        "| Received Session:", packet.session_id,
                        "| Expected Session:", self.session_id
                    )

            except socket.timeout:
                pass

            except (ValueError, OSError) as error:
                print("Communication error:", error)

            # Check every peer for pending ACKs and retransmissions
            for peer in self.peers.values():

                self.send_pending_ack(
                    peer["incoming_channel"],
                    self.session_id,
                    self.local_peer_id,
                    peer["address"],
                    peer["ack_message_type"]
                )

                self.retransmit_messages(
                    peer["outgoing_channel"],
                    peer["address"]
                )


    def stop_network_loop(self):

        if not self.running:
            return

        self.stop_event.set()

        if self.receiver_thread:
            self.receiver_thread.join(timeout=1)

        self.running = False
        self.receiver_thread = None

        print("Network loop stopped.")




    def close(self):
        self.stop_network_loop()
        self.socket.close()