import copy

from game.game_state import GameState
from game.draft import DraftManager, RESOURCE_QUERY, RESOURCE_OFFER, RESOURCE_BUY


class FakeTransport:
    def __init__(self):
        self.peers = {}
        self.sent_messages = []

    def send_reliable_packet(
        self, packet, outgoing_channel, address, incoming_channel
    ):
        self.sent_messages.append(copy.deepcopy(packet))


players = [
    {
        "peer_id": 1,
        "seat": 1,
        "wonder_board": "Alexandria",
        "wonder_side": "A"
    },
    {
        "peer_id": 2,
        "seat": 2,
        "wonder_board": "Babylon",
        "wonder_side": "A"
    },
    {
        "peer_id": 3,
        "seat": 3,
        "wonder_board": "Rhodes",
        "wonder_side": "A"
    }
]

# Each peer has its own local copy of the game state.
buyer_game = GameState(players)
seller_game = GameState(players)

buyer_transport = FakeTransport()
seller_transport = FakeTransport()

# Set up the buyer's connection to the seller.
buyer_transport.peers[2] = {
    "outgoing_channel": 1,
    "incoming_channel": 2,
    "address": ("127.0.0.1", 5002),
    "on_message": None
}

buyer_transport.peers[3] = {
    "outgoing_channel": 1,
    "incoming_channel": 3,
    "address": ("127.0.0.1", 5003),
    "on_message": None
}

# Set up the seller's connection to the buyer.
seller_transport.peers[1] = {
    "outgoing_channel": 2,
    "incoming_channel": 1,
    "address": ("127.0.0.1", 5001),
    "on_message": None
}

buyer = DraftManager(
    buyer_transport, b"1234567890123456", 1, [1, 2, 3], buyer_game
)

seller = DraftManager(
    seller_transport, b"1234567890123456", 2, [1, 2, 3], seller_game
)

third_transport = FakeTransport()

third_transport.peers[1] = {
    "outgoing_channel": 3,
    "incoming_channel": 1,
    "address": ("127.0.0.1", 5003),
    "on_message": None
}

third_seller = DraftManager(
    third_transport,
    b"1234567890123456",
    3,
    [1, 2, 3],
    seller_game
)

# Give both neighbors WOOD production.
buyer_game.get_player(2).resources["WOOD"] = 2
buyer_game.get_player(3).resources["WOOD"] = 3

seller_game.get_player(2).resources["WOOD"] = 2
seller_game.get_player(3).resources["WOOD"] = 3

print("\nTEST 1: RESOURCE QUERY")

buyer.query_resource(2, "WOOD", 1)

query_packet = buyer_transport.sent_messages[-1]

assert query_packet.message_type == RESOURCE_QUERY

seller.handle_message(query_packet, 1)

print("\nTEST 2: RESOURCE OFFER")

offer_packet = seller_transport.sent_messages[-1]

assert offer_packet.message_type == RESOURCE_OFFER

buyer.handle_message(offer_packet, 2)

assert buyer.resource_offers[(2, "WOOD")]["qty_available"] == 2
assert buyer.resource_offers[(2, "WOOD")]["price_per_unit"] == 2

print("\nTEST 3: RESOURCE BUY")

buyer.buy_resource_from_neighbor(2, "WOOD", 1)

buy_packet = buyer_transport.sent_messages[-1]

assert buy_packet.message_type == RESOURCE_BUY

seller.handle_message(buy_packet, 1)

print("\nTEST 4: VERIFY COIN BALANCES")

buyer_coins = buyer_game.get_player(1).coins
seller_coins = seller_game.get_player(2).coins
seller_wood = seller_game.get_player(2).resources["WOOD"]

print("Buyer coins:", buyer_coins)
print("Seller coins:", seller_coins)
print("Seller WOOD:", seller_wood)

assert buyer_coins == 1
assert seller_coins == 5
assert seller_wood == 2

print("\nTEST 5: QUERY BOTH NEIGHBORS")

eligible_neighbors = buyer.query_available_neighbors(
    "WOOD", 1
)

assert eligible_neighbors == [3, 2]

# Player 2 responds.
seller.handle_message(
    buyer_transport.sent_messages[-2],
    1
)

# Player 3 responds.
third_seller.handle_message(
    buyer_transport.sent_messages[-1],
    1
)

# Deliver both offers to the buyer.
buyer.handle_message(
    seller_transport.sent_messages[-1],
    2
)

buyer.handle_message(
    third_transport.sent_messages[-1],
    3
)

offers = buyer.get_resource_offers("WOOD")

print("Available offers:", offers)

assert len(offers) == 2
assert offers[0]["seller_id"] == 2
assert offers[1]["seller_id"] == 3

print("SUCCESS! Both neighbors supplied valid offers.")


print("\nTEST 6: SPLIT RESOURCE PURCHASE")

# Create fresh game states for this test.
split_buyer_game = GameState(players)
split_seller_game = GameState(players)

