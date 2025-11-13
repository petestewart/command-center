"""
API Testing module for Command Center

Handles storage, execution, and management of API requests.
Includes Phase 7 Enhancements: authentication, environments, and request chaining.
"""

import yaml
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

from ccc.api_request import (
    ApiRequest,
    ApiResponse,
    ApiRequestExecution,
    VariableStore,
    HttpMethod,
    AuthConfig,
    CaptureRule,
    Environment,
    EnvironmentStore,
)
from ccc.utils import get_ccc_home


def get_api_requests_path(branch_name: str) -> Path:
    """
    Get path to API requests file for a branch.

    Args:
        branch_name: Branch name

    Returns:
        Path to api-requests.yaml
    """
    from ccc.utils import get_branch_dir
    return get_branch_dir(branch_name) / "api-requests.yaml"


def get_api_history_path(branch_name: str) -> Path:
    """
    Get path to API history file for a branch.

    Args:
        branch_name: Branch name

    Returns:
        Path to api-history.yaml
    """
    from ccc.utils import get_branch_dir
    return get_branch_dir(branch_name) / "api-history.yaml"


def ensure_api_files(branch_name: str):
    """
    Ensure API request and history files exist for a branch.

    Args:
        branch_name: Branch name
    """
    requests_path = get_api_requests_path(branch_name)
    history_path = get_api_history_path(branch_name)

    if not requests_path.exists():
        save_requests(branch_name, [], VariableStore())

    if not history_path.exists():
        save_history(branch_name, [])


def load_requests(branch_name: str) -> Tuple[List[ApiRequest], VariableStore]:
    """
    Load API requests and variables for a branch.

    Args:
        branch_name: Branch name

    Returns:
        Tuple of (list of ApiRequest objects, VariableStore)
    """
    ensure_api_files(branch_name)
    path = get_api_requests_path(branch_name)

    try:
        with open(path, 'r') as f:
            data = yaml.safe_load(f) or {}

        # Load requests
        requests_data = data.get("requests", [])
        requests_list = [ApiRequest.from_dict(req) for req in requests_data]

        # Load variables
        variables_data = data.get("variables", {})
        variable_store = VariableStore.from_dict(variables_data)

        return requests_list, variable_store

    except Exception as e:
        # Return empty lists on error
        return [], VariableStore()


