# Request Library Management

Organize, store, and share API requests with Command Center's request library.

---

## Overview

The request library stores all API requests per branch in YAML format, making them:
- **Version controlled**: Commit with your code
- **Shareable**: Team members can use the same requests
- **Portable**: Export/import between branches

---

## Storage Format

Requests are stored in `~/.ccc-control/<branch-name>/api-requests.yaml`:

```yaml
requests:
  - name: "Get Users"
    method: GET
    url: "{{base_url}}/api/users"
    headers:
      Accept: application/json
    expected_status: 200
    timeout: 30
    follow_redirects: true
    created_at: "2025-11-12T10:30:00"
    last_executed: "2025-11-12T14:45:00"

  - name: "Create User"
    method: POST
    url: "{{base_url}}/api/users"
    headers:
      Content-Type: application/json
    body: |
      {
        "name": "John Doe",
        "email": "john@example.com"
      }
    expected_status: 201

variables:
  base_url: "http://localhost:3000"
  api_version: "v2"
```

---

## Request Structure

### Required Fields

```yaml
name: "Request Name"        # Unique identifier
method: GET                 # HTTP method
url: "http://example.com"   # Request URL
```

### Optional Fields

```yaml
headers:                    # HTTP headers
  Content-Type: application/json
  Accept: application/json

body: |                     # Request body (POST/PUT/PATCH)
  {
    "key": "value"
  }

expected_status: 200        # Expected status code for assertions
timeout: 30                 # Request timeout (seconds)
follow_redirects: true      # Follow HTTP redirects

# Metadata (auto-generated)
created_at: "2025-11-12T10:30:00"
last_executed: "2025-11-12T14:45:00"
```

---

## Managing Requests

### Via CLI

```bash
# Create
ccc api add <branch> "<name>" --url "..." --method POST

# List
ccc api list <branch>

# Edit (manually edit YAML file)
# Or use TUI: ccc tui, select branch, press 'a', edit request

# Delete
ccc api delete <branch> "<name>"
```

### Via TUI

```
1. Launch TUI: ccc tui
2. Select branch
3. Navigate to API Requests panel
4. Press 'n' for new, 'e' to edit, 'd' to delete
```

### Manual Editing

You can directly edit `~/.ccc-control/<branch>/api-requests.yaml`:

```bash
# Open in editor
vim ~/.ccc-control/feature-api-testing/api-requests.yaml

# Edit and save
# Requests are reloaded automatically in TUI
```

---

## Variables

Variables enable parameterized requests that adapt to different environments.

### Defining Variables

**Via CLI:**
```bash
ccc api var set <branch> <key> <value>
ccc api var set feature/api base_url "http://localhost:3000"
ccc api var set feature/api api_token "dev-token-123"
```

**Via YAML:**
```yaml
variables:
  base_url: "http://localhost:3000"
  api_token: "dev-token-123"
  api_version: "v2"
  user_id: "42"
```

### Using Variables

Use `{{variable_name}}` syntax anywhere in requests:

**URLs:**
```yaml
url: "{{base_url}}/api/{{api_version}}/users/{{user_id}}"
# Becomes: http://localhost:3000/api/v2/users/42
```

**Headers:**
```yaml
headers:
  Authorization: "Bearer {{api_token}}"
  X-API-Version: "{{api_version}}"
```

**Body:**
```yaml
body: |
  {
    "endpoint": "{{base_url}}",
    "user_id": {{user_id}}
  }
```

### Variable Scope

Variables are per-branch:
- `feature/api-v1` has its own variables
- `feature/api-v2` has different variables
- Useful for testing different API versions

### Environment-Specific Variables

Use different variable values for dev/staging/prod:

**Development:**
```yaml
variables:
  base_url: "http://localhost:3000"
  db_name: "app_dev"
```

**Staging:**
```yaml
variables:
  base_url: "https://staging.example.com"
  db_name: "app_staging"
```

**Production:**
```yaml
variables:
  base_url: "https://api.example.com"
  db_name: "app_production"
```

---

## Import/Export

### Exporting Requests

Save requests to a file for sharing or backup:

```bash
# Export to file
ccc api export <branch> requests.yaml

# Share with team
git add requests.yaml
git commit -m "Add API test requests"
```

### Importing Requests

Load requests from a file:

