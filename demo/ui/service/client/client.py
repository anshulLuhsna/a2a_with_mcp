import httpx
from httpx_sse import connect_sse
from typing import Any, AsyncIterable
from state.url_utils import api
from service.types import (
    CreateConversationRequest,
    CreateConversationResponse,
    ListConversationRequest,
    ListConversationResponse,
    SendMessageRequest,
    SendMessageResponse,
    ListMessageRequest,
    ListMessageResponse,
    GetEventRequest,
    GetEventResponse,
    PendingMessageRequest,
    PendingMessageResponse,
    ListTaskRequest,
    ListTaskResponse,
    RegisterAgentRequest,
    RegisterAgentResponse,
    AgentClientHTTPError,
    ListAgentRequest,
    ListAgentResponse,
    AgentClientJSONError,
    JSONRPCRequest,
    Conversation,
)
import json
from urllib.parse import urlparse

class ConversationClient:

  def __init__(self, base_url):
    # Ensure the base_url has a scheme
    parsed_url = urlparse(base_url)
    if not parsed_url.scheme:
        self.base_url = f"http://{base_url}".rstrip("/")
    else:
        self.base_url = base_url.rstrip("/")

  async def send_message(self, payload: SendMessageRequest) -> SendMessageResponse:
    return SendMessageResponse(**await self._send_request(payload))

  async def _send_request(self, request: JSONRPCRequest) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
      try:
        endpoint_url = api(request.method)
        # Log the endpoint URL for debugging
        print(f"Making request to: {endpoint_url}")
        response = await client.post(
          endpoint_url, json=request.model_dump()
        )
        response.raise_for_status()
        return response.json()
      except httpx.HTTPStatusError as e:
        raise AgentClientHTTPError(e.response.status_code, str(e)) from e
      except json.JSONDecodeError as e:
        raise AgentClientJSONError(str(e)) from e
      except Exception as e:
        print(f"Unexpected error in _send_request: {str(e)}")
        return {"result": None}  # Return a default result that won't break the calling code

  async def create_conversation(self, payload: CreateConversationRequest) -> CreateConversationResponse:
    return CreateConversationResponse(**await self._send_request(payload))

  async def list_conversation(self, payload: ListConversationRequest) -> ListConversationResponse:
    return ListConversationResponse(**await self._send_request(payload))

  async def get_events(self, payload: GetEventRequest) -> GetEventResponse:
    return GetEventResponse(**await self._send_request(payload))

  async def list_messages(self, payload: ListMessageRequest) -> ListMessageResponse:
    return ListMessageResponse(**await self._send_request(payload))


  async def get_pending_messages(self, payload: PendingMessageRequest) -> PendingMessageResponse:
    return PendingMessageResponse(**await self._send_request(payload))

  async def list_tasks(self, payload: ListTaskRequest) -> ListTaskResponse:
    return ListTaskResponse(**await self._send_request(payload))

  async def register_agent(self, payload: RegisterAgentRequest) -> RegisterAgentResponse:
    return RegisterAgentResponse(**await self._send_request(payload))

  async def list_agents(self, payload: ListAgentRequest) -> ListAgentResponse:
    return ListAgentResponse(**await self._send_request(payload))

