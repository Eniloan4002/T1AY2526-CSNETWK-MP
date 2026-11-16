
import threading
import time

from networking.udp import UDPTransport
from networking.peer_discovery import PeerDiscovery


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

# Close all UDP transports.
for transport in transports:
    transport.close()