# Phase 7 Future: Advanced Assertions

## Overview

**Status:** Deferred for future enhancement
**Dependencies:** Phase 7 Enhancements must be completed first

This document contains advanced assertion features that were originally planned for Phase 7 Enhancements but removed to keep the phase focused. These features may be implemented in a future phase if needed.

---

## Deferred Assertion Features

### 1. JSON Path Assertions

Assert on specific fields in JSON responses:

```yaml
requests:
  - name: "Get user"
    method: GET
    url: "{{base_url}}/api/users/123"
    assertions:
      - type: status
        expected: 200
      - type: jsonpath
        path: "$.user.id"
        expected: 123
      - type: jsonpath
        path: "$.user.email"
        contains: "@example.com"
      - type: jsonpath
        path: "$.user.roles"
        contains: "admin"
```

**Response Viewer shows:**
```
Assertions:
✓ Status code is 200
✓ $.user.id equals 123
✓ $.user.email contains "@example.com"
✗ $.user.roles contains "admin" (actual: ["user"])
```

### 2. Schema Validation

Validate response against JSON Schema:

```yaml
requests:
  - name: "Get user"
    method: GET
    url: "{{base_url}}/api/users/123"
    assertions:
      - type: schema
        schema: |
          {
            "type": "object",
            "required": ["user"],
            "properties": {
              "user": {
                "type": "object",
                "required": ["id", "email"],
                "properties": {
                  "id": {"type": "integer"},
                  "email": {"type": "string", "format": "email"}
                }
              }
            }
          }
```

### 3. Regular Expression Matching

Match response fields against regex patterns:

```yaml
assertions:
  - type: regex
    path: "$.user.email"
    pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
  - type: regex
    field: body
    pattern: "success.*true"
```

### 4. Response Time Assertions

Assert on response time:

```yaml
assertions:
  - type: response_time
    max_ms: 500
    message: "API should respond within 500ms"
```

**Response viewer shows:**
```
✓ Response time: 234ms (max 500ms)
✗ Response time: 612ms (max 500ms)
```

---

## Data Structures for Assertions

```python
@dataclass
class Assertion:
    """Assertion to validate response."""
    type: str  # "status", "jsonpath", "schema", "regex", "response_time"

    # JSONPath assertion fields
    path: Optional[str] = None  # JSONPath expression (e.g., "$.user.id")
    expected: Optional[Any] = None  # Expected value
    contains: Optional[str] = None  # Check if value contains substring

    # Regex assertion fields
    pattern: Optional[str] = None  # Regex pattern
    field: Optional[str] = None  # "body" or specific field

    # Response time assertion
    max_ms: Optional[int] = None  # Maximum response time in ms
    message: Optional[str] = None  # Custom message

    # Schema validation
    schema: Optional[Dict[str, Any]] = None  # JSON Schema object

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for YAML storage."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Assertion':
        """Load from YAML dict."""
        return cls(**data)


@dataclass
class AssertionResult:
    """Result of running an assertion."""
    assertion: Assertion
    passed: bool
    message: str  # Human-readable result
    actual_value: Optional[Any] = None  # Actual value found


# Add to ApiRequest
@dataclass
class ApiRequest:
    # ... existing fields ...
    assertions: List[Assertion] = field(default_factory=list)


# Add to ApiResponse
@dataclass
class ApiResponse:
    # ... existing fields ...
    assertion_results: List[AssertionResult] = field(default_factory=list)

    def all_assertions_passed(self) -> bool:
        """Check if all assertions passed."""
        return all(r.passed for r in self.assertion_results)
```

---

## Implementation Approach

### Assertion Execution

