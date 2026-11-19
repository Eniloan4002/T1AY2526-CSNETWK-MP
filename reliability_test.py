from networking.reliability import ReliableChannel


channel = ReliableChannel()

print("Testing outgoing messages:")

for i in range(4):
    sequence = channel.get_next_sequence()
    channel.track_message(sequence, f"Message {i + 1}")
    print("Sent:", sequence)

print("\nPending messages:", channel.pending_messages)

print("\nTesting the 4-message limit:")

try:
    channel.get_next_sequence()
except RuntimeError as error:
    print("Correctly blocked:", error)

print("\nTesting acknowledgment:")

channel.acknowledge(2)

print("Pending messages after ACK 2:", channel.pending_messages)

print("\nTesting sending after acknowledgment:")

sequence = channel.get_next_sequence()
channel.track_message(sequence, "Message 5")

print("New message sequence:", sequence)
print("Pending messages:", channel.pending_messages)

print("\nTesting message ordering:")

receiver = ReliableChannel()

print("Received 1:", receiver.receive(1, "Hello"))
print("Received 3:", receiver.receive(3, "Start"))
print("Received 2:", receiver.receive(2, "Ready"))

print("\nFinal ACK number:", receiver.get_ack_number())