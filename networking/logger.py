
class MessageLogger:
    def __init__(self, verbose=False):
        self.verbose = verbose

    def log_sent(self, message_type, peer_id, payload):
        if self.verbose:
            print("\n========== MESSAGE SENT ==========")
            print("Type:", message_type)
            print("Peer:", peer_id)
            print("Payload:", payload)
            print("==================================")

    def log_received(self, message_type, peer_id, payload):
        if self.verbose:
            print("\n======== MESSAGE RECEIVED ========")
            print("Type:", message_type)
            print("Peer:", peer_id)
            print("Payload:", payload)
            print("==================================")