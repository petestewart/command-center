# Phase 7 Enhancements: Advanced API Testing Features

## Overview

**Duration:** 2-3 weeks
**Prerequisites:** Phase 7 must be completed

This document outlines advanced API testing features that were deferred from the initial Phase 7 implementation. These features add authentication support, advanced assertions, and workflow automation.

---

## Deferred Features

### 1. Authentication Support

#### 1.1 Basic Authentication

Add support for HTTP Basic Auth:

```yaml
requests:
  - name: "Protected endpoint"
    method: GET
    url: "{{base_url}}/api/protected"
    auth:
      type: basic
      username: "{{api_username}}"
      password: "{{api_password}}"
```

#### 1.2 Bearer Token Authentication

Support for Bearer token authentication:

```yaml
requests:
  - name: "API with Bearer token"
    method: GET
    url: "{{base_url}}/api/users"
    auth:
      type: bearer
      token: "{{api_token}}"
```

**Alternative:** Can be achieved with headers in Phase 7:
```yaml
headers:
  Authorization: "Bearer {{api_token}}"
```

#### 1.3 OAuth 2.0 Support

Support for OAuth 2.0 flows:

```yaml
auth:
  type: oauth2
  grant_type: client_credentials  # or authorization_code, password
  token_url: "{{auth_server}}/oauth/token"
  client_id: "{{client_id}}"
  client_secret: "{{client_secret}}"
  scope: "read write"
```

**Implementation notes:**
- Store tokens in secure storage (keyring)
- Auto-refresh expired tokens
- Handle token expiration gracefully

#### 1.4 API Key Authentication

Support for API key authentication (query param or header):

```yaml
requests:
  - name: "API with key in header"
    method: GET
    url: "{{base_url}}/api/data"
    auth:
      type: api_key
      location: header  # or query
      key_name: "X-API-Key"
      key_value: "{{api_key}}"
```

### 2. Advanced Assertions

#### 2.1 JSON Path Assertions

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

#### 2.2 Schema Validation

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

#### 2.3 Regular Expression Matching

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

#### 2.4 Response Time Assertions

Assert on response time:

```yaml
assertions:
  - type: response_time
    max_ms: 500
    message: "API should respond within 500ms"
```

### 3. Request Chaining

Use response data from one request in subsequent requests:

```yaml
requests:
  - name: "Login"
    method: POST
    url: "{{base_url}}/auth/login"
    body: |
      {
        "username": "{{username}}",
        "password": "{{password}}"
      }
    capture:
      - name: auth_token
        jsonpath: "$.token"
      - name: user_id
        jsonpath: "$.user.id"

  - name: "Get user data"
    method: GET
    url: "{{base_url}}/api/users/{{user_id}}"
    headers:
      Authorization: "Bearer {{auth_token}}"
    depends_on: "Login"  # Must run after Login succeeds
```

**TUI Support:**
- Run request chain with single command
- Show progress through chain
- Stop on first failure
- Display captured variables

### 4. Environment Management

Support for multiple environments (dev, staging, prod):

```yaml
# ~/.ccc-control/<branch>/api-environments.yaml

environments:
  dev:
    base_url: "http://localhost:3000"
    api_key: "dev-key-123"
    db_name: "app_dev"

  staging:
    base_url: "https://staging.example.com"
    api_key: "staging-key-456"
    db_name: "app_staging"

  prod:
    base_url: "https://api.example.com"
    api_key: "{{PROD_API_KEY}}"  # From env var
    db_name: "app_production"
```

**CLI commands:**
```bash
# Switch environment
ccc api env <branch> <environment>

# List environments
ccc api env <branch> --list

# Show current environment
ccc api env <branch> --show

# Run request in specific environment
ccc api run <branch> <request> --env staging
```

**TUI:**
- Environment indicator in header
- Quick switch between environments
- Color coding (dev=green, staging=yellow, prod=red)

### 5. Mock Server Integration

Integration with mock servers for testing:

```yaml
requests:
  - name: "Test with mock"
    method: POST
    url: "{{base_url}}/api/upload"
    mock:
      enabled: true
      response:
        status: 200
        body: |
          {
            "success": true,
            "id": "mock-123"
          }
        delay_ms: 100
```

