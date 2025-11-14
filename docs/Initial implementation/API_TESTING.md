# API Testing Guide

Test API endpoints without leaving Command Center using the integrated HTTP request tool.

---

## Overview

Phase 7 adds comprehensive API testing capabilities to Command Center, allowing you to:
- Save and organize HTTP requests per branch
- Execute requests and view formatted responses
- Track request history
- Use variables for environment configuration
- Validate responses with status code assertions

---

## Getting Started

### Prerequisites

API testing is automatically available in Phase 7. No additional setup required.

### Quick Start

1. **Open the TUI**: `ccc tui`
2. **Select a branch**: Navigate to your branch
3. **Press 'a'**: Opens the API Request Builder
4. **Create a request**:
   - Name: "Get Users"
   - Method: GET
   - URL: `http://localhost:3000/api/users`
   - Expected Status: 200
5. **Press Ctrl+S**: Saves the request
6. **Press Enter**: Executes the request (from API panel)
7. **View response**: Response viewer shows status, headers, and body

---

## Using the TUI

### Main View

Press **'a'** from the branch detail view to open the Request Builder.

### API Request Panel

Located below the Test Status panel, shows all saved requests for the current branch.

```
┌─ API Requests ─────────────────────────────┐
│ GET     Get Users           200  2m         │
│ POST    Create User         201  5m         │
│ DELETE  Delete User         204  Never      │
│                                             │
│ [Enter] run [n]ew [e]dit [d]elete          │
└─────────────────────────────────────────────┘
```

**Keyboard Shortcuts:**
- `Enter` - Execute selected request
- `n` - Create new request
- `e` - Edit selected request
- `d` - Delete selected request
- `j/k` - Navigate up/down

### Request Builder

Create or edit API requests with all configuration options.

**Fields:**
- **Name**: Request identifier (required, cannot be renamed)
- **Method**: HTTP method dropdown (GET/POST/PUT/PATCH/DELETE)
- **URL**: Request URL (supports variable substitution)
- **Headers**: Key-value pairs, one per line (`Key: Value` format)
- **Body**: Request body (JSON, text, form data, etc.)
- **Expected Status**: Expected HTTP status code for assertions

**Keyboard Shortcuts:**
- `Ctrl+S` - Save request
- `Ctrl+T` - Test request immediately
- `Esc` - Cancel

**Example:**
```
Name: Create User
Method: POST
URL: {{base_url}}/api/users
Headers:
Content-Type: application/json
Accept: application/json

Body:
{
  "name": "John Doe",
  "email": "john@example.com"
}

Expected Status: 201
```

### Response Viewer

View detailed response information after executing a request.

**Displays:**
- **Status**: Color-coded status code (green=2xx, yellow=3xx, orange=4xx, red=5xx)
- **Time**: Request duration in milliseconds
- **Headers**: All response headers
- **Body**: Formatted response body (JSON auto-formatted)
- **Assertions**: ✓ or ✗ for expected status match

**Keyboard Shortcuts:**
- `Enter` - Close viewer
- `r` - Re-run the request

**Example:**
```
┌─ Response: Get Users ──────────────────────┐
│ ✓ 200 OK                       Time: 234ms │
│                                             │
│ ✓ Status matches expected (200)            │
│                                             │
│ Headers:                                    │
│ Content-Type: application/json              │
│ X-Request-ID: abc123                        │
│                                             │
│ Body:                                       │
│ {                                           │
│   "users": [                                │
│     {"id": 1, "name": "John"},              │
│     {"id": 2, "name": "Jane"}               │
│   ]                                         │
│ }                                           │
└─────────────────────────────────────────────┘
```

---

## Using the CLI

### Managing Requests

```bash
# Create a new request (interactive)
ccc api add feature/api-testing "Get Users"

# Create with options
ccc api add feature/api-testing "Create User" \
  --method POST \
  --url "http://localhost:3000/api/users" \
  --header "Content-Type: application/json" \
  --body '{"name":"John"}' \
  --expected-status 201

# List all requests
ccc api list feature/api-testing

# Execute a request
ccc api run feature/api-testing "Get Users"

# Delete a request
ccc api delete feature/api-testing "Get Users"
```

### Managing Variables

```bash
# Set a variable
ccc api var set feature/api-testing base_url "http://localhost:3000"

# List variables
ccc api var list feature/api-testing

# Delete a variable
ccc api var delete feature/api-testing base_url
```

### Viewing History

```bash
# Show last 10 executions
ccc api history feature/api-testing

# Show last 20 executions
ccc api history feature/api-testing --limit 20

# Clear history
ccc api history feature/api-testing --clear
```

---

## Variables

Variables allow you to parameterize requests for different environments or configurations.

### Using Variables

Variables are defined per-branch and use `{{variable_name}}` syntax:

```yaml
variables:
  base_url: "http://localhost:3000"
  api_token: "dev-token-123"
  user_id: "42"

requests:
  - name: "Get User"
    url: "{{base_url}}/api/users/{{user_id}}"
    headers:
      Authorization: "Bearer {{api_token}}"
```

### Variable Substitution

Variables are substituted in:
- URLs
- Header values
- Request body

**Example:**
```
URL: {{base_url}}/api/users/{{user_id}}
↓
URL: http://localhost:3000/api/users/42
```

### Sensitive Variables

Variables containing these keywords are masked in the CLI output:
- `token`
- `key`
- `secret`
- `password`

```bash
$ ccc api var list feature/api-testing

Variables (3):
  base_url: http://localhost:3000
  api_token: dev-***
  user_id: 42
```

---

## Request History

Every request execution is recorded in history:

