# Command Center - Project Tasks

This file demonstrates the Tasks Pane functionality (Phase 4).

## Phase 4: Tasks Pane Implementation

- [x] Create TasksManager class
  - [x] Implement Task dataclass
  - [x] Implement markdown parsing
  - [x] Add file change detection
  - [x] Add caching mechanism
- [x] Create TasksPane widget
  - [x] Display tasks with proper formatting
  - [x] Support nested tasks with indentation
  - [x] Add completion statistics
- [x] Wire into app.py
  - [x] Initialize TasksManager
  - [x] Add toggle action
  - [x] Set up auto-refresh polling
- [ ] Testing
  - [x] Write unit tests for TasksManager
  - [ ] Write widget tests (manual verification)
  - [ ] Test with large files (500+ tasks)
  - [ ] Test error handling

## Phase 5: Layout Refactoring (Next)

- [ ] Implement dynamic pane toggling
- [ ] Add CSS for pane visibility
- [ ] Finalize keyboard shortcuts
- [ ] Test responsive layout

## Example Task Formatting

### Different nesting levels
- [ ] Level 0 task
  - [ ] Level 1 nested task
    - [ ] Level 2 double nested task
      - [ ] Level 3 triple nested task

### Mixed completion states
- [x] Completed parent task
  - [x] Completed child task
  - [ ] Pending child task
    - [x] Completed grandchild
- [ ] Pending parent task
  - [x] Some children are done
  - [ ] Others are still pending

### Various formats supported
* [ ] Asterisk bullet point
* [x] Completed with asterisk
- [ ] Dash bullet point
- [X] Completed with uppercase X (also works)

## Known Limitations (by design)

- Tasks are READ-ONLY from CCC (edit in editor)
- Auto-reload polls every 3 seconds
- Only standard markdown checkbox format supported
- No task editing/toggling from TUI (Phase 5 may add)
