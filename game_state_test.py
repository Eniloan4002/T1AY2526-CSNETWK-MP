from game.game_state import GameState


game_players = [
    {
        "peer_id": 1,
        "seat": 0,
        "wonder_board": "Halikarnassus",
        "wonder_side": "B"
    },
    {
        "peer_id": 2,
        "seat": 1,
        "wonder_board": "Olympia",
        "wonder_side": "A"
    },
    {
        "peer_id": 3,
        "seat": 2,
        "wonder_board": "Rhodes",
        "wonder_side": "A"
    }
]

# Olympia Side B first stage discount.
players = [
    {
        "peer_id": "P1",
        "seat": 0,
        "wonder_board": "Olympia",
        "wonder_side": "B"
    },
    {
        "peer_id": "P2",
        "seat": 1,
        "wonder_board": "Giza",
        "wonder_side": "A"
    },
    {
        "peer_id": "P3",
        "seat": 2,
        "wonder_board": "Rhodes",
        "wonder_side": "A"
    }
]

game = GameState(players)

# Before completing the first stage, the price is 2.
assert game.get_resource_price("P1", "P2", "WOOD") == 2

# After completing the first stage, the price becomes 1.
game.get_player("P1").wonder_stages = 1

assert game.get_resource_price("P1", "P2", "WOOD") == 1
assert game.get_resource_price("P1", "P3", "STONE") == 1

print("SUCCESS! Olympia Side B resource discount works.")

game = GameState(game_players)


print("\n========== INITIAL GAME STATE ==========")

for peer_id, player in game.players.items():
    print(
        f"Player {peer_id} | "
        f"Coins: {player.coins} | "
        f"Wonder: {player.wonder_board} | "
        f"Resources: {player.resources}"
    )


print("\n========== DISCARD TEST ==========")

game.discard_card(1)

print("Player 1 coins:", game.players[1].coins)

if game.players[1].coins == 6:
    print("SUCCESS! DISCARD gives 3 coins.")
else:
    print("FAILED! Incorrect discard reward.")


print("\n========== BUILD TEST ==========")

# Give Player 1 enough resources and coins for testing
game.players[1].coins = 20

for resource in game.players[1].resources:
    game.players[1].resources[resource] = 5

print("Player 1 resources:", game.players[1].resources)

print("Can Player 1 build Workshop:",
      game.can_afford_card(1, "Workshop"))

try:
    game.build_card(1, "Workshop")
    print("Player 1 built Workshop.")
    print("Built cards:", [
        card["name"] for card in game.players[1].built_cards
    ])
    print("SUCCESS! BUILD action completed.")

except (ValueError, KeyError) as error:
    print("BUILD TEST:", error)


print("\n========== WONDER STAGE TEST ==========")

# Give Player 2 enough resources and coins for testing
game.players[2].coins = 20

for resource in game.players[2].resources:
    game.players[2].resources[resource] = 5

print("Player 2 resources:", game.players[2].resources)

print("Can Player 2 complete a Wonder stage:",
      game.can_afford_wonder_stage(2))

try:
    result = game.complete_wonder_stage(2)

    if result:
        print("Player 2 completed a Wonder stage.")
        print("Completed stages:", game.players[2].wonder_stages)
        print("Wonder VP:", game.players[2].wonder_vp)
        print("Remaining coins:", game.players[2].coins)
        print("Military shields:", game.players[2].military_shields)
        print("SUCCESS! WONDER_STAGE completed.")
    else:
        print("Player 2 cannot afford the Wonder stage.")

except (ValueError, KeyError, IndexError) as error:
    print("WONDER STAGE TEST:", error)


print("\n========== RESOURCE TRADING TEST ==========")

trade_game = GameState(game_players)

# Player 1 is seated between Player 3 and Player 2.
neighbors = trade_game.get_neighbors(1)

print("Player 1 neighbors:", neighbors)

# Player 1 buys WOOD from Player 2.
price = trade_game.get_resource_price(1, 2, "WOOD")

print("Price of 1 WOOD from Player 2:", price)

# Check the trade plan.
trades = [
    {
        "seller_id": 2,
        "resource": "WOOD",
        "amount": 1
    }
]

trade_plan = trade_game.check_trade_plan(1, trades)

print("Trade plan:", trade_plan)

if trade_plan:
    print("SUCCESS! Trade plan is valid.")
else:
    print("FAILED! Trade plan is invalid.")

# Check coin balances before payment.
buyer_coins_before = trade_game.players[1].coins
seller_coins_before = trade_game.players[2].coins

print("\nBefore trade:")
print("Player 1 coins:", buyer_coins_before)
print("Player 2 coins:", seller_coins_before)