```python
def evaluate_assertions(
    request: ApiRequest,
    response: ApiResponse
) -> List[AssertionResult]:
    """
    Evaluate all assertions for a request.

    Returns:
        List of assertion results
    """
    results = []

    for assertion in request.assertions:
        if assertion.type == "status":
            result = _evaluate_status_assertion(assertion, response)
        elif assertion.type == "jsonpath":
            result = _evaluate_jsonpath_assertion(assertion, response)
        elif assertion.type == "response_time":
            result = _evaluate_response_time_assertion(assertion, response)
        elif assertion.type == "schema":
            result = _evaluate_schema_assertion(assertion, response)
        elif assertion.type == "regex":
            result = _evaluate_regex_assertion(assertion, response)
        else:
            result = AssertionResult(
                assertion=assertion,
                passed=False,
                message=f"Unknown assertion type: {assertion.type}"
            )

        results.append(result)

    return results


def _evaluate_jsonpath_assertion(
    assertion: Assertion,
    response: ApiResponse
) -> AssertionResult:
    """Evaluate a JSONPath assertion."""
    try:
        import json
        from jsonpath_ng import parse as jsonpath_parse

        body_data = json.loads(response.body)

        # Parse JSONPath
        jsonpath_expr = jsonpath_parse(assertion.path)
        matches = jsonpath_expr.find(body_data)

        if not matches:
            return AssertionResult(
                assertion=assertion,
                passed=False,
                message=f"Path {assertion.path} not found in response",
                actual_value=None
            )

        actual_value = matches[0].value

        # Check for exact match
        if assertion.expected is not None:
            passed = actual_value == assertion.expected
            msg = f"{assertion.path} = {actual_value}"
            if passed:
                msg += " (expected)"
            else:
                msg += f" (expected {assertion.expected})"
        # Check for contains
        elif assertion.contains is not None:
            if isinstance(actual_value, (list, str)):
                passed = assertion.contains in actual_value
            else:
                passed = assertion.contains in str(actual_value)
            msg = f"{assertion.path} "
            msg += "contains" if passed else "does not contain"
            msg += f" '{assertion.contains}'"
        else:
            # Just check existence
            passed = True
            msg = f"{assertion.path} exists"

        return AssertionResult(
            assertion=assertion,
            passed=passed,
            message=msg,
            actual_value=actual_value
        )

    except Exception as e:
        return AssertionResult(
            assertion=assertion,
            passed=False,
            message=f"Assertion error: {str(e)}"
        )


def _evaluate_response_time_assertion(
    assertion: Assertion,
    response: ApiResponse
) -> AssertionResult:
    """Evaluate response time assertion."""
    passed = response.elapsed_ms <= assertion.max_ms
    msg = f"Response time: {response.elapsed_ms:.0f}ms (max {assertion.max_ms}ms)"

    if assertion.message:
        msg = assertion.message + f" ({response.elapsed_ms:.0f}ms)"

    return AssertionResult(
        assertion=assertion,
        passed=passed,
        message=msg,
        actual_value=response.elapsed_ms
    )


def _evaluate_schema_assertion(
    assertion: Assertion,
    response: ApiResponse
) -> AssertionResult:
    """Evaluate JSON schema assertion."""
    try:
        import json
        from jsonschema import validate, ValidationError

        body_data = json.loads(response.body)

        # Validate against schema
        validate(instance=body_data, schema=assertion.schema)

        return AssertionResult(
            assertion=assertion,
            passed=True,
            message="Response matches schema"
        )

    except ValidationError as e:
        return AssertionResult(
            assertion=assertion,
            passed=False,
            message=f"Schema validation failed: {e.message}"
        )
    except Exception as e:
        return AssertionResult(
            assertion=assertion,
            passed=False,
            message=f"Schema assertion error: {str(e)}"
        )


def _evaluate_regex_assertion(
    assertion: Assertion,
    response: ApiResponse
) -> AssertionResult:
    """Evaluate regex pattern assertion."""
    try:
        import re
        import json
        from jsonpath_ng import parse as jsonpath_parse

        # Get text to match against
        if assertion.field == "body":
            text = response.body
        elif assertion.path:
            body_data = json.loads(response.body)
            jsonpath_expr = jsonpath_parse(assertion.path)
            matches = jsonpath_expr.find(body_data)
            if not matches:
                return AssertionResult(
                    assertion=assertion,
                    passed=False,
                    message=f"Path {assertion.path} not found"
                )
            text = str(matches[0].value)
        else:
            return AssertionResult(
                assertion=assertion,
                passed=False,
                message="Must specify 'field' or 'path' for regex assertion"
            )

        # Match against pattern
        pattern = re.compile(assertion.pattern)
        matched = pattern.search(text) is not None

        target = assertion.field or assertion.path
        msg = f"{target} "
        msg += "matches" if matched else "does not match"
        msg += f" pattern '{assertion.pattern}'"

        return AssertionResult(
            assertion=assertion,
            passed=matched,
            message=msg,
            actual_value=text
        )

    except Exception as e:
        return AssertionResult(
            assertion=assertion,
            passed=False,
            message=f"Regex assertion error: {str(e)}"
        )


def _evaluate_status_assertion(
    assertion: Assertion,
    response: ApiResponse
) -> AssertionResult:
    """Evaluate status code assertion (already supported in Phase 7)."""
    passed = response.status_code == assertion.expected
    msg = f"Status code: {response.status_code}"
    if passed:
        msg += " (expected)"
    else:
        msg += f" (expected {assertion.expected})"

    return AssertionResult(
        assertion=assertion,
        passed=passed,
        message=msg,
        actual_value=response.status_code
    )
```