```bash
# Import (replace all)
ccc api import <branch> requests.yaml

# Import (merge with existing)
ccc api import <branch> requests.yaml --merge
```

**Merge Behavior:**
- Keeps existing requests if names don't conflict
- Overwrites variables with new values
- Useful for sharing request collections

---

## Request Organization

### Naming Conventions

**Pattern:** `<Action> <Resource> [- <Scenario>]`

**Examples:**
```
Get Users
Get User By ID
Create User - Valid Data
Create User - Invalid Email
Update User - Partial
Delete User - Non-existent
```

### Grouping Requests

While folders aren't supported yet (see [PHASE_7_ENHANCEMENTS.md](PHASE_7_ENHANCEMENTS.md)), use prefixes:

```yaml
requests:
  - name: "Auth - Login"
  - name: "Auth - Logout"
  - name: "Auth - Refresh Token"
  - name: "Users - Get All"
  - name: "Users - Get By ID"
  - name: "Users - Create"
```

Sort alphabetically in TUI for natural grouping.

### Test Scenarios

Document test cases in request names:

```yaml
- name: "Create User - Valid Data"
  expected_status: 201

- name: "Create User - Missing Email"
  expected_status: 400

- name: "Create User - Duplicate Email"
  expected_status: 409
```

---

## Sharing with Team

### Version Control

Commit request libraries with your code:

```bash
# Add to git
cd ~/.ccc-control/feature-api-testing
git add api-requests.yaml
git commit -m "Add API test requests for user endpoints"

# Or copy to project repo
cp ~/.ccc-control/feature-api-testing/api-requests.yaml \
   ~/project/tests/api-requests.yaml
git add tests/api-requests.yaml
```

### Team Workflow

1. **Developer A** creates requests in TUI
2. **Developer A** exports requests:
   ```bash
   ccc api export feature/api-v2 api-requests.yaml
   ```
3. **Developer A** commits to shared repo
4. **Developer B** pulls repo
5. **Developer B** imports requests:
   ```bash
   ccc api import feature/api-v2 api-requests.yaml --merge
   ```

### Repository Template

Create a template for new branches:

```bash
# Create template
mkdir -p ~/project/templates
ccc api export main ~/project/templates/api-requests-template.yaml

# Use for new branch
ccc create feature/new-feature
ccc api import feature/new-feature ~/project/templates/api-requests-template.yaml
```

---

## Request History

Execution history is separate from requests and stored in `api-history.yaml`.

### History Format

```yaml
history:
  - request_name: "Get Users"
    method: GET
    url: "http://localhost:3000/api/users"
    timestamp: "2025-11-12T14:45:00"
    response:
      status_code: 200
      reason: OK
      elapsed_ms: 234
      headers:
        Content-Type: application/json
      body: |
        {"users": [...]}
```

### History Limits

**Default:** 50 entries per branch

**Configure:**
```yaml
# ~/.ccc-control/config.yaml
api_max_history_entries: 100
```

### Clearing History

```bash
# Clear all history for branch
ccc api history <branch> --clear

# Or manually delete file
rm ~/.ccc-control/<branch>/api-history.yaml
```

---

## Advanced Patterns

### Common Headers Template

Define common headers in variables:

```yaml
variables:
  content_type_json: "application/json"
  accept_json: "application/json"
  user_agent: "Command-Center/0.1.0"

requests:
  - name: "Example"
    headers:
      Content-Type: "{{content_type_json}}"
      Accept: "{{accept_json}}"
      User-Agent: "{{user_agent}}"
```

### Dynamic URLs

Build URLs from components:

```yaml
variables:
  protocol: "https"
  domain: "api.example.com"
  api_version: "v2"
  resource: "users"

requests:
  - name: "Get Resource"
    url: "{{protocol}}://{{domain}}/{{api_version}}/{{resource}}"
    # Becomes: https://api.example.com/v2/users
```

### Request Templates

Create templates for common patterns:

**REST CRUD Template:**
```yaml
# GET /resource
- name: "Get All {{resource}}"
  method: GET
  url: "{{base_url}}/{{resource}}"

# GET /resource/:id
- name: "Get {{resource}} By ID"
  method: GET
  url: "{{base_url}}/{{resource}}/{{id}}"

# POST /resource
- name: "Create {{resource}}"
  method: POST
  url: "{{base_url}}/{{resource}}"
  body: "{}"

# PUT /resource/:id
- name: "Update {{resource}}"
  method: PUT
  url: "{{base_url}}/{{resource}}/{{id}}"
  body: "{}"

# DELETE /resource/:id
- name: "Delete {{resource}}"
  method: DELETE
  url: "{{base_url}}/{{resource}}/{{id}}"
```