# Execute the purchase.
try:
    paid = trade_game.buy_resource(1, 2, "WOOD")

    print("\nAmount paid:", paid)
    print("Player 1 coins:", trade_game.players[1].coins)
    print("Player 2 coins:", trade_game.players[2].coins)

    if (
        trade_game.players[1].coins == buyer_coins_before - price
        and trade_game.players[2].coins == seller_coins_before + price
    ):
        print("SUCCESS! Resource payment is correct.")
    else:
        print("FAILED! Incorrect coin transfer.")

except ValueError as error:
    print("TRADE TEST:", error)


print("\n========== INVALID TRADE TESTS ==========")

# Create a separate 4-player game for testing.
trade_players = game_players + [
    {
        "peer_id": 4,
        "seat": 3,
        "wonder_board": "Giza",
        "wonder_side": "A"
    }
]

test_game = GameState(trade_players)

# Give Player 1 enough coins for normal trades.
test_game.players[1].coins = 10

# Player 2 produces WOOD.
# Player 3 produces ORE.
# Player 4 produces STONE.
print("\n--- TEST 1: Non-neighbor seller ---")

# Player 3 is not Player 1's immediate neighbor in a 4-player game.
try:
    test_game.get_resource_price(1, 3, "ORE")
    print("FAILED! Non-neighbor was accepted.")
except ValueError:
    print("SUCCESS! Non-neighbor was rejected.")


print("\n--- TEST 2: Seller does not have resource ---")

# Player 2 produces WOOD, not ORE.
unavailable_trade = [
    {
        "seller_id": 2,
        "resource": "ORE",
        "amount": 1
    }
]

result = test_game.check_trade_plan(1, unavailable_trade)

if result is False:
    print("SUCCESS! Trade was rejected.")
else:
    print("FAILED! Unavailable resource was accepted.")


print("\n--- TEST 3: Insufficient coins ---")

test_game.players[1].coins = 1

expensive_trade = [
    {
        "seller_id": 2,
        "resource": "WOOD",
        "amount": 1
    }
]

result = test_game.check_trade_plan(1, expensive_trade)

if result is False:
    print("SUCCESS! Trade was rejected due to insufficient coins.")
else:
    print("FAILED! Trade was accepted.")

test_game.players[1].coins = 10


print("\n========== TRADING DISCOUNT TESTS ==========")

# Player 4 is Player 1's left neighbor.
# Player 2 is Player 1's right neighbor.

# TEST 4: West Trading Post
test_game.players[1].built_cards.append({
    "name": "West Trading Post"
})

west_price = test_game.get_resource_price(1, 4, "STONE")

print("West Trading Post price:", west_price)

if west_price == 1:
    print("SUCCESS! Left-side raw material costs 1 coin.")
else:
    print("FAILED! Incorrect West Trading Post price.")


# TEST 5: East Trading Post
test_game.players[1].built_cards.append({
    "name": "East Trading Post"
})

east_price = test_game.get_resource_price(1, 2, "WOOD")

print("East Trading Post price:", east_price)

if east_price == 1:
    print("SUCCESS! Right-side raw material costs 1 coin.")
else:
    print("FAILED! Incorrect East Trading Post price.")


# TEST 6: Marketplace
test_game.players[1].built_cards.append({
    "name": "Marketplace"
})

marketplace_price = test_game.get_resource_price(1, 2, "GLASS")

print("Marketplace price:", marketplace_price)

if marketplace_price == 1:
    print("SUCCESS! Manufactured goods cost 1 coin.")
else:
    print("FAILED! Incorrect Marketplace price.")


print("\n========== BUILD WITH RESOURCE TRADING TEST ==========")

build_game = GameState(game_players)

# Give Player 1 enough coins.
build_game.players[1].coins = 10

# Player 1 buys 1 WOOD from Player 2.
trades = [
    {
        "seller_id": 2,
        "resource": "WOOD",
        "amount": 1
    }
]

print("Can Player 1 build Stockade with trading:",
      build_game.can_afford_card(
          1,
          "Stockade",
          trades=trades
      ))

print("\nBefore BUILD:")
print("Player 1 coins:", build_game.players[1].coins)
print("Player 2 coins:", build_game.players[2].coins)

try:
    build_game.build_card(
        1,
        "Stockade",
        trades=trades
    )

    print("\nAfter BUILD:")
    print("Player 1 coins:", build_game.players[1].coins)
    print("Player 2 coins:", build_game.players[2].coins)

    print("Player 1 built cards:", [
        card["name"]
        for card in build_game.players[1].built_cards
    ])

    if (
        build_game.players[1].coins == 8
        and build_game.players[2].coins == 5
        and "Stockade" in [
            card["name"] for card in build_game.players[1].built_cards
        ]
    ):
        print("SUCCESS! BUILD with resource trading completed.")
    else:
        print("FAILED! Unexpected game state.")