---

## Dependencies

```txt
jsonpath-ng>=1.6.0      # JSON path extraction (already needed for variable capture)
jsonschema>=4.20.0      # Schema validation
```

---

## TUI Enhancements

### Enhanced Response Viewer

Show assertion results clearly:

```
┌─ Response: Get user ───────────────────────────┐
│ Status: 200 OK                     Time: 234ms │
│                                                │
│ Assertions:                                    │
│ ✓ Status code is 200                           │
│ ✓ $.user.id equals 123                         │
│ ✓ $.user.email contains "@example.com"         │
│ ✗ $.user.role: "user" (expected "admin")       │
│ ✓ Response time: 234ms (max 500ms)             │
│                                                │
│ Body:                                          │
│ {                                              │
│   "user": {                                    │
│     "id": 123,                                 │
│     "email": "user@example.com",               │
│     "role": "user"                             │
│   }                                            │
│ }                                              │
│                                                │
│ [Enter] close [r] re-run [e] edit             │
└────────────────────────────────────────────────┘
```

### Request Builder

Add assertions section to request builder:

```
┌─ New API Request ──────────────────────────────┐
│ ...                                            │
│                                                │
│ Assertions:                                    │
│ ┌────────────────────────────────────────────┐ │
│ │ ✓ Status: 200                              │ │
│ │ ✓ JSONPath: $.user.id = 123                │ │
│ │ ✓ Response time: max 500ms                 │ │
│ └────────────────────────────────────────────┘ │
│ [+ Add assertion]                              │
│                                                │
│ [Enter] save [Ctrl-T] test now [Esc] cancel   │
└────────────────────────────────────────────────┘
```

---

## Why Deferred

These assertion features were removed from Phase 7 Enhancements to:

1. **Keep scope focused** - Authentication, environments, and chaining are the core value
2. **Avoid bloat** - Assertions add complexity that may not be needed for most use cases
3. **Faster delivery** - Removing assertions significantly reduces implementation time
4. **User validation** - Can assess if assertions are needed based on actual usage

---

## Future Considerations

If implementing in the future, consider:

1. **Alternative approach**: Simple pass/fail indicator based on `expected_status` (already exists in Phase 7)
2. **Manual validation**: Users can visually inspect JSON responses in the viewer
3. **External validation**: Use dedicated API testing tools (Postman, Insomnia) for complex assertions
4. **Incremental addition**: Start with just JSONPath assertions if basic validation is needed

---

## Related Features

Also deferred from original Phase 7 Enhancements scope:

- OAuth 2.0 authentication (complex token refresh)
- Keyring credential storage (simpler to use environment variables)
- Mock server integration
- Response caching
- Request collections/folders

These may be addressed in future phases based on user needs.
