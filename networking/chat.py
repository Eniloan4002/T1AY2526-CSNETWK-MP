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

  def send_direct_message(self, target_peer_id, text):
    if target_peer_id not in self.transport.peers:
      printf(f"Cannot send message: Player {target_peer_id} not found.")
      return

    packet = Packet(
      message_type=DIRECT_MESSAGE,
      session_id=self.session_id,
      sender_peer_id=self.local_peer_id,
      sequence_number=0,
      payload={"text": text}
    )

  peer = self.transport.peers[target_peer_id]
  self.transport.send_reliable_packet(
    packet,
    peer["outgoing_channel"],
    peer["address"],
    peer["incoming_channel"]
  )
  print(f"[Private -> Player {target_peer_id}]: {text}")

def send_group_message(self, text):
  packet = Packet(
    message_type=GROUP_MESSAGE,
    session_id=self.session_id,
    sender_peer_id=self.local_peer_id,
    sequence_number=0,
    ack_number=0,
    payload={"text": text}
  )

  for peer_id, peer in self.transport.peers.items():
    self.transport.send_reliable_packet(
      packet,
      peer["outgoing_channel"],
      peer["address"],
      peer["incoming_channel"]
    )
    print(f"[Group Chat]: {text}")
