from networking.packet import Packet

DIRECT_MESSAGE = 0x18
GROUP_MESSAGE = 0x19

class ChatSystem:
  def __init__(self, transport, session_id, local_peer_id):
    self.transport = transport
    self.session_id = session_id
    self.local_peer_id = local_peer_id

  def handle_message(self, message, sender_peer_id):
    if message.message_type == DIRECT_MESSAGE:
      text = message.payload.get("text", "")
      print(f"\n[Private from Player {sender_peer_id}]: {text}")

    elif message.message_type == GROUP_MESSAGE:
      text = message.payload.get("text", "")
      print(f"\n[Group from Player {sender_peer_id}]: {text}")
