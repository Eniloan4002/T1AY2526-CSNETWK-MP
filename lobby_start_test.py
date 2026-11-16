
import time
from networking.lobby import Lobby

player1 = Lobby("start-test", "Player 1", "127.0.0.1", 5001)
player2 = Lobby("start-test", "Player 2", "127.0.0.1", 5002)
player3 = Lobby("start-test", "Player 3", "127.0.0.1", 5003)

players = [player1, player2, player3]

try:
    for player in players:
        player.start()

    print("\nWaiting for all players to discover each other...")

    time.sleep(5)

    for player in players:
        print(f"\n{player.display_name}:")
        print("Players found:", len(player.get_roster()))

    print("\nWaiting for the start vote...")
    time.sleep(5)

    for player in players:
        print(f"\n{player.display_name}:")
        print("Start vote:", player.start_vote)
        print("Start acknowledgments:", len(player.start_acks))
        print("Game started:", player.game_started)

finally:
    for player in players:
        player.stop()