def save_requests(branch_name: str, requests_list: List[ApiRequest], variables: VariableStore):
    """
    Save API requests and variables for a branch.

    Args:
        branch_name: Branch name
        requests_list: List of ApiRequest objects
        variables: VariableStore with variables
    """
    path = get_api_requests_path(branch_name)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "requests": [req.to_dict() for req in requests_list],
        "variables": variables.to_dict(),
    }

    with open(path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def load_history(branch_name: str, limit: Optional[int] = None) -> List[ApiRequestExecution]:
    """
    Load request execution history for a branch.

    Args:
        branch_name: Branch name
        limit: Maximum number of history entries to return (most recent first)

    Returns:
        List of ApiRequestExecution objects
    """
    ensure_api_files(branch_name)
    path = get_api_history_path(branch_name)

    try:
        with open(path, 'r') as f:
            data = yaml.safe_load(f) or {}

        history_data = data.get("history", [])
        history = [ApiRequestExecution.from_dict(exec_data) for exec_data in history_data]

        # Sort by timestamp descending (most recent first)
        history.sort(key=lambda x: x.timestamp, reverse=True)

        if limit:
            history = history[:limit]

        return history

    except Exception:
        return []


def save_history(branch_name: str, history: List[ApiRequestExecution], max_entries: int = 50):
    """
    Save request execution history for a branch.

    Args:
        branch_name: Branch name
        history: List of ApiRequestExecution objects
        max_entries: Maximum number of history entries to keep
    """
    path = get_api_history_path(branch_name)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Sort by timestamp descending and limit
    history.sort(key=lambda x: x.timestamp, reverse=True)
    history = history[:max_entries]

    data = {
        "history": [exec_data.to_dict() for exec_data in history],
    }

    with open(path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def add_to_history(branch_name: str, execution: ApiRequestExecution, max_entries: int = 50):
    """
    Add an execution to history.

    Args:
        branch_name: Branch name
        execution: ApiRequestExecution to add
        max_entries: Maximum number of history entries to keep
    """
    history = load_history(branch_name)
    history.insert(0, execution)
    save_history(branch_name, history, max_entries)


def get_request(branch_name: str, request_name: str) -> Optional[ApiRequest]:
    """
    Get a specific request by name.

    Args:
        branch_name: Branch name
        request_name: Request name

    Returns:
        ApiRequest or None if not found
    """
    requests_list, _ = load_requests(branch_name)
    for req in requests_list:
        if req.name == request_name:
            return req
    return None


def add_request(branch_name: str, request: ApiRequest) -> bool:
    """
    Add a new request.

    Args:
        branch_name: Branch name
        request: ApiRequest to add

    Returns:
        True if added successfully, False if name already exists
    """
    requests_list, variables = load_requests(branch_name)

    # Check if name already exists
    if any(req.name == request.name for req in requests_list):
        return False

    requests_list.append(request)
    save_requests(branch_name, requests_list, variables)
    return True


def update_request(branch_name: str, request: ApiRequest) -> bool:
    """
    Update an existing request.

    Args:
        branch_name: Branch name
        request: ApiRequest with updated data

    Returns:
        True if updated successfully, False if not found
    """
    requests_list, variables = load_requests(branch_name)

    for i, req in enumerate(requests_list):
        if req.name == request.name:
            requests_list[i] = request
            save_requests(branch_name, requests_list, variables)
            return True

    return False


def delete_request(branch_name: str, request_name: str) -> bool:
    """
    Delete a request.

    Args:
        branch_name: Branch name
        request_name: Name of request to delete

    Returns:
        True if deleted, False if not found
    """
    requests_list, variables = load_requests(branch_name)

    original_len = len(requests_list)
    requests_list = [req for req in requests_list if req.name != request_name]

    if len(requests_list) < original_len:
        save_requests(branch_name, requests_list, variables)
        return True

    return False


def _apply_authentication(
    auth_config: AuthConfig,
    variables: VariableStore,
    url: str
) -> Tuple[Dict[str, str], str, Optional[Any]]:
    """
    Apply authentication configuration to request.

    Args:
        auth_config: Authentication configuration
        variables: Variable store for substitution
        url: Original URL (may be modified for query param auth)

    Returns:
        Tuple of (headers_to_add, modified_url, requests_auth_object)
    """
    headers = {}
    auth_obj = None

    if auth_config.type == "basic":
        # HTTP Basic Auth
        username = variables.substitute(auth_config.username or "")
        password = variables.substitute(auth_config.password or "")
        auth_obj = requests.auth.HTTPBasicAuth(username, password)

    elif auth_config.type == "bearer":
        # Bearer Token
        token = variables.substitute(auth_config.token or "")
        headers["Authorization"] = f"Bearer {token}"

    elif auth_config.type == "api_key":
        # API Key (header or query param)
        key_name = variables.substitute(auth_config.key_name or "")
        key_value = variables.substitute(auth_config.key_value or "")

        if auth_config.location == "header":
            headers[key_name] = key_value
        elif auth_config.location == "query":
            # Add to URL query parameters
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            query_params[key_name] = [key_value]
            new_query = urlencode(query_params, doseq=True)
            url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))

    return headers, url, auth_obj


def execute_request(
    request: ApiRequest,
    variables: VariableStore,
    verify_ssl: bool = True
) -> Tuple[Optional[ApiResponse], Optional[str]]:
    """
    Execute an API request.

    Args:
        request: ApiRequest to execute
        variables: VariableStore for variable substitution
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Tuple of (ApiResponse, error_message)
        Either response or error will be None
    """
    try:
        # Substitute variables in URL, headers, and body
        url = variables.substitute(request.url)
        headers = {k: variables.substitute(v) for k, v in request.headers.items()}
        body = variables.substitute(request.body) if request.body else None

        # Apply authentication if configured
        auth_obj = None
        if request.auth:
            auth_headers, url, auth_obj = _apply_authentication(request.auth, variables, url)
            headers.update(auth_headers)

        # Prepare request kwargs
        kwargs = {
            "timeout": request.timeout,
            "allow_redirects": request.follow_redirects,
            "verify": verify_ssl,
        }

        # Add auth object if present (for Basic Auth)
        if auth_obj:
            kwargs["auth"] = auth_obj

        # Add headers if present
        if headers:
            kwargs["headers"] = headers

        # Add body for methods that support it
        if body and request.needs_body():
            # Try to determine content type
            content_type = headers.get("Content-Type", "").lower()
            if "application/json" in content_type:
                # Parse as JSON if content type is JSON
                import json
                try:
                    kwargs["json"] = json.loads(body)
                except json.JSONDecodeError:
                    # Fall back to sending as text
                    kwargs["data"] = body
            else:
                kwargs["data"] = body

        # Execute request
        start_time = datetime.now(timezone.utc)
        response = requests.request(request.method.value, url, **kwargs)
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000  # Convert to ms

        # Build ApiResponse
        api_response = ApiResponse(
            status_code=response.status_code,
            reason=response.reason,
            headers=dict(response.headers),
            body=response.text,
            elapsed_ms=elapsed,
        )

        return api_response, None

    except requests.exceptions.Timeout:
        return None, f"Request timed out after {request.timeout} seconds"
    except requests.exceptions.ConnectionError as e:
        return None, f"Connection error: {str(e)}"
    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


