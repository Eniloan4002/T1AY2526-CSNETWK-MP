import time


MAX_UNACKNOWLEDGED = 4

RTO_INIT = 0.2       # 200 milliseconds
RTO_MAX = 3.2        # 3.2 seconds
RETRY_MAX = 6
T_ACK_DELAY = 0.05  # 50 milliseconds


class ReliableChannel:
    def __init__(self):
        self.next_sequence = 1
        self.pending_messages = {}

        self.expected_sequence = 1
        self.received_buffer = {}

        # Retransmission settings
        self.rto = RTO_INIT
        self.timeout_count = 0
        self.failed = False
        self.ack_pending = False
        self.ack_deadline = None

    def get_next_sequence(self):
        if self.failed:
            raise RuntimeError("This channel has failed.")

        if len(self.pending_messages) >= MAX_UNACKNOWLEDGED:
            raise RuntimeError("Waiting for ACKs before sending more messages.")

        sequence = self.next_sequence
        self.next_sequence += 1

        return sequence

    def track_message(self, sequence_number, message, current_time=None):
        if self.failed:
            raise RuntimeError("This channel has failed.")

        if sequence_number in self.pending_messages:
            raise ValueError("Message is already being tracked.")

        if len(self.pending_messages) >= MAX_UNACKNOWLEDGED:
            raise RuntimeError("Maximum of 4 unacknowledged messages reached.")

        self.pending_messages[sequence_number] = {
            "message": message,
            "sent_at": time.monotonic() if current_time is None else current_time,
            "retries": 0
        }

    def acknowledge(self, ack_number):
        acknowledged = False

        for sequence in list(self.pending_messages):
            if sequence <= ack_number:
                del self.pending_messages[sequence]
                acknowledged = True

        if acknowledged:
            self.rto = RTO_INIT
            self.timeout_count = 0

    
    def check_timeouts(self, current_time=None):
        if self.failed:
            return []

        if current_time is None:
            current_time = time.monotonic()

        messages_to_resend = []

        for sequence, details in self.pending_messages.items():
            elapsed = current_time - details["sent_at"]

            if elapsed >= self.rto:
                messages_to_resend.append(
                    (sequence, details["message"])
                )

        if messages_to_resend:
            self.timeout_count += 1

            if self.timeout_count >= RETRY_MAX:
                self.failed = True
                print("Channel failed after 6 consecutive timeouts.")
                return []

            for sequence, message in messages_to_resend:
                self.pending_messages[sequence]["retries"] += 1
                self.pending_messages[sequence]["sent_at"] = current_time

            self.rto = min(self.rto * 2, RTO_MAX)

        return messages_to_resend


    def receive(self, sequence_number, message):
        if sequence_number < self.expected_sequence:
            return []

        if sequence_number not in self.received_buffer:
            self.received_buffer[sequence_number] = message

        delivered_messages = []

        while self.expected_sequence in self.received_buffer:
            delivered_messages.append(
                self.received_buffer.pop(self.expected_sequence)
            )

            self.expected_sequence += 1

        return delivered_messages

    def get_ack_number(self):
        return self.expected_sequence - 1

    
    
    def schedule_ack(self, current_time=None):
        if self.ack_pending:
            return

        if current_time is None:
            current_time = time.monotonic()

        self.ack_pending = True
        self.ack_deadline = current_time + T_ACK_DELAY



    def is_ack_due(self, current_time=None):
        if not self.ack_pending:
            return False

        if current_time is None:
            current_time = time.monotonic()

        return current_time >= self.ack_deadline
