import requests
from common.types import AgentCard
from state.url_utils import normalize_base

def get_agent_card(remote_agent_address: str) -> AgentCard:
  """Get the agent card."""
  normalized_address = normalize_base(remote_agent_address)
  manifest_url = f"{normalized_address}/.well-known/agent.json"
  print(f"[get_agent_card] Fetching manifest from: {manifest_url}")
  agent_card = requests.get(manifest_url)
  agent_card.raise_for_status()
  return AgentCard(**agent_card.json())