except (ValueError, KeyError) as error:
    print("FAILED!", error)


print("\n========== WONDER STAGE WITH RESOURCE TRADING TEST ==========")

wonder_game = GameState(game_players)

# Simulate Player 1 producing one WOOD for this test.
wonder_game.players[1].resources["WOOD"] = 1

trades = [
    {
        "seller_id": 1,
        "resource": "WOOD",
        "amount": 1
    }
]

print("Can Player 2 complete Wonder stage with trading:",
      wonder_game.can_afford_wonder_stage(
          2,
          trades=trades
      ))

print("\nBefore WONDER_STAGE:")
print("Player 2 coins:", wonder_game.players[2].coins)
print("Player 1 coins:", wonder_game.players[1].coins)

try:
    wonder_game.complete_wonder_stage(
        2,
        trades=trades
    )

    print("\nAfter WONDER_STAGE:")
    print("Player 2 coins:", wonder_game.players[2].coins)
    print("Player 1 coins:", wonder_game.players[1].coins)
    print("Player 2 completed stages:", wonder_game.players[2].wonder_stages)
    print("Player 2 Wonder VP:", wonder_game.players[2].wonder_vp)

    if (
        wonder_game.players[2].coins == 1
        and wonder_game.players[1].coins == 5
        and wonder_game.players[2].wonder_stages == 1
        and wonder_game.players[2].wonder_vp == 3
    ):
        print("SUCCESS! WONDER_STAGE with resource trading completed.")
    else:
        print("FAILED! Unexpected game state.")

except (ValueError, KeyError) as error:
    print("FAILED!", error)


print("\n========== MULTIPLE RESOURCE PURCHASE TEST ==========")

players = [
    {
        "peer_id": "P1",
        "seat": 0,
        "wonder_board": "Alexandria",
        "wonder_side": "A"
    },
    {
        "peer_id": "P2",
        "seat": 1,
        "wonder_board": "Giza",
        "wonder_side": "A"
    },
    {
        "peer_id": "P3",
        "seat": 2,
        "wonder_board": "Rhodes",
        "wonder_side": "A"
    }
]

game = GameState(players)

buyer = game.get_player("P1")
seller = game.get_player("P2")

# Give the buyer enough coins.
buyer.coins = 10

# P2 produces 1 WOOD from Giza? No, use a card-independent
# resource setup for this isolated purchase test.
seller.resources["WOOD"] = 3

print("Before purchase:")
print("Buyer coins:", buyer.coins)
print("Seller coins:", seller.coins)

amount_paid = game.buy_resource(
    "P1",
    "P2",
    "WOOD",
    qty=3
)

print("\nAfter purchase:")
print("Amount paid:", amount_paid)
print("Buyer coins:", buyer.coins)
print("Seller coins:", seller.coins)

assert amount_paid == 6
assert buyer.coins == 4
assert seller.coins == 9

print("SUCCESS! Multiple resource purchase works.")



print("\n========== INVALID PURCHASE QUANTITY TESTS ==========")

try:
    game.buy_resource("P1", "P2", "WOOD", qty=0)
    assert False, "Zero quantity should be rejected."
except ValueError:
    print("SUCCESS! Zero quantity was rejected.")

try:
    game.buy_resource("P1", "P2", "WOOD", qty=4)
    assert False, "Unavailable quantity should be rejected."
except ValueError:
    print("SUCCESS! Unavailable quantity was rejected.")

try:
    game.buy_resource("P1", "P2", "WOOD", qty=-1)
    assert False, "Negative quantity should be rejected."
except ValueError:
    print("SUCCESS! Negative quantity was rejected.")


print("\n========== RESOURCE OFFER TEST ==========")

offer = game.create_resource_offer(
    "P1",
    "P2",
    "WOOD"
)

print("Offer:", offer)

assert offer["resource"] == "WOOD"
assert offer["qty_available"] == 3
assert offer["price_per_unit"] == 2

print("SUCCESS! Resource offer is correct.")


print("\n========== RESOURCE OFFER DISCOUNT TEST ==========")

# Get the actual players stored in this GameState.
buyer = game.get_player("P1")
seller = game.get_player("P3")

# Give P1 the West Trading Post.
buyer.built_cards.append({"name": "West Trading Post"})

# Give P3 WOOD so it can sell the resource.
seller.resources["WOOD"] = 1

offer = game.create_resource_offer(
    "P1",
    "P3",
    "WOOD"
)

print("Discounted offer:", offer)

assert offer["qty_available"] == 1
assert offer["price_per_unit"] == 1

print("SUCCESS! Seller used the buyer's discount.")