# Player 1 has East Trading Post.
# This gives a discount when buying raw materials
# from the right neighbor, Player 2.
split_seller_game.get_player(1).built_cards.append({
    "name": "East Trading Post"
})

# Give the buyer enough coins for the purchase.
split_buyer_game.get_player(1).coins = 10

# Give both neighbors WOOD production.
split_buyer_game.get_player(2).resources["WOOD"] = 2
split_buyer_game.get_player(3).resources["WOOD"] = 3

split_seller_game.get_player(2).resources["WOOD"] = 2
split_seller_game.get_player(3).resources["WOOD"] = 3

# Create fresh transports.
split_buyer_transport = FakeTransport()
split_seller_transport = FakeTransport()
split_third_transport = FakeTransport()

# Connect Player 1 to both neighbors.
split_buyer_transport.peers[2] = {
    "outgoing_channel": 1,
    "incoming_channel": 2,
    "address": ("127.0.0.1", 5002),
    "on_message": None
}

split_buyer_transport.peers[3] = {
    "outgoing_channel": 1,
    "incoming_channel": 3,
    "address": ("127.0.0.1", 5003),
    "on_message": None
}

# Connect Player 2 to Player 1.
split_seller_transport.peers[1] = {
    "outgoing_channel": 2,
    "incoming_channel": 1,
    "address": ("127.0.0.1", 5001),
    "on_message": None
}

# Connect Player 3 to Player 1.
split_third_transport.peers[1] = {
    "outgoing_channel": 3,
    "incoming_channel": 1,
    "address": ("127.0.0.1", 5001),
    "on_message": None
}

# Create the three DraftManagers.
split_buyer = DraftManager(
    split_buyer_transport,
    b"1234567890123456",
    1,
    [1, 2, 3],
    split_buyer_game
)

split_seller = DraftManager(
    split_seller_transport,
    b"1234567890123456",
    2,
    [1, 2, 3],
    split_seller_game
)

split_third_seller = DraftManager(
    split_third_transport,
    b"1234567890123456",
    3,
    [1, 2, 3],
    split_seller_game
)

# Query both neighbors for 4 WOOD.
eligible = split_buyer.query_available_neighbors("WOOD", 4)

assert eligible == [3, 2]

# Deliver Player 3's query to Player 3.
split_third_seller.handle_message(
    split_buyer_transport.sent_messages[-2],
    1
)

# Deliver Player 2's query to Player 2.
split_seller.handle_message(
    split_buyer_transport.sent_messages[-1],
    1
)

# Deliver both offers to the buyer.
split_buyer.handle_message(
    split_seller_transport.sent_messages[-1],
    2
)

split_buyer.handle_message(
    split_third_transport.sent_messages[-1],
    3
)

# Check the offers.
print("Available offers:", split_buyer.get_resource_offers("WOOD"))

# TEST 7: INSUFFICIENT RESOURCE QUANTITY

print("\nTEST 7: INSUFFICIENT RESOURCES")

buyer_coins_before = split_buyer_game.get_player(1).coins
seller_2_coins_before = split_seller_game.get_player(2).coins
seller_3_coins_before = split_seller_game.get_player(3).coins

messages_before = len(split_buyer_transport.sent_messages)

try:
    split_buyer.buy_resource_from_neighbors("WOOD", 6)
    assert False, "Purchase should have been rejected."

except ValueError:
    print("SUCCESS! Purchase rejected due to insufficient resources.")

assert len(split_buyer_transport.sent_messages) == messages_before

assert split_buyer_game.get_player(1).coins == buyer_coins_before
assert split_seller_game.get_player(2).coins == seller_2_coins_before
assert split_seller_game.get_player(3).coins == seller_3_coins_before

print("SUCCESS! No purchase packets were sent and no coins changed.")

# TEST 8: INSUFFICIENT BUYER COINS

print("\nTEST 8: INSUFFICIENT BUYER COINS")

# Give Player 1 only 5 coins.
split_buyer_game.get_player(1).coins = 5

buyer_coins_before = split_buyer_game.get_player(1).coins
seller_2_coins_before = split_seller_game.get_player(2).coins
seller_3_coins_before = split_seller_game.get_player(3).coins

messages_before = len(split_buyer_transport.sent_messages)

try:
    split_buyer.buy_resource_from_neighbors("WOOD", 4)
    assert False, "Purchase should have been rejected."

except ValueError:
    print("SUCCESS! Purchase rejected due to insufficient coins.")

assert len(split_buyer_transport.sent_messages) == messages_before

assert split_buyer_game.get_player(1).coins == buyer_coins_before
assert split_seller_game.get_player(2).coins == seller_2_coins_before
assert split_seller_game.get_player(3).coins == seller_3_coins_before

print("SUCCESS! No purchase packets were sent and no coins changed.")

# Restore the buyer's coins for the original successful purchase test.
split_buyer_game.get_player(1).coins = 10

# Buy 4 WOOD, splitting the purchase between both neighbors.
total_cost = split_buyer.buy_resource_from_neighbors("WOOD", 4)

