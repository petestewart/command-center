# Phase 7 Enhancements: Advanced API Testing Features

## Overview

**Duration:** 2-3 weeks
**Prerequisites:** Phase 7 must be completed

This document outlines advanced API testing features that were deferred from the initial Phase 7 implementation. These features add authentication support, environment management, and request chaining for workflow automation.

**Note:** Advanced assertion features were removed from this phase to keep it focused. See `PHASE_7_FUTURE_ASSERTIONS.md` for deferred assertion features.

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

### 2. Request Chaining

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

### 3. Environment Management

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

---

## Implementation Priority

**Week 1: Authentication & Data Structures**
1. Extend ApiRequest with `auth` field
2. Implement Basic Auth support
3. Implement Bearer Token support
4. Implement API Key support (header and query param)
5. Update TUI request builder for authentication

**Week 2: Environment Management**
6. Create environment management module
7. Multi-environment variable system
8. CLI commands for environment management
9. TUI environment indicator and switcher
10. Production environment confirmation dialogs

**Week 3: Request Chaining & Polish**
11. Add `capture` and `depends_on` fields to ApiRequest
12. Implement request chain execution
13. Variable capture from responses using JSONPath
14. CLI command for running chains
15. Testing and documentation

**Deferred to Future:**
- Advanced assertions (see PHASE_7_FUTURE_ASSERTIONS.md)
- OAuth 2.0 support
- Keyring credential storage
- Mock server integration
- Response caching
- Request collections/folders

---

## Technical Dependencies

### New Libraries

```txt
# requirements.txt additions
jsonpath-ng>=1.6.0      # JSON path extraction for variable capture
```

**Note:** No other new dependencies required! We use the existing `requests` library for authentication and standard library features for environment management.

### Data Structure Updates

```python
# Extend ApiRequest dataclass
@dataclass
class ApiRequest:
    # ... existing Phase 7 fields ...

    # New fields for Phase 7 Enhancements (all optional for backward compatibility)
    auth: Optional[AuthConfig] = None
    capture: List[CaptureRule] = field(default_factory=list)
    depends_on: Optional[str] = None

@dataclass
class AuthConfig:
    """Authentication configuration."""
    type: str  # "basic", "bearer", "api_key"

    # Basic auth
    username: Optional[str] = None
    password: Optional[str] = None

    # Bearer token
    token: Optional[str] = None

    # API key
    key_name: Optional[str] = None
    key_value: Optional[str] = None
    location: Optional[str] = None  # "header" or "query"

@dataclass
class CaptureRule:
    """Rule for capturing values from response."""
    name: str  # Variable name to capture to
    jsonpath: str  # JSON path to extract from response

@dataclass
class Environment:
    """An environment with its variables."""
    name: str
    variables: Dict[str, str]

@dataclass
class EnvironmentStore:
    """Stores multiple environments and tracks current selection."""
    current_environment: str = "dev"
    environments: Dict[str, Environment] = field(default_factory=dict)
```

---

## Success Criteria

### Authentication
✅ Supports Basic Auth (username/password)
✅ Supports Bearer tokens (Authorization header)
✅ Supports API keys (header or query parameter)
✅ Auth configuration supports variable substitution
✅ Auth integrates with existing request execution

### Environment Management
✅ Can define multiple environments (dev, staging, prod)
✅ Can switch between environments via CLI and TUI
✅ Variables correctly substituted per environment
✅ Environment variables support shell env var references
✅ Environment clearly indicated in TUI
✅ Production environment requires confirmation
✅ Environment files are .gitignore'd

### Request Chaining
✅ Can capture values from JSON responses using JSONPath
✅ Captured values available in subsequent requests
✅ Can define request dependencies using `depends_on`
✅ Chain execution stops on first failure
✅ Chain execution order determined by dependencies
✅ Circular dependencies detected and reported

### Backward Compatibility
✅ All existing Phase 7 requests work without modification
✅ New fields are optional with sensible defaults
✅ YAML format remains compatible

---

## Documentation

Documentation updates required:

1. Update **API_TESTING.md** with authentication examples
2. Add **ENVIRONMENTS.md** - Managing multiple environments
3. Add **REQUEST_CHAINING.md** - Building request workflows
4. Update inline help for new CLI commands

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
- Advanced assertions (see PHASE_7_FUTURE_ASSERTIONS.md)
- OAuth 2.0 authentication with token refresh
- Keyring integration for secure credential storage
- GraphQL query support
- WebSocket testing
- gRPC testing
- Load testing integration
- CI/CD integration (run requests in pipeline)
- Postman/Insomnia collection import