```bash
$ ccc api history feature/api-testing

API Request History (10 recent):
Time      Request       Method  Status  Result
2m ago    Get Users     GET     200     ✓ Success
5m ago    Create User   POST    201     ✓ Success
10m ago   Get Users     GET     500     ✗ Error
```

History includes:
- Execution timestamp
- Request name
- HTTP method
- Response status code
- Success/failure indicator
- Error message (if failed)

**Configuration:**
History is limited to 50 entries by default. Configure in `~/.ccc-control/config.yaml`:

```yaml
api_max_history_entries: 100
```

---

## Status Code Assertions

Set `expected_status` to validate responses:

```yaml
requests:
  - name: "Valid Request"
    url: "{{base_url}}/api/users"
    expected_status: 200  # Expects 2xx

  - name: "Not Found"
    url: "{{base_url}}/api/users/999"
    expected_status: 404  # Expects 4xx
```

**Response Viewer:**
- ✓ Green checkmark if status matches
- ✗ Red X if status doesn't match

---

## HTTP Methods

All common HTTP methods are supported:

| Method | Use Case | Body Allowed |
|--------|----------|--------------|
| GET    | Retrieve data | No |
| POST   | Create resources | Yes |
| PUT    | Update (replace) resources | Yes |
| PATCH  | Update (modify) resources | Yes |
| DELETE | Remove resources | No |
| HEAD   | Get headers only | No |
| OPTIONS | Get supported methods | No |

---

## JSON Formatting

JSON responses are automatically detected and formatted for readability:

**Raw Response:**
```
{"users":[{"id":1,"name":"John"},{"id":2,"name":"Jane"}]}
```

**Formatted Display:**
```json
{
  "users": [
    {
      "id": 1,
      "name": "John"
    },
    {
      "id": 2,
      "name": "Jane"
    }
  ]
}
```

---

## Configuration

API testing settings in `~/.ccc-control/config.yaml`:

```yaml
# API Testing settings
api_default_timeout: 30              # Request timeout (seconds)
api_follow_redirects: true           # Follow HTTP redirects
api_max_history_entries: 50          # History entry limit
api_verify_ssl: true                 # Verify SSL certificates
```

---

## Best Practices

### Organize Requests

Group related requests by feature:
- `Get User`
- `Create User`
- `Update User`
- `Delete User`

### Use Descriptive Names

Good: `"Get user by ID"`, `"Create user with valid data"`, `"Delete non-existent user"`

Bad: `"Test 1"`, `"Request 2"`, `"API Call"`

### Set Expected Status

Always set `expected_status` to catch regressions:

```yaml
- name: "Valid Request"
  expected_status: 200

- name: "Invalid Schema"
  expected_status: 400
```

### Use Variables

Keep requests portable with variables:

```yaml
variables:
  base_url: "http://localhost:3000"  # Change once, affects all requests
```

### Document Headers

Add comments to complex requests:

```
Headers:
Content-Type: application/json
X-API-Version: v2
X-Request-ID: test-123
```

---

## Troubleshooting

### Request Times Out

**Issue:** Request exceeds timeout limit

**Solution:**
```yaml
# Increase timeout in config.yaml
api_default_timeout: 60
```

### SSL Certificate Error

**Issue:** Self-signed certificates fail verification

**Solution:**
```yaml
# Disable SSL verification (development only!)
api_verify_ssl: false
```

### Variable Not Substituted

**Issue:** `{{variable}}` appears in URL instead of value

**Solution:**
1. Check variable is defined: `ccc api var list <branch>`
2. Ensure correct spelling and case
3. Variable names are case-sensitive

### JSON Not Formatted

**Issue:** Response body not pretty-printed

**Cause:** Response `Content-Type` header is not `application/json`

**Solution:** Set correct header in API server response

---

## See Also

- [REQUEST_LIBRARY.md](REQUEST_LIBRARY.md) - Managing saved requests and variables
- [PHASE_7_ENHANCEMENTS.md](PHASE_7_ENHANCEMENTS.md) - Advanced features (authentication, assertions)
- [PHASE_7.md](PHASE_7.md) - Implementation details

---

## Examples

### Testing a REST API

```bash
# Set up environment
ccc api var set feature/api base_url "http://localhost:3000"

# Create requests via TUI
# Press 'a' and create:

# 1. Get all users
Name: Get Users
Method: GET
URL: {{base_url}}/api/users
Expected Status: 200

# 2. Get specific user
Name: Get User By ID
Method: GET
URL: {{base_url}}/api/users/1
Expected Status: 200

# 3. Create user
Name: Create User
Method: POST
URL: {{base_url}}/api/users
Headers:
Content-Type: application/json
Body:
{
  "name": "John Doe",
  "email": "john@example.com"
}
Expected Status: 201

# 4. Update user
Name: Update User
Method: PUT
URL: {{base_url}}/api/users/1
Headers:
Content-Type: application/json
Body:
{
  "name": "Jane Doe"
}
Expected Status: 200

# 5. Delete user
Name: Delete User
Method: DELETE
URL: {{base_url}}/api/users/1
Expected Status: 204
```

### Testing Error Cases

```yaml
# Test invalid data
- name: "Create User - Invalid Email"
  method: POST
  url: "{{base_url}}/api/users"
  body: '{"email": "not-an-email"}'
  expected_status: 400

# Test missing auth
- name: "Protected Endpoint - No Auth"
  method: GET
  url: "{{base_url}}/api/admin"
  expected_status: 401

# Test not found
- name: "Get Non-existent User"
  method: GET
  url: "{{base_url}}/api/users/99999"
  expected_status: 404
```
