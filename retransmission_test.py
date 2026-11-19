from networking.reliability import ReliableChannel, RTO_INIT


channel = ReliableChannel()

sequence = channel.get_next_sequence()
channel.track_message(sequence, "Hello Player 2!", current_time=0)

print("Original message:", channel.pending_messages)

# Simulate six consecutive timeouts
current_time = 0

for attempt in range(1, 7):
    current_time += channel.rto + 0.01

    print(f"\nTimeout attempt {attempt}")
    messages = channel.check_timeouts(current_time)

    print("Messages to resend:", messages)
    print("Current RTO:", channel.rto)
    print("Timeout count:", channel.timeout_count)
    print("Channel failed:", channel.failed)

    if channel.failed:
        break

print("\nTesting failed channel:")

try:
    channel.get_next_sequence()
except RuntimeError as error:
    print("Correctly blocked:", error)