---

## Troubleshooting

### Request Not Found

**Issue:** `ccc api run <branch> "Request Name"` says request not found

**Solutions:**
1. Check exact name: `ccc api list <branch>`
2. Names are case-sensitive
3. Check you're on the correct branch

### Variables Not Substituting

**Issue:** `{{variable}}` appears literally in request

**Solutions:**
1. Check variable exists: `ccc api var list <branch>`
2. Check spelling and case
3. Ensure variable is defined before request execution

### Invalid YAML

**Issue:** Requests file won't load

**Solutions:**
1. Validate YAML syntax: `yamllint ~/.ccc-control/<branch>/api-requests.yaml`
2. Check indentation (use spaces, not tabs)
3. Ensure multiline strings use `|` or `>` syntax

### Corrupted File

**Issue:** File is corrupted and won't load

**Recovery:**
```bash
# Restore from git if tracked
git checkout ~/.ccc-control/<branch>/api-requests.yaml

# Or recreate
rm ~/.ccc-control/<branch>/api-requests.yaml
ccc tui  # Creates new empty file
```

---

## Best Practices

### ✅ Do

- Use descriptive names
- Set `expected_status` for all requests
- Group related requests with prefixes
- Use variables for environment-specific values
- Commit request libraries to version control
- Document complex requests with comments (in YAML)

### ❌ Don't

- Hardcode credentials in requests (use variables)
- Use generic names like "Test 1"
- Store sensitive data in version control
- Manually edit auto-generated fields (`created_at`, `last_executed`)
- Delete variables that are referenced in requests

---

## See Also

- [API_TESTING.md](API_TESTING.md) - Using API testing features
- [PHASE_7.md](PHASE_7.md) - Implementation details
- [PHASE_7_ENHANCEMENTS.md](PHASE_7_ENHANCEMENTS.md) - Advanced features

---

## Examples

### Complete Request Library

```yaml
# ~/.ccc-control/feature-user-api/api-requests.yaml

# Variables for this branch
variables:
  base_url: "http://localhost:3000"
  api_version: "v2"
  test_user_id: "123"
  test_email: "test@example.com"

# User Management Requests
requests:
  # List operations
  - name: "Users - Get All"
    method: GET
    url: "{{base_url}}/api/{{api_version}}/users"
    headers:
      Accept: application/json
    expected_status: 200

  - name: "Users - Get By ID"
    method: GET
    url: "{{base_url}}/api/{{api_version}}/users/{{test_user_id}}"
    headers:
      Accept: application/json
    expected_status: 200

  # Create operations
  - name: "Users - Create Valid"
    method: POST
    url: "{{base_url}}/api/{{api_version}}/users"
    headers:
      Content-Type: application/json
    body: |
      {
        "name": "John Doe",
        "email": "{{test_email}}",
        "role": "user"
      }
    expected_status: 201

  - name: "Users - Create Invalid Email"
    method: POST
    url: "{{base_url}}/api/{{api_version}}/users"
    headers:
      Content-Type: application/json
    body: |
      {
        "name": "Jane Doe",
        "email": "not-an-email"
      }
    expected_status: 400

  # Update operations
  - name: "Users - Update Full"
    method: PUT
    url: "{{base_url}}/api/{{api_version}}/users/{{test_user_id}}"
    headers:
      Content-Type: application/json
    body: |
      {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "role": "admin"
      }
    expected_status: 200

  - name: "Users - Update Partial"
    method: PATCH
    url: "{{base_url}}/api/{{api_version}}/users/{{test_user_id}}"
    headers:
      Content-Type: application/json
    body: |
      {
        "name": "Jane Doe"
      }
    expected_status: 200

  # Delete operations
  - name: "Users - Delete"
    method: DELETE
    url: "{{base_url}}/api/{{api_version}}/users/{{test_user_id}}"
    expected_status: 204

  - name: "Users - Delete Non-existent"
    method: DELETE
    url: "{{base_url}}/api/{{api_version}}/users/99999"
    expected_status: 404
```
