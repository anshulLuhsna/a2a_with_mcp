from ..types import (
    JSONRPCResponse,
    ContentTypeNotSupportedError,
    UnsupportedOperationError,
    InvalidParamsError,
    JSONParseError,
    InvalidRequestError,
    MethodNotFoundError,
    InternalError
)
from typing import List, Any


def are_modalities_compatible(
    server_output_modes: List[str], client_output_modes: List[str]
):
    """Modalities are compatible if they are both non-empty
    and there is at least one common element."""
    if client_output_modes is None or len(client_output_modes) == 0:
        return True

    if server_output_modes is None or len(server_output_modes) == 0:
        return True

    return any(x in server_output_modes for x in client_output_modes)


def new_incompatible_types_error(request_id):
    return JSONRPCResponse(id=request_id, error=ContentTypeNotSupportedError())


def new_not_implemented_error(request_id):
    return JSONRPCResponse(id=request_id, error=UnsupportedOperationError())


def new_parse_error(request_id: str | int | None) -> JSONRPCResponse:
    """Creates a JSON-RPC Parse Error response."""
    return JSONRPCResponse(id=request_id, error=JSONParseError())


def new_invalid_request_error(request_id: str | int | None, message: str | None = None) -> JSONRPCResponse:
    """Creates a JSON-RPC Invalid Request response."""
    return JSONRPCResponse(id=request_id, error=InvalidRequestError(message=message))


def new_method_not_found_error(request_id: str | int | None) -> JSONRPCResponse:
    """Creates a JSON-RPC Method Not Found response."""
    return JSONRPCResponse(id=request_id, error=MethodNotFoundError())


def new_invalid_params_error(request_id: str | int | None, message: str | None = None) -> JSONRPCResponse:
    """Creates a JSON-RPC Invalid Params response."""
    return JSONRPCResponse(id=request_id, error=InvalidParamsError(message=message))


def new_internal_error(request_id: str | int | None, message: str | None = None) -> JSONRPCResponse:
    """Creates a JSON-RPC Internal Error response."""
    return JSONRPCResponse(id=request_id, error=InternalError(message=message))