def execute_request_by_name(
    branch_name: str,
    request_name: str,
    verify_ssl: bool = True
) -> Tuple[Optional[ApiResponse], Optional[str]]:
    """
    Execute a saved request by name.

    Args:
        branch_name: Branch name
        request_name: Name of the request to execute
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Tuple of (ApiResponse, error_message)
        Either response or error will be None
    """
    # Load request
    request = get_request(branch_name, request_name)
    if not request:
        return None, f"Request '{request_name}' not found"

    # Load variables
    _, variables = load_requests(branch_name)

    # Execute
    response, error = execute_request(request, variables, verify_ssl)

    # Update last executed time and save
    if response:
        request.update_last_executed()
        update_request(branch_name, request)

    # Add to history
    execution = ApiRequestExecution(
        request_name=request.name,
        method=request.method.value,
        url=request.url,
        response=response,
        error=error,
    )
    add_to_history(branch_name, execution)

    return response, error


def set_variable(branch_name: str, key: str, value: str):
    """
    Set a variable value.

    Args:
        branch_name: Branch name
        key: Variable name
        value: Variable value
    """
    requests_list, variables = load_requests(branch_name)
    variables.set(key, value)
    save_requests(branch_name, requests_list, variables)


def get_variable(branch_name: str, key: str) -> Optional[str]:
    """
    Get a variable value.

    Args:
        branch_name: Branch name
        key: Variable name

    Returns:
        Variable value or None if not found
    """
    _, variables = load_requests(branch_name)
    return variables.get(key)


def delete_variable(branch_name: str, key: str) -> bool:
    """
    Delete a variable.

    Args:
        branch_name: Branch name
        key: Variable name

    Returns:
        True if deleted, False if not found
    """
    requests_list, variables = load_requests(branch_name)
    if variables.delete(key):
        save_requests(branch_name, requests_list, variables)
        return True
    return False


def export_requests(branch_name: str, file_path: Path):
    """
    Export requests to a file.

    Args:
        branch_name: Branch name
        file_path: Path to export to
    """
    path = get_api_requests_path(branch_name)
    with open(path, 'r') as src:
        data = src.read()
    with open(file_path, 'w') as dst:
        dst.write(data)


def import_requests(branch_name: str, file_path: Path, merge: bool = False):
    """
    Import requests from a file.

    Args:
        branch_name: Branch name
        file_path: Path to import from
        merge: If True, merge with existing requests. If False, replace all.
    """
    with open(file_path, 'r') as f:
        data = yaml.safe_load(f) or {}

    new_requests_data = data.get("requests", [])
    new_variables_data = data.get("variables", {})

    new_requests = [ApiRequest.from_dict(req) for req in new_requests_data]
    new_variables = VariableStore.from_dict(new_variables_data)

    if merge:
        # Merge with existing
        existing_requests, existing_variables = load_requests(branch_name)

        # Merge requests (keep existing if name conflicts)
        existing_names = {req.name for req in existing_requests}
        for req in new_requests:
            if req.name not in existing_names:
                existing_requests.append(req)

        # Merge variables (new values override existing)
        for key, value in new_variables.variables.items():
            existing_variables.set(key, value)

        save_requests(branch_name, existing_requests, existing_variables)
    else:
        # Replace all
        save_requests(branch_name, new_requests, new_variables)


