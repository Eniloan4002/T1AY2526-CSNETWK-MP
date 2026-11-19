import time

from game.draft import DraftManager, T_RESOURCE_TIMEOUT


class FakeTransport:
    def __init__(self):
        self.peers = {
            2: {
                "outgoing_channel": 1,
                "address": ("127.0.0.1", 5002),
                "incoming_channel": 2,
                "on_message": None
            }
        }

        self.sent_messages = []

    def send_reliable_packet(
        self, packet, outgoing_channel, address, incoming_channel
    ):
        self.sent_messages.append(packet)


manager = DraftManager(
    FakeTransport(),
    "test_session",
    1,
    [2]
)

# Register a query as if Player 1 had requested WOOD from Player 2.
manager.resource_queries[(2, "WOOD")] = 2

# TEST 1: No offer arrives, so the query should be retried.
print("\nTEST 1: RESOURCE QUERY RETRY")

start = time.monotonic()

offer = manager.wait_for_resource_offer(2, "WOOD")

assert len(manager.transport.sent_messages) == 1
assert manager.transport.sent_messages[0].message_type == 0x0E

print("SUCCESS! One RESOURCE_QUERY retry was sent.")

elapsed = time.monotonic() - start

assert offer is None
assert elapsed >= T_RESOURCE_TIMEOUT * 2
assert elapsed < T_RESOURCE_TIMEOUT * 2 + 2

print("SUCCESS! Query timed out and was retried once.")
print("Elapsed time:", round(elapsed, 2), "seconds")

# TEST 2: RESOURCE OFFER ARRIVES
print("\nTEST 2: RESOURCE OFFER RECEIVED")

manager.resource_offers[(2, "WOOD")] = {
    "resource": "WOOD",
    "qty_available": 2,
    "price_per_unit": 2
}

start = time.monotonic()

offer = manager.wait_for_resource_offer(2, "WOOD")

elapsed = time.monotonic() - start

assert offer is not None
assert offer["resource"] == "WOOD"
assert offer["qty_available"] == 2
assert offer["price_per_unit"] == 2
assert elapsed < T_RESOURCE_TIMEOUT

print("SUCCESS! Resource offer was received.")
print("Elapsed time:", round(elapsed, 2), "seconds")