
import threading
import time

from networking.udp import UDPTransport
from networking.peer_discovery import PeerDiscovery
from networking.randomness import RandomnessCeremony
from game.deterministic_setup import create_game_setup
from game.ring_confirmation import RingConfirmation
from game.deterministic_setup import DeterministicRandom
from game.deterministic_setup import (
    create_game_setup,
    build_age_one_deck,
    build_age_two_deck,
    build_age_three_deck,
    build_all_age_decks,
    deal_hand
)
from game.draft import create_card_commitment, verify_card_commitment
from game.draft import create_card_reveal, verify_card_reveal
from game.draft import DraftManager


# Create three players, each with its own UDP socket.
transports = [
    UDPTransport(host="127.0.0.1", port=0)
    for _ in range(3)
]

# Get the actual port assigned to each player.
addresses = [
    transport.get_address()
    for transport in transports
]

# All players use the same session ID.
session_id = b"7WONDERS-SESSION"  # Must be exactly 16 bytes.

# Create the same player manifest for everyone.
manifest = [
    {
        "peer_id": i + 1,
        "display_name": f"Player {i + 1}",
        "host": addresses[i][0],
        "port": addresses[i][1]
    }
    for i in range(3)
]

discoveries = [
    PeerDiscovery(transports[i], session_id, i + 1, manifest)
    for i in range(3)
]

results = [False, False, False]

# Start all three handshakes at almost the same time.
threads = []

for i in range(3):
    thread = threading.Thread(
        target=lambda index=i: results.__setitem__(
            index, discoveries[index].start()
        )
    )
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()

# Check whether all players completed peer discovery.
if all(results):
    print("\nAll players are ready for the draft.")

if all(results):
    ceremonies = [
        RandomnessCeremony(
            transports[i],
            session_id,
            i + 1
        )
        for i in range(3)
    ]

    seed_results = [False, False, False]
    seed_threads = []

    for i in range(3):
        thread = threading.Thread(
            target=lambda index=i: seed_results.__setitem__(
                index, ceremonies[index].start()
            )
        )
        seed_threads.append(thread)
        thread.start()

    for thread in seed_threads:
        thread.join()

    print("\n========== SEED TEST RESULTS ==========")

    for i in range(3):
        print(
            f"Player {i + 1}:",
            "SUCCESS" if seed_results[i] else "FAILED"
        )

    
    if all(seed_results):
        seeds = [
            ceremony.shared_seed
            for ceremony in ceremonies
        ]

        if seeds[0] == seeds[1] == seeds[2]:
            print("\nSUCCESS! All players calculated the same seed.")

            print("\n========== RING CONFIRMATION TEST ==========")

            player_ids = [1, 2, 3]

            # Each player independently calculates the game setup.
            setups = [
                create_game_setup(
                    seeds[i],
                    player_ids,
                    both_sides=True
                )
                for i in range(3)
            ]

            confirmations = [
                RingConfirmation(
                    transports[i],
                    session_id,
                    i + 1,
                    setups[i]
                )
                for i in range(3)
            ]

            confirmation_results = [False, False, False]
            confirmation_threads = []

            # All players send their RING_CONFIRM messages.
            for i in range(3):
                thread = threading.Thread(
                    target=lambda index=i: confirmation_results.__setitem__(
                        index, confirmations[index].start()
                    )
                )
                confirmation_threads.append(thread)
                thread.start()

            for thread in confirmation_threads:
                thread.join()

            print("\n========== RING CONFIRMATION RESULTS ==========")

            for i in range(3):
                print(
                    f"Player {i + 1}:",
                    "SUCCESS" if confirmation_results[i] else "FAILED"
                )

            if all(confirmation_results):
                print("\nSUCCESS! All players confirmed the same game setup.")

                print("\n========== NETWORK DRAFT TEST ==========")

                active_players = [1, 2, 3]

                # Create a DraftManager for each player.
                draft_managers = [
                    DraftManager(
                        transports[i],
                        session_id,
                        i + 1,
                        active_players
                    )
                    for i in range(3)
                ]

                # Register the draft message handlers.
                for manager in draft_managers:
                    manager.register_callbacks()

                # Give each player a different action.
                draft_actions = [
                    ("Lumber Yard", "BUILD"),
                    ("Stone Pit", "WONDER_STAGE"),
                    ("Clay Pool", "DISCARD")
                ]

                draft_results = [False, False, False]
                draft_threads = []

                # All players perform their draft turns simultaneously.
                for i in range(3):
                    thread = threading.Thread(
                        target=lambda index=i: draft_results.__setitem__(
                            index,
                            draft_managers[index].run_turn(
                                draft_actions[index][0],
                                draft_actions[index][1]
                            )
                        )
                    )

                    draft_threads.append(thread)
                    thread.start()

                for thread in draft_threads:
                    thread.join()

                print("\n========== DRAFT TEST RESULTS ==========")

                for i in range(3):
                    print(
                        f"Player {i + 1}:",
                        "SUCCESS" if draft_results[i] else "FAILED"
                    )

                if all(draft_results):
                    print("\nSUCCESS! All players completed the commit-reveal exchange.")
                else:
                    print("\nDRAFT TEST FAILED.")

            else:
                print("\nRING CONFIRMATION FAILED.")

        else:
            print("\nERROR! Players calculated different seeds.")
    else:
        print("\nThe randomness ceremony failed.")



