"""
Command Center CLI - Command routing and handlers
"""

import sys
import subprocess
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from ccc import __version__
from ccc.config import load_config, init_config
from ccc.ticket import Ticket, TicketRegistry, create_ticket
from ccc.session import TmuxSessionManager, check_tmux_installed, get_tmux_version
from ccc.status import (
    init_status_file,
    read_agent_status,
    update_status as update_status_file,
)
from ccc.build_status import (
    init_build_status,
    read_build_status,
    update_build_status,
    format_build_status,
)
from ccc.test_status import (
    init_test_status,
    read_test_status,
    update_test_status,
    format_test_status,
    parse_test_output,
    TestFailure,
)
from ccc.git_status import get_git_status, format_git_status
from ccc.utils import (
    get_tmux_session_name_from_branch,
    extract_display_id,
    format_time_ago,
    print_success,
    print_error,
    print_warning,
    print_info,
    confirm,
    expand_path,
)
from ccc.todo import (
    init_todos,
    add_todo,
    list_todos,
    update_todo_status,
    delete_todo,
    move_todo,
    assign_todo,
    set_blocked_by,
    update_todo_description,
)

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="Command Center")
@click.pass_context
def cli(ctx):
    """
    Command Center - Terminal-based mission control for managing development tickets.

    Manage multiple development tickets with AI agents, tmux sessions, and real-time status tracking.
    """
    # Ensure tmux is installed
    if not check_tmux_installed():
        print_error("tmux is not installed or not in PATH")
        print_info("Please install tmux:")
        print_info("  - Ubuntu/Debian: sudo apt install tmux")
        print_info("  - macOS: brew install tmux")
        print_info("  - Fedora: sudo dnf install tmux")
        sys.exit(1)


@cli.command()
@click.argument("branch_name")
@click.argument("title", required=False, default="")
@click.option("--worktree-path", "-w", help="Custom worktree path (overrides config)")
@click.option("--base-repo", help="Base repository path for creating worktree")
def create(
    branch_name: str, title: str, worktree_path: Optional[str], base_repo: Optional[str]
):
    """
    Create a new ticket with git worktree and tmux session using a branch name.

    BRANCH_NAME: Git branch name (e.g., "feature/IN-413-add-api", "bugfix/auth-fix")

    TITLE: Human-readable ticket title (optional, extracted from branch if not provided)

    \b
    Examples:
        ccc create feature/IN-413-add-api "Public API bulk uploads"
        ccc create bugfix/auth-fix "Fix authentication error"
        ccc create feature/new-dashboard
    """
    # Load config
    config = load_config()

    # Check if ticket already exists
    registry = TicketRegistry()
    if registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' already exists in registry")
        print_info(f"Use 'ccc delete {branch_name}' to remove it first")
        sys.exit(1)

    # If title not provided, try to generate from branch name
    if not title:
        # Convert branch name to title (e.g., "feature/add-api" -> "Add api")
        parts = branch_name.split("/")
        title = parts[-1].replace("-", " ").replace("_", " ").title()

    # Determine worktree path
    if worktree_path:
        wt_path = expand_path(worktree_path)
    else:
        wt_path = config.get_worktree_path(branch_name)

    # Check if worktree path already exists
    if wt_path.exists():
        print_error(f"Worktree path already exists: {wt_path}")
        sys.exit(1)

    # Determine base repository
    if base_repo:
        repo_path = expand_path(base_repo)
    elif config.base_repo_path:
        repo_path = expand_path(config.base_repo_path)
    else:
        # Try to detect current git repo
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
            )
            repo_path = Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            print_error("Not in a git repository and no base repository configured")
            print_info(
                "Either run this command from a git repository, or configure base_repo_path in ~/.ccc-control/config.yaml"
            )
            sys.exit(1)

    # Extract display ID if available
    display_id = extract_display_id(branch_name)
    console.print(f"\n[bold]Creating work item for branch '{branch_name}'[/bold]")
    if display_id:
        console.print(f"[dim]Detected ticket ID: {display_id}[/dim]\n")
    else:
        console.print()

    # Create git worktree
    try:
        print_info(f"Creating worktree at {wt_path}...")

        # Ensure parent directory exists
        wt_path.parent.mkdir(parents=True, exist_ok=True)

        # Create worktree and checkout branch
        subprocess.run(
            ["git", "worktree", "add", "-b", branch_name, str(wt_path)],
            cwd=str(repo_path),
            check=True,
            capture_output=True,
        )

        print_success(f"Created worktree at {wt_path}")
        print_success(f"Created and checked out branch '{branch_name}'")

    except subprocess.CalledProcessError as e:
        print_error(f"Failed to create git worktree: {e}")
        if e.stderr:
            print_error(e.stderr.decode())
        sys.exit(1)

    # Create ticket
    ticket = create_ticket(
        branch=branch_name,
        title=title,
        worktree_path=str(wt_path),
    )

    # Create tmux session
    print_info("Creating tmux session...")
    session_mgr = TmuxSessionManager()
    if not session_mgr.create_session(ticket):
        print_warning("Failed to create tmux session, but ticket was created")

    # Initialize status files
    print_info("Initializing status files...")
    init_status_file(branch_name)
    init_build_status(branch_name)
    init_test_status(branch_name)
    init_todos(branch_name)

    # Add to registry
    try:
        registry.add(ticket)
        print_success(f"\nWork item for branch '{branch_name}' created successfully!")

    except Exception as e:
        print_error(f"Failed to add ticket to registry: {e}")
        # Clean up
        print_info("Cleaning up...")
        session_mgr.kill_session(ticket.tmux_session)
        subprocess.run(["git", "worktree", "remove", str(wt_path)], check=False)
        sys.exit(1)

    # Print next steps
    console.print("\n[bold blue]Next steps:[/bold blue]")
    console.print(
        f"  • Attach to agent terminal: [cyan]ccc attach {branch_name} agent[/cyan]"
    )
    console.print(f"  • View all tickets: [cyan]ccc list[/cyan]")
    console.print(f"  • Open in editor: [cyan]cd {wt_path} && cursor .[/cyan]\n")