**Features:**
- Record actual responses and replay as mocks
- Override specific requests with mocks
- Simulate network delays and errors
- Useful for offline development

### 6. Response Caching

Cache responses for faster iteration:

```yaml
config:
  cache:
    enabled: true
    ttl_seconds: 300
    invalidate_on_change: true
```

**Behavior:**
- Cache GET requests by default
- Display cache indicator in response viewer
- Manual cache invalidation
- Useful for expensive API calls during testing

### 7. Request Collections & Folders

Organize requests into folders:

```yaml
collections:
  - name: "User Management"
    folder: "users"
    requests:
      - "Get user"
      - "Create user"
      - "Update user"
      - "Delete user"

  - name: "Authentication"
    folder: "auth"
    requests:
      - "Login"
      - "Logout"
      - "Refresh token"
```

**TUI:**
- Tree view of collections
- Expand/collapse folders
- Run all requests in a collection
- Export/import collections

---

## Implementation Priority

**High Priority (Week 1-2):**
1. Authentication support (Basic, Bearer, API Key)
2. JSON path assertions
3. Response time assertions

**Medium Priority (Week 2-3):**
4. Environment management
5. Request chaining
6. Schema validation

**Low Priority (Future):**
7. OAuth 2.0 support
8. Mock server integration
9. Response caching
10. Request collections

---

## Technical Dependencies

### New Libraries

```txt
# requirements.txt additions
jsonpath-ng>=1.6.0      # JSON path assertions
jsonschema>=4.20.0      # Schema validation
keyring>=24.3.0         # Secure credential storage
```

### Data Structure Updates

```python
# Extend ApiRequest dataclass
@dataclass
class ApiRequest:
    # ... existing fields ...

    # New fields for enhancements
    auth: Optional[AuthConfig] = None
    assertions: List[Assertion] = field(default_factory=list)
    capture: List[CaptureRule] = field(default_factory=list)
    depends_on: Optional[str] = None
    mock: Optional[MockConfig] = None

@dataclass
class AuthConfig:
    type: str  # "basic", "bearer", "oauth2", "api_key"
    # Type-specific fields stored as dict
    config: Dict[str, Any]

@dataclass
class Assertion:
    type: str  # "status", "jsonpath", "schema", "regex", "response_time"
    config: Dict[str, Any]

@dataclass
class CaptureRule:
    name: str  # Variable name to capture to
    jsonpath: str  # JSON path to extract

@dataclass
class MockConfig:
    enabled: bool
    response: MockResponse
    delay_ms: int = 0
```

---

## Success Criteria

### Authentication
✅ Supports Basic Auth, Bearer tokens, and API keys
✅ Credentials stored securely
✅ OAuth 2.0 token refresh works automatically

### Advanced Assertions
✅ JSON path assertions work correctly
✅ Schema validation catches invalid responses
✅ Response time assertions detect slow APIs
✅ Assertion results clearly displayed in TUI

### Request Chaining
✅ Can capture values from responses
✅ Captured values available in subsequent requests
✅ Chain execution stops on first failure
✅ Chain progress visible in TUI

### Environment Management
✅ Can define and switch between environments
✅ Variables correctly substituted per environment
✅ Environment clearly indicated in TUI
✅ Prevents accidental prod usage (confirmation)

---

## Documentation

Required documentation for enhancements:

1. **AUTHENTICATION.md** - Setting up authentication
2. **ADVANCED_ASSERTIONS.md** - Using JSON path and schema validation
3. **REQUEST_CHAINING.md** - Building request workflows
4. **ENVIRONMENTS.md** - Managing multiple environments
5. **MOCKING.md** - Using mock responses

---

## Migration from Phase 7

All Phase 7 features remain backward compatible. Users can:
- Continue using requests without authentication
- Opt-in to new features as needed
- Upgrade existing requests incrementally

No breaking changes to YAML format - new fields are optional.

---

## Next Steps After Enhancements

Once enhancements are complete, consider:
- GraphQL query support
- WebSocket testing
- gRPC testing
- Load testing integration
- CI/CD integration (run requests in pipeline)
- Postman/Insomnia collection import
