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
    # Restore base_url initialization
    # Ensure the base_url has a scheme
    parsed_url = urlparse(base_url)
    if not parsed_url.scheme:
        self.base_url = f"http://{base_url}".rstrip("/") # Should be UI server URL
    else:
        self.base_url = base_url.rstrip("/")
    print(f"[ConversationClient] Initialized with base_url: {self.base_url}")

  async def send_message(self, payload: SendMessageRequest) -> SendMessageResponse:
    return SendMessageResponse(**await self._send_request(payload))

  async def _send_request(self, request: JSONRPCRequest) -> dict[str, Any]:
    # Use the api() function which now gets the correct BASE URL (UI server)
    endpoint_url = api(request.method)
    print(f"[ConversationClient] Making request to: {endpoint_url}")
    async with httpx.AsyncClient() as client:
      try:
        response = await client.post(
          endpoint_url, json=request.model_dump()
        )
        response.raise_for_status()
        return response.json()
      except httpx.HTTPStatusError as e:
        error_message = f"HTTP Error {e.response.status_code} calling {e.request.url}: {str(e)}"
        print(error_message)
        raise AgentClientHTTPError(e.response.status_code, error_message) from e
      except httpx.RequestError as e:
        error_message = f"Request failed for {e.request.url}: {str(e)}"
        print(error_message)
        raise AgentClientHTTPError(500, error_message) from e
      except json.JSONDecodeError as e:
        error_message = f"Failed to decode JSON response: {str(e)}"
        print(error_message)
        raise AgentClientJSONError(error_message) from e
      except Exception as e:
        error_message = f"Unexpected error in _send_request: {str(e)}"
        print(error_message)
        raise AgentClientHTTPError(500, error_message) from e

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

