#!/usr/bin/env python3
"""Manual test for TODO parsing - runs without pytest."""

from ccc.multi_agent_manager import TodoParser

def test_all_formats():
    """Test all supported TODO formats."""
    parser = TodoParser()

    print("Testing TODO Parser...")
    print("=" * 60)

    # Test completed formats
    tests = [
        ("✓ Task completed", 1, True, False, "Checkmark completed"),
        ("✅ Task completed", 1, True, False, "Green checkmark completed"),
        ("[x] Task completed", 1, True, False, "[x] completed"),
        ("[X] Task completed", 1, True, False, "[X] uppercase completed"),
        ("* [x] Task completed", 1, True, False, "* [x] completed"),
        ("- [x] Task completed", 1, True, False, "- [x] completed"),

        # Pending formats
        ("○ Task pending", 1, False, False, "Circle pending"),
        ("⚬ Task pending", 1, False, False, "Dotted circle pending"),
        ("[ ] Task pending", 1, False, False, "[ ] pending"),
        ("* [ ] Task pending", 1, False, False, "* [ ] pending"),
        ("- [ ] Task pending", 1, False, False, "- [ ] pending"),

        # Blocked formats
        ("✗ Task blocked", 1, False, True, "X-mark blocked"),
        ("❌ Task blocked", 1, False, True, "Red X blocked"),
    ]

    passed = 0
    failed = 0

    for text, expected_count, expected_completed, expected_blocked, test_name in tests:
        todos = parser.parse_todo_list(text)

        if len(todos) == expected_count:
            if expected_count > 0:
                if todos[0].completed == expected_completed and todos[0].blocked == expected_blocked:
                    print(f"✓ {test_name}")
                    passed += 1
                else:
                    print(f"✗ {test_name}: Wrong status (completed={todos[0].completed}, blocked={todos[0].blocked})")
                    failed += 1
            else:
                print(f"✓ {test_name}")
                passed += 1
        else:
            print(f"✗ {test_name}: Expected {expected_count} todos, got {len(todos)}")
            failed += 1

    # Test empty/edge cases
    print()
    print("Edge Cases:")
    print("-" * 60)

    edge_cases = [
        ("", 0, "Empty string"),
        ("   \n\n   ", 0, "Whitespace only"),
        ("No TODOs here", 0, "No TODO markers"),
        ("✓ AB", 0, "Too short (filtered)"),
    ]

    for text, expected_count, test_name in edge_cases:
        todos = parser.parse_todo_list(text)
        if len(todos) == expected_count:
            print(f"✓ {test_name}")
            passed += 1
        else:
            print(f"✗ {test_name}: Expected {expected_count} todos, got {len(todos)}")
            failed += 1

    # Test multiple TODOs
    print()
    print("Multiple TODOs:")
    print("-" * 60)

    multi_text = """
✓ Completed task
[ ] Pending task
✗ Blocked task
[x] Another completed
○ Another pending
"""
    todos = parser.parse_todo_list(multi_text)
    if len(todos) == 5:
        print(f"✓ Multiple TODOs parsed correctly (count: {len(todos)})")
        passed += 1

        # Check each one
        checks = [
            (todos[0].completed == True, "First is completed"),
            (todos[1].completed == False and not todos[1].blocked, "Second is pending"),
            (todos[2].blocked == True, "Third is blocked"),
            (todos[3].completed == True, "Fourth is completed"),
            (todos[4].completed == False, "Fifth is pending"),
        ]

        for check, name in checks:
            if check:
                print(f"  ✓ {name}")
                passed += 1
            else:
                print(f"  ✗ {name}")
                failed += 1
    else:
        print(f"✗ Multiple TODOs: Expected 5 todos, got {len(todos)}")
        failed += 1

    # Test section extraction
    print()
    print("Section Extraction:")
    print("-" * 60)

    section_text = """
Some introduction text here.

## TODO

✓ First task
[ ] Second task

## Next Section

Some other content.
"""
    todos = parser.parse_todo_list(section_text)
    if len(todos) == 2:
        print(f"✓ TODO section extracted correctly")
        passed += 1
    else:
        print(f"✗ TODO section extraction: Expected 2 todos, got {len(todos)}")
        failed += 1

    # Summary
    print()
    print("=" * 60)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = test_all_formats()
    exit(0 if success else 1)