print("\n========== TEST RESULTS ==========")

for i in range(3):
    print(
        f"Player {i + 1}:",
        "SUCCESS" if results[i] else "FAILED"
    )

if all(results):
    print("\nSUCCESS! All three players completed peer discovery.")
else:
    print("\nPeer discovery test failed.")


print("\n========== AGE I DECK TEST ==========")

test_seed = bytes.fromhex(
    "ccdd2abe" + "11" * 28
)

for player_count in range(3, 8):
    deck_one = build_age_one_deck(test_seed, player_count)
    deck_two = build_age_one_deck(test_seed, player_count)

    expected_count = player_count * 7

    print("\nPlayers:", player_count)
    print("Expected cards:", expected_count)
    print("Actual cards:", len(deck_one))
    print("Deck:", deck_one)

    if deck_one == deck_two and len(deck_one) == expected_count:
        print("SUCCESS! Age I deck is correct and deterministic.")
    else:
        print("FAILED! Age I deck is incorrect.")


print("\n========== AGE II DECK TEST ==========")

test_seed = bytes.fromhex(
    "ccdd2abe" + "11" * 28
)

for player_count in range(3, 8):
    deck_one = build_age_two_deck(test_seed, player_count)
    deck_two = build_age_two_deck(test_seed, player_count)

    expected_count = player_count * 7

    print("\nPlayers:", player_count)
    print("Expected cards:", expected_count)
    print("Actual cards:", len(deck_one))
    print("Deck:", deck_one)

    if deck_one == deck_two and len(deck_one) == expected_count:
        print("SUCCESS! Age II deck is correct and deterministic.")
    else:
        print("FAILED! Age II deck is incorrect.")


print("\n========== AGE III DECK TEST ==========")

test_seed = bytes.fromhex(
    "ccdd2abe" + "11" * 28
)

for player_count in range(3, 8):
    player_ids = list(range(1, player_count + 1))

    setup = create_game_setup(
        test_seed,
        player_ids,
        both_sides=True
    )

    selected_guilds = setup["guild_cards"]

    deck_one = build_age_three_deck(
        test_seed,
        player_count,
        selected_guilds
    )

    deck_two = build_age_three_deck(
        test_seed,
        player_count,
        selected_guilds
    )

    expected_count = player_count * 7

    print("\nPlayers:", player_count)
    print("Expected cards:", expected_count)
    print("Actual cards:", len(deck_one))
    print("Selected Guilds:", selected_guilds)
    print("Deck:", deck_one)

    if deck_one == deck_two and len(deck_one) == expected_count:
        print("SUCCESS! Age III deck is correct and deterministic.")
    else:
        print("FAILED! Age III deck is incorrect.")


print("\n========== COMPLETE DECK SETUP TEST ==========")

test_seed = bytes.fromhex(
    "ccdd2abe" + "11" * 28
)

for player_count in range(3, 8):
    player_ids = list(range(1, player_count + 1))

    setup = create_game_setup(
        test_seed,
        player_ids,
        both_sides=True
    )

    selected_guilds = setup["guild_cards"]

    # Simulate three peers independently generating their decks.
    player_decks = []

    for _ in range(3):
        decks = build_all_age_decks(
            test_seed,
            player_count,
            selected_guilds
        )
        player_decks.append(decks)

    expected_count = player_count * 7

    same_decks = (
        player_decks[0] == player_decks[1]
        and player_decks[1] == player_decks[2]
    )

    correct_sizes = all(
        len(decks["age_one"]) == expected_count
        and len(decks["age_two"]) == expected_count
        and len(decks["age_three"]) == expected_count
        for decks in player_decks
    )

    print("\nPlayers:", player_count)
    print("Age I:", len(player_decks[0]["age_one"]))
    print("Age II:", len(player_decks[0]["age_two"]))
    print("Age III:", len(player_decks[0]["age_three"]))

    if same_decks and correct_sizes:
        print("SUCCESS! All three players generated identical decks.")
    else:
        print("FAILED! Deck generation is inconsistent.")


