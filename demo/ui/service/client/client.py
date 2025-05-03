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

  def __init__(self, base_url=None):
    # The base_url is no longer needed here as _send_request uses api()
    pass

  async def send_message(self, payload: SendMessageRequest) -> SendMessageResponse:
    return SendMessageResponse(**await self._send_request(payload))

  async def _send_request(self, request: JSONRPCRequest) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
      try:
        # api() now provides the full URL including the base
        endpoint_url = api(request.method)
        print(f"Making request to: {endpoint_url}")
        response = await client.post(
          endpoint_url, json=request.model_dump()
        )
        response.raise_for_status()
        return response.json()
      except httpx.HTTPStatusError as e:
        # Provide more context in the error message
        error_message = f"HTTP Error {e.response.status_code} calling {e.request.url}: {str(e)}"
        print(error_message)
        # Optionally, inspect e.response.text for more details from the server
        # print(f"Response body: {e.response.text}") 
        raise AgentClientHTTPError(e.response.status_code, error_message) from e
      except httpx.RequestError as e:
         # Handle connection errors, timeouts etc.
        error_message = f"Request failed for {e.request.url}: {str(e)}"
        print(error_message)
        raise AgentClientHTTPError(500, error_message) from e # Use a generic 500 or specific code
      except json.JSONDecodeError as e:
        error_message = f"Failed to decode JSON response: {str(e)}"
        print(error_message)
        raise AgentClientJSONError(error_message) from e
      except Exception as e:
        # Catch unexpected errors
        error_message = f"Unexpected error in _send_request: {str(e)}"
        print(error_message)
        # Returning a dict might hide the error, better to raise
        # return {"result": None} # Avoid this if possible
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

