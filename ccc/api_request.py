"""
API Request data structures for Command Center

Defines the core data models for API testing functionality.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
from enum import Enum
import json


class HttpMethod(Enum):
    """HTTP request methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

    @classmethod
    def from_string(cls, method: str) -> 'HttpMethod':
        """Parse method from string"""
        try:
            return cls(method.upper())
        except ValueError:
            raise ValueError(f"Invalid HTTP method: {method}. Must be one of: {', '.join(m.value for m in cls)}")


@dataclass
class ApiRequest:
    """
    Represents an API request.

    Stores all information needed to execute an HTTP request,
    including method, URL, headers, body, and validation criteria.
    """

    name: str
    method: HttpMethod
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    expected_status: Optional[int] = None
    timeout: int = 30
    follow_redirects: bool = True

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_executed: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for YAML storage.

        Returns:
            Dictionary representation suitable for YAML serialization
        """
        return {
            "name": self.name,
            "method": self.method.value,
            "url": self.url,
            "headers": self.headers,
            "body": self.body,
            "expected_status": self.expected_status,
            "timeout": self.timeout,
            "follow_redirects": self.follow_redirects,
            "created_at": self.created_at.isoformat(),
            "last_executed": self.last_executed.isoformat() if self.last_executed else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApiRequest':
        """
        Load from dictionary (from YAML).

        Args:
            data: Dictionary containing request data

        Returns:
            ApiRequest instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Parse method
        method = HttpMethod.from_string(data["method"])

        # Parse dates
        created_at = datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now()
        last_executed = datetime.fromisoformat(data["last_executed"]) if data.get("last_executed") else None

        return cls(
            name=data["name"],
            method=method,
            url=data["url"],
            headers=data.get("headers", {}),
            body=data.get("body"),
            expected_status=data.get("expected_status"),
            timeout=data.get("timeout", 30),
            follow_redirects=data.get("follow_redirects", True),
            created_at=created_at,
            last_executed=last_executed,
        )

    def needs_body(self) -> bool:
        """Check if this HTTP method typically includes a request body"""
        return self.method in [HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH]

    def update_last_executed(self):
        """Update the last executed timestamp to now"""
        self.last_executed = datetime.now(timezone.utc)


@dataclass
class ApiResponse:
    """
    Represents an API response.

    Contains all information about the HTTP response including
    status, headers, body, and timing information.
    """

    status_code: int
    reason: str
    headers: Dict[str, str]
    body: str
    elapsed_ms: float
    timestamp: datetime = field(default_factory=datetime.now)

    def is_json(self) -> bool:
        """
        Check if response content type is JSON.

        Returns:
            True if the Content-Type header indicates JSON
        """
        content_type = self.headers.get("content-type", "").lower()
        return "application/json" in content_type or "application/json" in content_type

    def get_formatted_body(self) -> str:
        """
        Get formatted response body.

        If the response is JSON, returns pretty-printed JSON.
        Otherwise returns the body as-is.

        Returns:
            Formatted response body
        """
        if self.is_json():
            try:
                parsed = json.loads(self.body)
                return json.dumps(parsed, indent=2)
            except json.JSONDecodeError:
                # If JSON parsing fails, return as-is
                return self.body
        return self.body

    def status_color(self) -> str:
        """
        Get color name for status code.

        Returns:
            Color string: "green" (2xx), "yellow" (3xx), "orange" (4xx), "red" (5xx)
        """
        if 200 <= self.status_code < 300:
            return "green"
        elif 300 <= self.status_code < 400:
            return "yellow"
        elif 400 <= self.status_code < 500:
            return "orange"
        else:  # 500+
            return "red"

    def status_symbol(self) -> str:
        """
        Get symbol for status code.

        Returns:
            Symbol: "✓" (2xx), "→" (3xx), "⚠" (4xx), "✗" (5xx)
        """
        if 200 <= self.status_code < 300:
            return "✓"
        elif 300 <= self.status_code < 400:
            return "→"
        elif 400 <= self.status_code < 500:
            return "⚠"
        else:  # 500+
            return "✗"

    def matches_expected(self, expected: Optional[int]) -> bool:
        """
        Check if status code matches expected value.

        Args:
            expected: Expected status code (None means no expectation)

        Returns:
            True if status matches or no expectation set
        """
        if expected is None:
            return True
        return self.status_code == expected

    def is_success(self) -> bool:
        """
        Check if response is successful (2xx status).

        Returns:
            True if status code is in the 200-299 range
        """
        return 200 <= self.status_code < 300

    def is_error(self) -> bool:
        """
        Check if response is an error (4xx or 5xx status).

        Returns:
            True if status code is 400 or above
        """
        return self.status_code >= 400

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for storage.

        Returns:
            Dictionary representation
        """
        return {
            "status_code": self.status_code,
            "reason": self.reason,
            "headers": self.headers,
            "body": self.body,
            "elapsed_ms": self.elapsed_ms,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApiResponse':
        """
        Load from dictionary.

        Args:
            data: Dictionary containing response data

        Returns:
            ApiResponse instance
        """
        return cls(
            status_code=data["status_code"],
            reason=data["reason"],
            headers=data["headers"],
            body=data["body"],
            elapsed_ms=data["elapsed_ms"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class ApiRequestExecution:
    """
    Record of a request execution.

    Stores the request, response (if successful), and any error
    that occurred during execution.
    """

    request_name: str
    method: str
    url: str
    response: Optional[ApiResponse] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def success(self) -> bool:
        """Whether request succeeded (no error and got response)"""
        return self.response is not None and self.error is None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for storage.

        Returns:
            Dictionary representation
        """
        return {
            "request_name": self.request_name,
            "method": self.method,
            "url": self.url,
            "response": self.response.to_dict() if self.response else None,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApiRequestExecution':
        """
        Load from dictionary.

        Args:
            data: Dictionary containing execution data

        Returns:
            ApiRequestExecution instance
        """
        response = ApiResponse.from_dict(data["response"]) if data.get("response") else None

        return cls(
            request_name=data["request_name"],
            method=data["method"],
            url=data["url"],
            response=response,
            error=data.get("error"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class VariableStore:
    """
    Stores variables for request substitution.

    Variables can be used in URLs, headers, and body using {{variable_name}} syntax.
    """

    variables: Dict[str, str] = field(default_factory=dict)

    def set(self, key: str, value: str):
        """Set a variable value"""
        self.variables[key] = value

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a variable value"""
        return self.variables.get(key, default)

    def delete(self, key: str) -> bool:
        """Delete a variable. Returns True if it existed."""
        if key in self.variables:
            del self.variables[key]
            return True
        return False

    def substitute(self, text: str) -> str:
        """
        Substitute all variables in text.

        Replaces {{variable_name}} with the variable value.

        Args:
            text: Text containing {{variable}} placeholders

        Returns:
            Text with all variables substituted

        Example:
            >>> store = VariableStore({"host": "localhost", "port": "3000"})
            >>> store.substitute("http://{{host}}:{{port}}/api")
            'http://localhost:3000/api'
        """
        if not text:
            return text

        result = text
        for key, value in self.variables.items():
            placeholder = f"{{{{{key}}}}}"  # {{key}}
            result = result.replace(placeholder, value)

        return result

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for YAML storage"""
        return self.variables.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'VariableStore':
        """Load from dictionary"""
        return cls(variables=data.copy())
