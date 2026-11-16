
import time
from networking.lobby import Lobby

player1 = Lobby("test-room", "Player 1", "127.0.0.1", 5001)
player2 = Lobby("test-room", "Player 2", "127.0.0.1", 5002)

try:
    player1.start()
    player2.start()

    time.sleep(3)

    print("\nBefore Player 2 leaves:")
    print("Player 1:", player1.get_roster())
    print("Player 2:", player2.get_roster())

    print("\nPlayer 2 is leaving...")
    player2.stop()

    time.sleep(1)

    print("\nAfter Player 2 leaves:")
    print("Player 1:", player1.get_roster())

finally:
    player1.stop()
    player2.stop()