def clear_history(branch_name: str):
    """
    Clear all execution history for a branch.

    Args:
        branch_name: Branch name
    """
    save_history(branch_name, [])


# ============================================================================
# Phase 7 Enhancements: Request Chaining
# ============================================================================


def capture_variables_from_response(
    response: ApiResponse,
    capture_rules: List[CaptureRule]
) -> Dict[str, str]:
    """
    Capture variables from response body using JSONPath.

    Args:
        response: ApiResponse to extract from
        capture_rules: List of CaptureRule objects

    Returns:
        Dictionary of {variable_name: captured_value}
    """
    captured = {}

    # Parse response body as JSON
    try:
        import json
        body_data = json.loads(response.body)
    except json.JSONDecodeError:
        # Can't capture from non-JSON responses
        return captured

    # Apply each capture rule
    for rule in capture_rules:
        try:
            from jsonpath_ng import parse as jsonpath_parse

            # Parse JSONPath expression
            jsonpath_expr = jsonpath_parse(rule.jsonpath)

            # Find matches
            matches = jsonpath_expr.find(body_data)

            if matches:
                # Use first match
                value = matches[0].value
                captured[rule.name] = str(value)
        except Exception:
            # Skip invalid capture rules
            continue

    return captured


def build_request_chain(
    requests_list: List[ApiRequest],
    start_request_name: str
) -> List[ApiRequest]:
    """
    Build execution chain starting from a request.

    Analyzes depends_on fields to determine execution order.
    Uses topological sort to handle dependencies.

    Args:
        requests_list: List of all available requests
        start_request_name: Name of the request to start from

    Returns:
        Ordered list of requests to execute

    Raises:
        ValueError: If circular dependency detected or request not found
    """
    # Build a map of request names to requests
    request_map = {req.name: req for req in requests_list}

    # Check if start request exists
    if start_request_name not in request_map:
        raise ValueError(f"Request not found: {start_request_name}")

    chain = []
    visited = set()
    visiting = set()  # For cycle detection

    def visit(req_name: str):
        """DFS to build dependency chain."""
        if req_name in visiting:
            raise ValueError(f"Circular dependency detected involving: {req_name}")

        if req_name in visited:
            return

        visiting.add(req_name)

        # Find the request
        if req_name not in request_map:
            raise ValueError(f"Request not found: {req_name}")

        req = request_map[req_name]

        # Visit dependencies first
        if req.depends_on:
            visit(req.depends_on)

        # Add this request to chain
        visiting.remove(req_name)
        visited.add(req_name)
        chain.append(req)

    visit(start_request_name)
    return chain


def execute_request_chain(
    branch_name: str,
    start_request_name: str,
    verify_ssl: bool = True
) -> List[Tuple[ApiRequest, Optional[ApiResponse], Optional[str]]]:
    """
    Execute a chain of requests with variable capture.

    Requests are executed in dependency order. Variables captured
    from earlier responses are available in later requests.
    Execution stops on first error.

    Args:
        branch_name: Branch name
        start_request_name: Name of the request to start the chain from
        verify_ssl: Whether to verify SSL certificates

    Returns:
        List of (request, response, error) tuples for each execution
    """
    from ccc.api_environments import get_merged_variables

    # Load all requests
    requests_list, _ = load_requests(branch_name)

    # Build execution chain
    try:
        chain = build_request_chain(requests_list, start_request_name)
    except ValueError as e:
        # Return error for chain building failure
        req = get_request(branch_name, start_request_name)
        if req:
            return [(req, None, str(e))]
        return []

    # Track captured variables across the chain
    captured_vars = {}

    # Execute each request in order
    results = []
    for request in chain:
        # Merge environment vars + captured vars
        variables = get_merged_variables(branch_name, captured_vars)

        # Execute request
        response, error = execute_request(request, variables, verify_ssl)

        # Update last executed time and save
        if response:
            request.update_last_executed()
            update_request(branch_name, request)

        # Add to history
        execution = ApiRequestExecution(
            request_name=request.name,
            method=request.method.value,
            url=request.url,
            response=response,
            error=error,
        )
        add_to_history(branch_name, execution)

        # Store result
        results.append((request, response, error))

        # Stop on first error
        if error or not response:
            break

        # Capture variables from response
        if request.capture and response:
            new_captures = capture_variables_from_response(response, request.capture)
            captured_vars.update(new_captures)

    return results
