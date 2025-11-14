# Phase 7: API Testing Tools - Implementation Plan

## Overview

**Duration:** 2 weeks
**Goal:** Test API endpoints without leaving Command Center

Phase 7 adds integrated API testing capabilities, allowing developers to save, execute, and validate HTTP requests directly from the TUI.

**Note:** Advanced features (authentication, JSON path assertions) are deferred to Phase 7 Enhancements. See `PHASE_7_ENHANCEMENTS.md`.

---

## Goal

Test API endpoints without leaving Command Center

## Key Features

### 7.1 Request Library

**Storage format:** `~/.ccc-control/<branch-name>/api-requests.yaml`

```yaml
# Example saved requests
requests:
  - name: "Valid bulk upload"
    method: POST
    url: "{{base_url}}/api/bulk-upload"
    headers:
      Content-Type: application/json
    body: |
      {
        "items": [
          {"id": 1, "value": "test"}
        ]
      }
    expected_status: 200
    timeout: 30

  - name: "Get user by ID"
    method: GET
    url: "{{base_url}}/api/users/{{user_id}}"
    headers:
      Accept: application/json
    expected_status: 200

  - name: "Invalid schema"
    method: POST
    url: "{{base_url}}/api/bulk-upload"
    body: |
      {
        "invalid": "data"
      }
    expected_status: 400

# Variables for this branch
variables:
  base_url: "http://localhost:3000"
  user_id: "123"
```

### 7.2 Variable Substitution

Requests support variable substitution using `{{variable_name}}` syntax:
- Variables can be defined per-branch in `api-requests.yaml`
- Substitution works in URLs, headers, and body
- Variables can be edited via CLI or TUI

**Example:**
```yaml
variables:
  api_host: "http://localhost:3000"
  api_token: "test-token-123"
  user_id: "42"

requests:
  - name: "Get user"
    url: "{{api_host}}/users/{{user_id}}"
    headers:
      Authorization: "Bearer {{api_token}}"
```

### 7.3 Request Builder

```
┌─ New API Request ──────────────────────────────┐
│ Name: Valid bulk upload                        │
│                                                │
│ Method: [POST ▼]  URL: {{base_url}}/api/      │
│                        bulk-upload             │
│                                                │
│ Headers:                                       │
│ ┌────────────────────────────────────────────┐ │
│ │ Content-Type: application/json             │ │
│ │ Accept: application/json                   │ │
│ └────────────────────────────────────────────┘ │
│ [+ Add header]                                 │
│                                                │
│ Body:                                          │
│ ┌────────────────────────────────────────────┐ │
│ │ {                                          │ │
│ │   "items": [{"id": 1}]                    │ │
│ │ }                                          │ │
│ └────────────────────────────────────────────┘ │
│                                                │
│ Expected Status: [200]  Timeout: [30]s         │
│                                                │
│ [Enter] save [Ctrl-T] test now [Esc] cancel   │
└────────────────────────────────────────────────┘
```

### 7.4 Response Viewer

```
┌─ Response: Valid bulk upload ──────────────────┐
│ Status: 200 OK                     Time: 234ms │
│                                                │
│ Headers:                                       │
│ Content-Type: application/json                 │
│ X-Request-ID: abc123                           │
│ Content-Length: 42                             │
│                                                │
│ Body:                                          │
│ {                                              │
│   "success": true,                             │
│   "processed": 1                               │
│ }                                              │
│                                                │
│ ✓ Status matches expected (200)                │
│                                                │
│ [Enter] close [s] save [r] re-run [e] edit    │
└────────────────────────────────────────────────┘
```

### 7.5 Request History

**Storage:** `~/.ccc-control/<branch-name>/api-history.yaml`

Tracks execution history:
- Request name and timestamp
- Response status and time
- Success/failure indicator
- Limited to last 50 executions (configurable)

## CLI Commands

```bash
# Request management
ccc api add <branch> <name>              # Create new request (interactive)
ccc api list <branch>                    # List all saved requests
ccc api run <branch> <request-name>      # Execute a saved request
ccc api delete <branch> <request-name>   # Delete a request
ccc api edit <branch> <request-name>     # Edit a request (interactive)

# Variables
ccc api var set <branch> <key> <value>   # Set a variable
ccc api var list <branch>                # List all variables
ccc api var delete <branch> <key>        # Delete a variable

# History
ccc api history <branch>                 # Show execution history
ccc api history <branch> --clear         # Clear history

# Import/Export
ccc api export <branch> <file>           # Export requests to YAML
ccc api import <branch> <file>           # Import requests from YAML
```

## TUI Integration

### Keyboard Shortcuts

**Main view (branch detail):**
- `a` - Open API Request Builder

**API Request List:**
- `Enter` - Execute selected request
- `e` - Edit request
- `d` - Delete request
- `n` - New request
- `v` - Manage variables

**Response Viewer:**
- `Enter` - Close
- `s` - Save (if ad-hoc test)
- `r` - Re-run request
- `e` - Edit request

### API Request Panel

Added to branch detail view below Test Status:

```
┌─ API Requests: feature/api-testing ────────────┐
│ POST  Valid bulk upload              200  2m   │
│ GET   Get user by ID                 200  5m   │
│ POST  Invalid schema                 400  10m  │
│                                                │
│ [Enter] run [n]ew [e]dit [d]elete [v]ars      │
└────────────────────────────────────────────────┘
```

## Deliverables

✅ Request library storage (YAML)
✅ Variable substitution support
✅ Request builder UI
✅ Execute requests with `requests` library
✅ Response viewer with JSON formatting
✅ Request history tracking
✅ Status code assertions
✅ CLI commands for all operations
✅ TUI integration with keyboard shortcuts

## Out of Scope (See PHASE_7_ENHANCEMENTS.md)

❌ Authentication (Basic Auth, Bearer tokens, OAuth)
❌ Advanced assertions (JSON path, regex, schema validation)
❌ Request chaining (use response from one request in another)
❌ Environment management (dev/staging/prod)
❌ Response caching
❌ Mock server integration

## Documentation

1. **API_TESTING.md** - Using API testing features
2. **REQUEST_LIBRARY.md** - Managing saved requests and variables
