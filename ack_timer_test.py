from networking.reliability import ReliableChannel

channel = ReliableChannel()

# First message arrives at 0 seconds
channel.schedule_ack(current_time=0)
print("First deadline:", channel.ack_deadline)

# Another message arrives at 0.02 seconds
channel.schedule_ack(current_time=0.02)
print("Second deadline:", channel.ack_deadline)

# Check whether ACK is due at 0.05 seconds
print("ACK due at 0.05:", channel.is_ack_due(current_time=0.05))