print("\n========== CARD DEALING TEST ==========")

test_seed = bytes.fromhex(
    "ccdd2abe" + "11" * 28
)

for player_count in range(3, 8):
    player_ids = list(range(1, player_count + 1))

    setup = create_game_setup(
        test_seed,
        player_ids,
        both_sides=True
    )

    selected_guilds = setup["guild_cards"]

    # Simulate three peers independently generating their decks.
    player_decks = []

    for _ in range(3):
        decks = build_all_age_decks(
            test_seed,
            player_count,
            selected_guilds
        )
        player_decks.append(decks)

    print("\nPlayers:", player_count)

    for age in ["age_one", "age_two", "age_three"]:
        # Each peer independently deals the cards.
        peer_hands = []

        for peer in range(3):
            hands = []

            for seat in range(player_count):
                hand = deal_hand(
                    player_decks[peer][age],
                    seat,
                    player_count
                )
                hands.append(hand)

            peer_hands.append(hands)

        # Check that every peer calculated identical hands.
        same_hands = (
            peer_hands[0] == peer_hands[1]
            and peer_hands[1] == peer_hands[2]
        )

        # Check that every hand contains seven cards.
        correct_sizes = all(
            len(hand) == 7
            for hand in peer_hands[0]
        )

        # Check that all hands reconstruct the original deck.
        combined_hands = [
            card
            for hand in peer_hands[0]
            for card in hand
        ]

        correct_order = (
            combined_hands == player_decks[0][age]
        )

        if same_hands and correct_sizes and correct_order:
            print(age, ": SUCCESS")
        else:
            print(age, ": FAILED")

    print("Card dealing test completed.")



print("\n========== CARD COMMITMENT TEST ==========")

card_id = "Lumber Yard"
action = "BUILD"

result = create_card_commitment(card_id, action)

commitment = result["commitment"]
nonce = result["nonce"]

print("Card:", card_id)
print("Action:", action)
print("Commitment:", commitment)
print("Nonce:", nonce)

# Verify the original information.
valid_result = verify_card_commitment(
    card_id,
    action,
    nonce,
    commitment
)

# Try changing the card.
invalid_result = verify_card_commitment(
    "Stone Pit",
    action,
    nonce,
    commitment
)

print("\nOriginal information:", valid_result)
print("Changed card:", invalid_result)

if valid_result and not invalid_result:
    print("SUCCESS! Card commitment verification works.")
else:
    print("FAILED! Card commitment verification is incorrect.")



print("\n========== CARD REVEAL TEST ==========")

# Test BUILD.
card_id = "Lumber Yard"
action = "BUILD"

result = create_card_commitment(card_id, action)

reveal = create_card_reveal(
    card_id,
    action,
    result["nonce"]
)

print("\nBUILD reveal:", reveal)

build_valid = verify_card_reveal(
    reveal,
    result["commitment"]
)

print("BUILD verification:", build_valid)


# Test WONDER_STAGE.
action = "WONDER_STAGE"

result = create_card_commitment("Lumber Yard", action)

reveal = create_card_reveal(
    "Lumber Yard",
    action,
    result["nonce"]
)

print("\nWONDER_STAGE reveal:", reveal)

wonder_valid = verify_card_reveal(
    reveal,
    result["commitment"]
)

print("WONDER_STAGE format:", wonder_valid)


# Test DISCARD.
action = "DISCARD"

result = create_card_commitment("Lumber Yard", action)

reveal = create_card_reveal(
    "Lumber Yard",
    action,
    result["nonce"]
)

print("\nDISCARD reveal:", reveal)

discard_valid = verify_card_reveal(
    reveal,
    result["commitment"]
)

print("DISCARD format:", discard_valid)


if build_valid and wonder_valid and discard_valid:
    print("\nSUCCESS! All reveal formats passed.")
else:
    print("\nFAILED! Check the reveal implementation.")

# Close all UDP transports.
for transport in transports:
    transport.close()