# The buyer should purchase 2 WOOD from each neighbor.
player_2_buy = split_buyer_transport.sent_messages[-2]
player_3_buy = split_buyer_transport.sent_messages[-1]

assert player_2_buy.message_type == RESOURCE_BUY
assert player_3_buy.message_type == RESOURCE_BUY

assert player_2_buy.payload["qty"] == 2
assert player_3_buy.payload["qty"] == 2
assert player_2_buy.payload["coins"] == 2
assert player_3_buy.payload["coins"] == 4

# Check the purchase packets.
print("\nDEBUG: PLAYER 2")
print("Buy packet:", player_2_buy.payload)
print("Stored offers:", split_seller.sent_resource_offers)

print("\nDEBUG: PLAYER 3")
print("Buy packet:", player_3_buy.payload)
print("Stored offers:", split_third_seller.sent_resource_offers)

# Deliver the purchases to the sellers.
split_seller.handle_message(player_2_buy, 1)
split_third_seller.handle_message(player_3_buy, 1)

# Verify coin balances.
buyer_coins = split_buyer_game.get_player(1).coins
seller_2_coins = split_seller_game.get_player(2).coins
seller_3_coins = split_seller_game.get_player(3).coins

print("Total cost:", total_cost)
print("Buyer coins:", buyer_coins)
print("Player 2 coins:", seller_2_coins)
print("Player 3 coins:", seller_3_coins)

assert total_cost == 6
assert buyer_coins == 4
assert seller_2_coins == 5
assert seller_3_coins == 7

# Resource production should not be consumed.
assert split_seller_game.get_player(2).resources["WOOD"] == 2
assert split_seller_game.get_player(3).resources["WOOD"] == 3

print("SUCCESS! Buyer successfully purchased resources from both neighbors.")


# TEST 9: FALLBACK TO THE OTHER NEIGHBOR
print("\nTEST 9: ALTERNATE NEIGHBOR FALLBACK")

# Clear previous offers and queries.
split_buyer.resource_offers.clear()
split_buyer.resource_queries.clear()

# Save the original waiting method.
original_wait = split_buyer.wait_for_resource_offer

# Simulate Player 3 not responding and Player 2 responding.
def simulate_resource_response(seller_id, resource):
    if seller_id == 3:
        print("SIMULATION: Player 3 does not respond.")
        return None

    if seller_id == 2:
        print("SIMULATION: Player 2 sends a RESOURCE_OFFER.")

        offer = {
            "resource": resource,
            "qty_available": 2,
            "price_per_unit": 2
        }

        split_buyer.resource_offers[(seller_id, resource)] = offer

        return offer

    return None


split_buyer.wait_for_resource_offer = simulate_resource_response

messages_before = len(split_buyer_transport.sent_messages)

# Player 1 needs 2 WOOD.
success = split_buyer.query_resource_with_fallback("WOOD", 2)

# Restore the original waiting method.
split_buyer.wait_for_resource_offer = original_wait

# Check that the fallback succeeded.
assert success is True

# Check that two RESOURCE_QUERY messages were sent.
new_messages = split_buyer_transport.sent_messages[messages_before:]

assert len(new_messages) == 2
assert all(
    message.message_type == RESOURCE_QUERY
    for message in new_messages
)

# Check that Player 3 was queried first, followed by Player 2.
assert new_messages[0].payload["resource"] == "WOOD"
assert new_messages[1].payload["resource"] == "WOOD"

# Check that Player 2's offer was stored.
assert split_buyer.resource_offers[(2, "WOOD")]["qty_available"] == 2

print("SUCCESS! Player 1 tried Player 3 first.")
print("SUCCESS! Player 1 tried Player 2 after Player 3 timed out.")
print("SUCCESS! Player 1 received enough WOOD from Player 2.")


# TEST 10: PURCHASE AFTER FALLBACK
print("\nTEST 10: PURCHASE AFTER FALLBACK")

# Simulate the offer that Player 2 sent to Player 1.
split_seller.sent_resource_offers[(1, "WOOD")] = {
    "resource": "WOOD",
    "qty_available": 2,
    "price_per_unit": 2
}

buyer_coins_before = split_buyer_game.get_player(1).coins
seller_coins_before = split_seller_game.get_player(2).coins

total_cost = split_buyer.buy_resource_from_neighbors("WOOD", 2)

buy_packet = split_buyer_transport.sent_messages[-1]

assert buy_packet.message_type == RESOURCE_BUY
assert buy_packet.payload["qty"] == 2
assert buy_packet.payload["coins"] == 4

# Deliver the purchase packet to Player 2.
split_seller.handle_message(buy_packet, 1)

# Verify both players' coin balances.
assert split_buyer_game.get_player(1).coins == buyer_coins_before - 4
assert split_seller_game.get_player(2).coins == seller_coins_before + 4

print("SUCCESS! Player 1 purchased WOOD after fallback.")
print("Total cost:", total_cost)
print("Buyer coins:", split_buyer_game.get_player(1).coins)
print("Seller coins:", split_seller_game.get_player(2).coins)


print("\nSUCCESS! Resource trading test passed.")