@cli.command()
@click.option(
    "--status",
    "-s",
    type=click.Choice(["active", "complete", "blocked", "all"]),
    default="all",
    help="Filter by status",
)
def list(status: str):
    """
    List all tickets with their current status.

    \b
    Examples:
        ccc list
        ccc list --status active
    """
    registry = TicketRegistry()

    if status == "all":
        tickets = registry.list_all()
    else:
        tickets = registry.list_by_status(status)

    if not tickets:
        print_info("No tickets found")
        if status != "all":
            print_info(f"Try 'ccc list' to see all tickets")
        return

    # Create table
    table = Table(title=f"Command Center Tickets ({len(tickets)})", show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("Branch", style="blue")
    table.add_column("Title", style="white")
    table.add_column("Status", style="green")
    table.add_column("Updated", style="yellow")

    for ticket in tickets:
        # Get status symbol
        status_symbols = {
            "active": "●",
            "complete": "✓",
            "blocked": "⚠",
        }
        symbol = status_symbols.get(ticket.status, "○")

        # Get display ID (extracted from branch name if available)
        display_id = ticket.display_id or "-"

        # Get agent status if available
        agent_status = read_agent_status(ticket.branch)
        if agent_status and agent_status.current_task:
            status_text = (
                f"{symbol} {agent_status.status}: {agent_status.current_task[:30]}"
            )
        else:
            status_text = f"{symbol} {ticket.status}"

        table.add_row(
            display_id,
            ticket.branch[:30],
            ticket.title[:30],
            status_text,
            format_time_ago(ticket.updated_at),
        )

    console.print(table)

    # Print summary
    active_count = len([t for t in tickets if t.status == "active"])
    complete_count = len([t for t in tickets if t.status == "complete"])
    blocked_count = len([t for t in tickets if t.status == "blocked"])

    console.print(f"\n{len(tickets)} tickets total ", end="")
    console.print(f"([green]{active_count} active[/green], ", end="")
    console.print(f"[dim]{complete_count} complete[/dim], ", end="")
    console.print(f"[yellow]{blocked_count} blocked[/yellow])\n")


@cli.command()
@click.argument("branch_name")
@click.option(
    "--keep-worktree",
    is_flag=True,
    help="Keep the git worktree (only remove from registry)",
)
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
def delete(branch_name: str, keep_worktree: bool, force: bool):
    """
    Delete a work item and clean up its resources.

    BRANCH_NAME: The branch name of the work item to delete

    \b
    Examples:
        ccc delete feature/IN-413-add-api
        ccc delete bugfix/auth-fix --keep-worktree
        ccc delete feature/new-dashboard --force
    """
    registry = TicketRegistry()

    # Check if ticket exists
    ticket = registry.get(branch_name)
    if ticket is None:
        print_error(f"Work item for branch '{branch_name}' not found")
        sys.exit(1)

    # Confirm deletion
    if not force:
        console.print(
            f"\n[bold yellow]About to delete work item for branch '{branch_name}':[/bold yellow]"
        )
        console.print(f"  Title: {ticket.title}")
        console.print(f"  Worktree: {ticket.worktree_path}")
        console.print(f"  Tmux session: {ticket.tmux_session}")

        if not keep_worktree:
            console.print(
                "\n[bold red]This will remove the worktree and all uncommitted changes![/bold red]"
            )

        if not confirm("\nAre you sure you want to delete this ticket?"):
            print_info("Deletion cancelled")
            return

    # Kill tmux session
    print_info("Killing tmux session...")
    session_mgr = TmuxSessionManager()
    session_mgr.kill_session(ticket.tmux_session)

    # Remove worktree if requested
    if not keep_worktree:
        print_info("Removing git worktree...")
        try:
            subprocess.run(
                ["git", "worktree", "remove", ticket.worktree_path, "--force"],
                check=True,
                capture_output=True,
            )
            print_success("Removed git worktree")
        except subprocess.CalledProcessError as e:
            print_warning(f"Failed to remove worktree: {e}")
            print_info("You may need to remove it manually:")
            print_info(f"  git worktree remove {ticket.worktree_path}")

    # Remove from registry
    print_info("Removing from registry...")
    registry.delete(branch_name)

    print_success(f"\nWork item for branch '{branch_name}' deleted successfully")


@cli.command()
@click.argument("branch_name")
@click.argument("window", type=click.Choice(["agent", "server", "tests"]))
def attach(branch_name: str, window: str):
    """
    Attach to a tmux window for a work item.

    BRANCH_NAME: The branch name of the work item to attach to

    WINDOW: Which terminal to attach to (agent, server, or tests)

    \b
    Examples:
        ccc attach feature/IN-413-add-api agent
        ccc attach bugfix/auth-fix server
        ccc attach feature/new-dashboard tests
    """
    registry = TicketRegistry()

    # Check if ticket exists
    ticket = registry.get(branch_name)
    if ticket is None:
        print_error(f"Work item for branch '{branch_name}' not found")
        sys.exit(1)

    # Attach to session
    session_mgr = TmuxSessionManager()
    session_mgr.attach_to_window(ticket.tmux_session, window)


@cli.group()
def status():
    """Manage agent status for tickets."""
    pass


@status.command("update")
@click.argument("branch_name")
@click.option(
    "--status",
    "-s",
    required=True,
    type=click.Choice(["idle", "working", "complete", "blocked", "error"]),
    help="Agent status",
)
@click.option("--task", "-t", help="Current task description")
@click.option("--blocked", is_flag=True, help="Mark as blocked")
@click.option("--question", "-q", help="Add a question")
def status_update(
    branch_name: str,
    status: str,
    task: Optional[str],
    blocked: bool,
    question: Optional[str],
):
    """
    Update agent status for a work item.

    \b
    Examples:
        ccc status update feature/IN-413-add-api --status working --task "Adding validation"
        ccc status update bugfix/auth-fix --status blocked --question "Use Zod or Joi?"
        ccc status update feature/new-dashboard --status complete
    """
    registry = TicketRegistry()

    # Check if ticket exists
    if not registry.exists(branch_name):
        print_error(f"Work item for branch '{branch_name}' not found")
        sys.exit(1)

    # Update status
    if update_status_file(branch_name, status, task, blocked, question):
        print_success(f"Updated status for branch '{branch_name}'")
        if task:
            print_info(f"Task: {task}")
        if blocked:
            print_warning("Marked as blocked")
    else:
        print_error("Failed to update status")
        sys.exit(1)


@status.command("show")
@click.argument("branch_name")
def status_show(branch_name: str):
    """
    Show agent status for a work item.

    \b
    Examples:
        ccc status show feature/IN-413-add-api
    """
    registry = TicketRegistry()

    # Check if ticket exists
    if not registry.exists(branch_name):
        print_error(f"Work item for branch '{branch_name}' not found")
        sys.exit(1)

    # Read status
    agent_status = read_agent_status(branch_name)

    if agent_status is None:
        print_warning(f"No status file found for branch '{branch_name}'")
        print_info("Agent may not have started yet")
        return

    # Display status
    console.print(f"\n[bold]Agent Status: {branch_name}[/bold]\n")
    console.print(
        f"Status: [{_get_status_color(agent_status.status)}]{agent_status.status}[/]"
    )

    if agent_status.current_task:
        console.print(f"Task: {agent_status.current_task}")

    if agent_status.last_update:
        console.print(f"Updated: {format_time_ago(agent_status.last_update)}")

    console.print(f"Blocked: {'Yes' if agent_status.blocked else 'No'}")

    if agent_status.questions:
        console.print(f"\nQuestions ({len(agent_status.questions)}):")
        for q in agent_status.questions:
            console.print(f"  • {q.get('question', 'N/A')}")

    console.print()


@cli.group()
def build():
    """Manage build status for tickets."""
    pass


@build.command("update")
@click.argument("branch_name")
@click.option(
    "--status",
    "-s",
    required=True,
    type=click.Choice(["passing", "failing"]),
    help="Build status",
)
@click.option("--duration", "-d", type=int, help="Build duration in seconds")
@click.option("--warnings", "-w", type=int, default=0, help="Number of warnings")
@click.option("--errors", "-e", multiple=True, help="Error messages")
def build_update(
    branch_name: str, status: str, duration: Optional[int], warnings: int, errors: tuple
):
    """
    Update build status for a ticket.

    \b
    Examples:
        ccc build update feature/IN-413-add-api --status passing --duration 45
        ccc build update feature/IN-413-add-api --status failing --duration 23 --errors "Syntax error in main.py"
    """
    registry = TicketRegistry()

    # Check if ticket exists
    if not registry.exists(branch_name):
        print_error(f"branch '{branch_name}' not found")
        sys.exit(1)

    # Update build status
    error_list = list(errors) if errors else None
    if update_build_status(branch_name, status, duration, error_list, warnings):
        print_success(f"Updated build status for branch '{branch_name}'")
        print_info(f"Status: {status}")
        if duration:
            print_info(f"Duration: {duration}s")
    else:
        print_error("Failed to update build status")
        sys.exit(1)


@build.command("show")
@click.argument("branch_name")
def build_show(branch_name: str):
    """
    Show build status for a ticket.

    \b
    Examples:
        ccc build show feature/IN-413-add-api
    """
    registry = TicketRegistry()

    # Check if ticket exists
    if not registry.exists(branch_name):
        print_error(f"branch '{branch_name}' not found")
        sys.exit(1)

    # Read build status
    build_status_obj = read_build_status(branch_name)

    if build_status_obj is None:
        print_warning(f"No build status found for branch '{branch_name}'")
        print_info("Run a build first or use 'ccc build update' to set status")
        return

    # Display status
    console.print(f"\n[bold]Build Status: {branch_name}[/bold]\n")
    console.print(format_build_status(build_status_obj))
    console.print()


@cli.group()
def test():
    """Manage test status for tickets."""
    pass


@test.command("update")
@click.argument("branch_name")
@click.option(
    "--status",
    "-s",
    required=True,
    type=click.Choice(["passing", "failing"]),
    help="Test status",
)
@click.option("--duration", "-d", type=int, help="Test run duration in seconds")
@click.option("--total", type=int, help="Total number of tests")
@click.option("--passed", type=int, help="Number of passed tests")
@click.option("--failed", type=int, help="Number of failed tests")
@click.option("--skipped", type=int, help="Number of skipped tests")
def test_update(
    branch_name: str,
    status: str,
    duration: Optional[int],
    total: Optional[int],
    passed: Optional[int],
    failed: Optional[int],
    skipped: Optional[int],
):
    """
    Update test status for a ticket.

    \b
    Examples:
        ccc test update feature/IN-413-add-api --status passing --total 50 --passed 50 --failed 0
        ccc test update feature/IN-413-add-api --status failing --total 50 --passed 47 --failed 3 --duration 12
    """
    registry = TicketRegistry()

    # Check if ticket exists
    if not registry.exists(branch_name):
        print_error(f"branch '{branch_name}' not found")
        sys.exit(1)

    # Update test status
    if update_test_status(
        branch_name, status, duration, total, passed, failed, skipped
    ):
        print_success(f"Updated test status for branch '{branch_name}'")
        print_info(f"Status: {status}")
        if total:
            print_info(f"Tests: {passed}/{total} passed")
    else:
        print_error("Failed to update test status")
        sys.exit(1)


@test.command("parse")
@click.argument("branch_name")
@click.argument("output_file", type=click.Path(exists=True))
@click.option(
    "--framework",
    "-f",
    type=click.Choice(["auto", "jest", "pytest", "go"]),
    default="auto",
    help="Test framework type",
)
@click.option("--duration", "-d", type=int, help="Test run duration in seconds")
@click.option(
    "--status", "-s", type=click.Choice(["passing", "failing"]), help="Override status"
)
def test_parse(
    branch_name: str,
    output_file: str,
    framework: str,
    duration: Optional[int],
    status: Optional[str],
):
    """
    Parse test output file and update status.

    \b
    Examples:
        ccc test parse feature/IN-413-add-api test-output.txt
        ccc test parse feature/IN-413-add-api test-output.txt --framework jest --duration 12
    """
    registry = TicketRegistry()

    # Check if ticket exists
    if not registry.exists(branch_name):
        print_error(f"branch '{branch_name}' not found")
        sys.exit(1)

    # Read output file
    try:
        with open(output_file, "r") as f:
            output = f.read()
    except Exception as e:
        print_error(f"Failed to read output file: {e}")
        sys.exit(1)

    # Parse output
    parsed = parse_test_output(output, framework)

    # Determine status
    if status is None:
        status = "passing" if parsed.get("failed", 0) == 0 else "failing"

    # Update test status
    if update_test_status(
        branch_name,
        status,
        duration,
        parsed.get("total"),
        parsed.get("passed"),
        parsed.get("failed"),
        parsed.get("skipped"),
    ):
        print_success(f"Updated test status for branch '{branch_name}'")
        print_info(
            f"Parsed {parsed.get('total', 0)} tests: "
            f"{parsed.get('passed', 0)} passed, "
            f"{parsed.get('failed', 0)} failed, "
            f"{parsed.get('skipped', 0)} skipped"
        )
    else:
        print_error("Failed to update test status")
        sys.exit(1)


@test.command("show")
@click.argument("branch_name")
def test_show(branch_name: str):
    """
    Show test status for a ticket.

    \b
    Examples:
        ccc test show feature/IN-413-add-api
    """
    registry = TicketRegistry()

    # Check if ticket exists
    if not registry.exists(branch_name):
        print_error(f"branch '{branch_name}' not found")
        sys.exit(1)

    # Read test status
    test_status_obj = read_test_status(branch_name)

    if test_status_obj is None:
        print_warning(f"No test status found for branch '{branch_name}'")
        print_info("Run tests first or use 'ccc test update' to set status")
        return

    # Display status
    console.print(f"\n[bold]Test Status: {branch_name}[/bold]\n")
    console.print(format_test_status(test_status_obj))
    console.print()


@cli.group()
def api():
    """Manage API requests for testing."""
    pass


@api.command("add")
@click.argument("branch_name")
@click.argument("request_name")
@click.option("--method", "-m", type=click.Choice(["GET", "POST", "PUT", "PATCH", "DELETE"]), default="GET", help="HTTP method")
@click.option("--url", "-u", help="Request URL")
@click.option("--header", "-H", multiple=True, help="Header in format 'Key: Value'")
@click.option("--body", "-b", help="Request body")
@click.option("--expected-status", "-s", type=int, help="Expected status code")
def api_add(branch_name: str, request_name: str, method: str, url: Optional[str], header: tuple, body: Optional[str], expected_status: Optional[int]):
    """
    Add a new API request.

    \b
    Examples:
        ccc api add feature/api --method POST --url "http://localhost:3000/api/users"
        ccc api add feature/api --method GET --url "{{base_url}}/api/users" --header "Accept: application/json"
    """
    from ccc.api_testing import add_request, load_requests
    from ccc.api_request import ApiRequest, HttpMethod

    registry = TicketRegistry()
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    # Check if request already exists
    existing_requests, _ = load_requests(branch_name)
    if any(req.name == request_name for req in existing_requests):
        print_error(f"Request '{request_name}' already exists")
        sys.exit(1)

    # Interactive mode if URL not provided
    if not url:
        url = console.input("URL: ").strip()
        if not url:
            print_error("URL is required")
            sys.exit(1)

    # Parse headers
    headers_dict = {}
    for h in header:
        if ": " in h:
            key, value = h.split(": ", 1)
            headers_dict[key] = value

    # Create request
    request = ApiRequest(
        name=request_name,
        method=HttpMethod.from_string(method),
        url=url,
        headers=headers_dict,
        body=body,
        expected_status=expected_status,
    )

    if add_request(branch_name, request):
        print_success(f"Added API request '{request_name}'")
        print_info(f"Method: {method}")
        print_info(f"URL: {url}")
    else:
        print_error("Failed to add request")
        sys.exit(1)


@api.command("list")
@click.argument("branch_name")
def api_list(branch_name: str):
    """
    List all API requests for a branch.

    \b
    Examples:
        ccc api list feature/api-testing
    """
    from ccc.api_testing import load_requests

    registry = TicketRegistry()
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    requests_list, variables = load_requests(branch_name)

    if not requests_list:
        print_info(f"No API requests found for branch '{branch_name}'")
        print_info("Use 'ccc api add' to create one")
        return

    # Create table
    table = Table(title=f"API Requests ({len(requests_list)})", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Method", style="blue")
    table.add_column("URL", style="white")
    table.add_column("Expected", style="yellow")
    table.add_column("Last Run", style="green")

    for req in requests_list:
        last_run = format_time_ago(req.last_executed) if req.last_executed else "Never"
        expected = str(req.expected_status) if req.expected_status else "-"

        # Truncate URL if too long
        url_display = req.url[:50] + "..." if len(req.url) > 50 else req.url

        table.add_row(
            req.name,
            req.method.value,
            url_display,
            expected,
            last_run,
        )

    console.print(table)

    # Show variables if any
    if variables.variables:
        console.print(f"\n[bold]Variables ({len(variables.variables)}):[/bold]")
        for key, value in variables.variables.items():
            # Mask sensitive values (containing 'token', 'key', 'secret', 'password')
            if any(word in key.lower() for word in ['token', 'key', 'secret', 'password']):
                masked_value = value[:4] + "***" if len(value) > 4 else "***"
                console.print(f"  {key}: {masked_value}")
            else:
                console.print(f"  {key}: {value}")
        console.print()


@api.command("run")
@click.argument("branch_name")
@click.argument("request_name")
def api_run(branch_name: str, request_name: str):
    """
    Execute an API request.

    \b
    Examples:
        ccc api run feature/api-testing "Get users"
    """
    from ccc.api_testing import execute_request_by_name

    registry = TicketRegistry()
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    console.print(f"\n[bold]Executing: {request_name}[/bold]\n")

    response, error = execute_request_by_name(branch_name, request_name)

    if error:
        print_error(f"Request failed: {error}")
        sys.exit(1)

    if response:
        # Display response
        status_color = response.status_color()
        console.print(f"Status: [{status_color}]{response.status_code} {response.reason}[/]")
        console.print(f"Time: {response.elapsed_ms:.0f}ms")
        console.print()

        # Show headers
        console.print("[bold]Headers:[/bold]")
        for key, value in list(response.headers.items())[:5]:  # Show first 5 headers
            console.print(f"  {key}: {value}")
        if len(response.headers) > 5:
            console.print(f"  ... and {len(response.headers) - 5} more")
        console.print()

        # Show body
        console.print("[bold]Body:[/bold]")
        formatted_body = response.get_formatted_body()
        # Truncate if too long
        if len(formatted_body) > 500:
            console.print(formatted_body[:500])
            console.print(f"\n... (truncated, {len(formatted_body)} total characters)")
        else:
            console.print(formatted_body)
        console.print()

        print_success("Request completed successfully")


@api.command("delete")
@click.argument("branch_name")
@click.argument("request_name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def api_delete(branch_name: str, request_name: str, force: bool):
    """
    Delete an API request.

    \b
    Examples:
        ccc api delete feature/api-testing "Get users"
    """
    from ccc.api_testing import delete_request, get_request

    registry = TicketRegistry()
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    # Check if request exists
    request = get_request(branch_name, request_name)
    if not request:
        print_error(f"Request '{request_name}' not found")
        sys.exit(1)

    # Confirm deletion
    if not force:
        console.print(f"\n[bold yellow]About to delete API request:[/bold yellow]")
        console.print(f"  Name: {request.name}")
        console.print(f"  Method: {request.method.value}")
        console.print(f"  URL: {request.url}")

        if not confirm("\nAre you sure you want to delete this request?"):
            print_info("Deletion cancelled")
            return

    if delete_request(branch_name, request_name):
        print_success(f"Deleted API request '{request_name}'")
    else:
        print_error("Failed to delete request")
        sys.exit(1)


@api.command("history")
@click.argument("branch_name")
@click.option("--limit", "-n", type=int, default=10, help="Number of entries to show")
@click.option("--clear", is_flag=True, help="Clear all history")
def api_history(branch_name: str, limit: int, clear: bool):
    """
    Show or clear execution history.

    \b
    Examples:
        ccc api history feature/api-testing
        ccc api history feature/api-testing --limit 20
        ccc api history feature/api-testing --clear
    """
    from ccc.api_testing import load_history, clear_history

    registry = TicketRegistry()
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    if clear:
        if confirm("Clear all API request history?"):
            clear_history(branch_name)
            print_success("History cleared")
        return

    history = load_history(branch_name, limit=limit)

    if not history:
        print_info(f"No execution history for branch '{branch_name}'")
        return

    # Create table
    table = Table(title=f"API Request History ({len(history)} recent)", show_header=True)
    table.add_column("Time", style="yellow")
    table.add_column("Request", style="cyan")
    table.add_column("Method", style="blue")
    table.add_column("Status", style="white")
    table.add_column("Result", style="green")

    for exec_data in history:
        time_str = format_time_ago(exec_data.timestamp)

        if exec_data.response:
            status = str(exec_data.response.status_code)
            result = "✓ Success" if exec_data.response.is_success() else "✗ Error"
        else:
            status = "-"
            result = f"✗ {exec_data.error[:30]}" if exec_data.error else "✗ Failed"

        table.add_row(
            time_str,
            exec_data.request_name,
            exec_data.method,
            status,
            result,
        )

    console.print(table)
    console.print()


@api.group("var")
def api_var():
    """Manage variables for request substitution."""
    pass


@api_var.command("set")
@click.argument("branch_name")
@click.argument("key")
@click.argument("value")
def api_var_set(branch_name: str, key: str, value: str):
    """
    Set a variable value.

    \b
    Examples:
        ccc api var set feature/api-testing base_url "http://localhost:3000"
        ccc api var set feature/api-testing api_token "abc123"
    """
    from ccc.api_testing import set_variable

    registry = TicketRegistry()
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    set_variable(branch_name, key, value)
    print_success(f"Set variable '{key}' = '{value}'")


@api_var.command("list")
@click.argument("branch_name")
def api_var_list(branch_name: str):
    """
    List all variables.

    \b
    Examples:
        ccc api var list feature/api-testing
    """
    from ccc.api_testing import load_requests

    registry = TicketRegistry()
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    _, variables = load_requests(branch_name)

    if not variables.variables:
        print_info("No variables defined")
        print_info("Use 'ccc api var set' to create one")
        return

    console.print(f"\n[bold]Variables ({len(variables.variables)}):[/bold]\n")
    for key, value in variables.variables.items():
        # Mask sensitive values
        if any(word in key.lower() for word in ['token', 'key', 'secret', 'password']):
            masked_value = value[:4] + "***" if len(value) > 4 else "***"
            console.print(f"  {key}: {masked_value}")
        else:
            console.print(f"  {key}: {value}")
    console.print()


@api_var.command("delete")
@click.argument("branch_name")
@click.argument("key")
def api_var_delete(branch_name: str, key: str):
    """
    Delete a variable.

    \b
    Examples:
        ccc api var delete feature/api-testing api_token
    """
    from ccc.api_testing import delete_variable

    registry = TicketRegistry()
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    if delete_variable(branch_name, key):
        print_success(f"Deleted variable '{key}'")
    else:
        print_error(f"Variable '{key}' not found")
        sys.exit(1)


@cli.command()
def config():
    """Initialize or reconfigure Command Center."""
    init_config()


@cli.command()
def version():
    """Show version information."""
    console.print(f"\nCommand Center v{__version__}")
    console.print(f"Tmux: {get_tmux_version()}\n")


@cli.command()
def tui():
    """
    Launch the Command Center TUI (Terminal User Interface).

    The TUI provides a LazyGit-style interface for managing tickets
    and monitoring status in real-time.

    \b
    Keyboard shortcuts:
        q     - Quit
        r     - Refresh all data
        j/k   - Navigate up/down
        Enter - Select ticket
    """
    from ccc.tui import run_tui

    try:
        run_tui()
    except Exception as e:
        print_error(f"TUI error: {e}")
        sys.exit(1)


@cli.group()
def todo():
    """Manage todo lists for branches."""
    pass


@todo.command("add")
@click.argument("branch_name")
@click.argument("description")
@click.option("--estimate", "-e", type=int, help="Estimated time in minutes")
@click.option("--blocked-by", "-b", type=int, help="ID of blocking task")
@click.option("--assign", "-a", help="Assign to agent")
def todo_add(
    branch_name: str,
    description: str,
    estimate: Optional[int],
    blocked_by: Optional[int],
    assign: Optional[str],
):
    """
    Add a new todo item to a branch.

    \b
    Examples:
        ccc todo add feature/IN-413 "Write unit tests"
        ccc todo add feature/IN-413 "Add validation" --estimate 30
        ccc todo add feature/IN-413 "Integration tests" --blocked-by 3
        ccc todo add feature/IN-413 "Deploy to staging" --assign agent-1
    """
    registry = TicketRegistry()

    # Check if branch exists
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    try:
        item = add_todo(
            branch_name,
            description,
            estimated_minutes=estimate,
            blocked_by=blocked_by,
            assigned_agent=assign,
        )
        print_success(f"Added todo #{item.id}: {description}")
        if estimate:
            print_info(f"Estimated time: {estimate} minutes")
        if blocked_by:
            print_warning(f"Blocked by task #{blocked_by}")
        if assign:
            print_info(f"Assigned to: {assign}")
    except ValueError as e:
        print_error(f"Failed to add todo: {e}")
        sys.exit(1)


@todo.command("list")
@click.argument("branch_name")
@click.option("--all", "-a", is_flag=True, help="Show all todos including completed")
def todo_list_cmd(branch_name: str, all: bool):
    """
    List todos for a branch.

    \b
    Examples:
        ccc todo list feature/IN-413
        ccc todo list feature/IN-413 --all
    """
    registry = TicketRegistry()

    # Check if branch exists
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    todo_list = list_todos(branch_name)

    if not todo_list.items:
        print_info(f"No todos for branch '{branch_name}'")
        return

    # Filter out completed items if not showing all
    config = load_config()
    items = todo_list.items
    if not all and not config.todos_show_completed:
        items = [item for item in items if item.status != "done"]

    # Display todos
    console.print(f"\n[bold]Todo List: {branch_name}[/bold]\n")

    for item in items:
        # Status symbol
        symbols = {
            "done": "✓",
            "in_progress": "⚙",
            "not_started": "☐",
            "blocked": "⏸",
        }
        symbol = symbols.get(item.status, "○")

        # Build status line
        status_parts = []
        if item.assigned_agent:
            status_parts.append(f"[{item.assigned_agent}]")
        if item.blocked_by:
            status_parts.append(f"(blocked by #{item.blocked_by})")
        if item.estimated_minutes:
            status_parts.append(f"~{item.estimated_minutes}m")

        status_str = " ".join(status_parts)

        # Print todo item
        console.print(f"{symbol} {item.id}. {item.description} {status_str}")

    # Display progress
    stats = todo_list.progress_stats()
    progress = todo_list.progress_percentage()
    console.print(
        f"\n[bold]Progress:[/bold] {stats['done']}/{stats['total']} complete ({progress:.0f}%)"
    )
    console.print(
        f"  {stats['in_progress']} in progress, "
        f"{stats['not_started']} not started, "
        f"{stats['blocked']} blocked\n"
    )


@todo.command("done")
@click.argument("branch_name")
@click.argument("task_id", type=int)
def todo_done(branch_name: str, task_id: int):
    """
    Mark a todo as done.

    \b
    Examples:
        ccc todo done feature/IN-413 3
    """
    registry = TicketRegistry()

    # Check if branch exists
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    item = update_todo_status(branch_name, task_id, "done")
    if item:
        print_success(f"Marked todo #{task_id} as done: {item.description}")
    else:
        print_error(f"Todo #{task_id} not found")
        sys.exit(1)


@todo.command("status")
@click.argument("branch_name")
@click.argument("task_id", type=int)
@click.argument(
    "status", type=click.Choice(["not_started", "in_progress", "done", "blocked"])
)
def todo_status_cmd(branch_name: str, task_id: int, status: str):
    """
    Update todo status.

    \b
    Examples:
        ccc todo status feature/IN-413 3 in_progress
        ccc todo status feature/IN-413 5 blocked
    """
    registry = TicketRegistry()

    # Check if branch exists
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    item = update_todo_status(branch_name, task_id, status)
    if item:
        print_success(f"Updated todo #{task_id} status to '{status}'")
    else:
        print_error(f"Todo #{task_id} not found")
        sys.exit(1)


@todo.command("delete")
@click.argument("branch_name")
@click.argument("task_id", type=int)
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def todo_delete(branch_name: str, task_id: int, force: bool):
    """
    Delete a todo item.

    \b
    Examples:
        ccc todo delete feature/IN-413 3
        ccc todo delete feature/IN-413 5 --force
    """
    registry = TicketRegistry()

    # Check if branch exists
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    # Get the item first to show what will be deleted
    todo_list = list_todos(branch_name)
    item = todo_list.get_item(task_id)

    if not item:
        print_error(f"Todo #{task_id} not found")
        sys.exit(1)

    # Confirm deletion
    if not force:
        console.print(f"\n[bold yellow]About to delete:[/bold yellow]")
        console.print(f"  #{item.id}: {item.description}")
        if not confirm("Are you sure?"):
            print_info("Deletion cancelled")
            return

    if delete_todo(branch_name, task_id):
        print_success(f"Deleted todo #{task_id}")
    else:
        print_error(f"Failed to delete todo #{task_id}")
        sys.exit(1)


@todo.command("move")
@click.argument("branch_name")
@click.argument("task_id", type=int)
@click.argument("position", type=int)
def todo_move(branch_name: str, task_id: int, position: int):
    """
    Move a todo to a new position (1-indexed).

    \b
    Examples:
        ccc todo move feature/IN-413 5 1  # Move task 5 to first position
        ccc todo move feature/IN-413 2 4  # Move task 2 to fourth position
    """
    registry = TicketRegistry()

    # Check if branch exists
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    if move_todo(branch_name, task_id, position):
        print_success(f"Moved todo #{task_id} to position {position}")
    else:
        print_error(f"Failed to move todo #{task_id} to position {position}")
        print_info("Check that the task exists and position is valid")
        sys.exit(1)


@todo.command("assign")
@click.argument("branch_name")
@click.argument("task_id", type=int)
@click.argument("agent_name")
def todo_assign_cmd(branch_name: str, task_id: int, agent_name: str):
    """
    Assign a todo to an agent.

    \b
    Examples:
        ccc todo assign feature/IN-413 3 agent-1
        ccc todo assign feature/IN-413 5 claude-engineer
    """
    registry = TicketRegistry()

    # Check if branch exists
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    item = assign_todo(branch_name, task_id, agent_name)
    if item:
        print_success(f"Assigned todo #{task_id} to {agent_name}")
    else:
        print_error(f"Todo #{task_id} not found")
        sys.exit(1)


@todo.command("unassign")
@click.argument("branch_name")
@click.argument("task_id", type=int)
def todo_unassign(branch_name: str, task_id: int):
    """
    Unassign a todo from an agent.

    \b
    Examples:
        ccc todo unassign feature/IN-413 3
    """
    registry = TicketRegistry()

    # Check if branch exists
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    item = assign_todo(branch_name, task_id, None)
    if item:
        print_success(f"Unassigned todo #{task_id}")
    else:
        print_error(f"Todo #{task_id} not found")
        sys.exit(1)


@todo.command("block")
@click.argument("branch_name")
@click.argument("task_id", type=int)
@click.argument("blocked_by", type=int)
def todo_block(branch_name: str, task_id: int, blocked_by: int):
    """
    Set a todo as blocked by another todo.

    \b
    Examples:
        ccc todo block feature/IN-413 5 3  # Task 5 is blocked by task 3
    """
    registry = TicketRegistry()

    # Check if branch exists
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    try:
        item = set_blocked_by(branch_name, task_id, blocked_by)
        if item:
            print_success(f"Todo #{task_id} is now blocked by #{blocked_by}")
            print_warning(f"Status automatically set to 'blocked'")
        else:
            print_error(f"Todo #{task_id} not found")
            sys.exit(1)
    except ValueError as e:
        print_error(f"Failed to set dependency: {e}")
        sys.exit(1)


@todo.command("unblock")
@click.argument("branch_name")
@click.argument("task_id", type=int)
def todo_unblock(branch_name: str, task_id: int):
    """
    Remove blocking dependency from a todo.

    \b
    Examples:
        ccc todo unblock feature/IN-413 5
    """
    registry = TicketRegistry()

    # Check if branch exists
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    item = set_blocked_by(branch_name, task_id, None)
    if item:
        print_success(f"Removed blocking dependency from todo #{task_id}")
    else:
        print_error(f"Todo #{task_id} not found")
        sys.exit(1)


@todo.command("edit")
@click.argument("branch_name")
@click.argument("task_id", type=int)
@click.argument("description")
def todo_edit(branch_name: str, task_id: int, description: str):
    """
    Edit a todo's description.

    \b
    Examples:
        ccc todo edit feature/IN-413 3 "Write comprehensive unit tests"
    """
    registry = TicketRegistry()

    # Check if branch exists
    if not registry.exists(branch_name):
        print_error(f"Branch '{branch_name}' not found")
        sys.exit(1)

    item = update_todo_description(branch_name, task_id, description)
    if item:
        print_success(f"Updated todo #{task_id}: {description}")
    else:
        print_error(f"Todo #{task_id} not found")
        sys.exit(1)


def _get_status_color(status: str) -> str:
    """Get color for status display."""
    colors = {
        "working": "green",
        "complete": "blue",
        "blocked": "yellow",
        "error": "red",
        "idle": "white",
    }
    return colors.get(status, "white")


def main():
    """Entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        print_info("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
