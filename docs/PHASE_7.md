# Phase 7: API Testing Tools - Implementation Plan

## Overview

**Duration:** 2 weeks  
**Goal:** Test API endpoints without leaving Command Center

Phase 7 adds integrated API testing capabilities, allowing developers to save, execute, and validate HTTP requests directly from the TUI.

---

## Goal

Test API endpoints without leaving Command Center

## Key Features

### 7.1 Request Library

```yaml
# ~/.cc-control/<branch-name>/api-requests.yaml
requests:
  - name: "Valid bulk upload"
    method: POST
    url: http://localhost:3000/api/bulk-upload
    headers:
      Content-Type: application/json
    body: |
      {
        "items": [
          {"id": 1, "value": "test"}
        ]
      }
    expected_status: 200
    
  - name: "Invalid schema"
    method: POST
    url: http://localhost:3000/api/bulk-upload
    body: |
      {
        "invalid": "data"
      }
    expected_status: 400
```

### 7.2 Request Builder

```
┌─ New API Request ──────────────────────────────┐
│ Name: Valid bulk upload                        │
│                                                │
│ Method: [POST ▼]  URL: http://localhost:3000  │
│         /api/bulk-upload                       │
│                                                │
│ Headers:                                       │
│ Content-Type: application/json                 │
│ [+ Add header]                                 │
│                                                │
│ Body:                                          │
│ ┌────────────────────────────────────────────┐ │
│ │ {                                          │ │
│ │   "items": [{"id": 1}]                    │ │
│ │ }                                          │ │
│ └────────────────────────────────────────────┘ │
│                                                │
│ [Enter] save [Ctrl-T] test now [Esc] cancel   │
└────────────────────────────────────────────────┘
```

### 7.3 Response Viewer

```
┌─ Response: Valid bulk upload ──────────────────┐
│ Status: 200 OK                     Time: 234ms │
│                                                │
│ Headers:                                       │
│ Content-Type: application/json                 │
│ X-Request-ID: abc123                           │
│                                                │
│ Body:                                          │
│ {                                              │
│   "success": true,                             │
│   "processed": 1                               │
│ }                                              │
│                                                │
│ ✓ Status matches expected (200)                │
│                                                │
│ [Enter] close [s] save [e] edit request        │
└────────────────────────────────────────────────┘
```

## Deliverables

✅ Request library storage  
✅ Request builder UI  
✅ Execute requests  
✅ Response viewer with formatting  
✅ Request history  
✅ Assertions/validation  

## Documentation

1. **API_TESTING.md** - Using API testing features
2. **REQUEST_LIBRARY.md** - Managing saved requests
3. **ASSERTIONS.md** - Writing response assertions
