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
from ccc.status import init_status_file, read_agent_status, update_status as update_status_file
from ccc.utils import (
    validate_ticket_id,
    get_branch_name,
    format_time_ago,
    print_success,
    print_error,
    print_warning,
    print_info,
    confirm,
    expand_path,
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
@click.argument('ticket_id')
@click.argument('title')
@click.option('--worktree-path', '-w', help='Custom worktree path (overrides config)')
@click.option('--branch', '-b', help='Custom branch name (auto-generated if not provided)')
@click.option('--base-repo', help='Base repository path for creating worktree')
def create(ticket_id: str, title: str, worktree_path: Optional[str], branch: Optional[str], base_repo: Optional[str]):
    """
    Create a new ticket with git worktree and tmux session.

    TICKET_ID: Unique ticket identifier (e.g., IN-413, PROJ-123)

    TITLE: Human-readable ticket title

    \b
    Examples:
        ccc create IN-413 "Public API bulk uploads"
        ccc create BUG-42 "Fix login error" --branch hotfix/bug-42
    """
    # Validate ticket ID format
    if not validate_ticket_id(ticket_id):
        print_error(f"Invalid ticket ID format: {ticket_id}")
        print_info("Expected format: PREFIX-NUMBER (e.g., IN-413, PROJ-123)")
        sys.exit(1)

    # Load config
    config = load_config()

    # Check if ticket already exists
    registry = TicketRegistry()
    if registry.exists(ticket_id):
        print_error(f"Ticket {ticket_id} already exists")
        print_info(f"Use 'ccc delete {ticket_id}' to remove it first")
        sys.exit(1)

    # Determine worktree path
    if worktree_path:
        wt_path = expand_path(worktree_path)
    else:
        wt_path = config.get_worktree_path(ticket_id)

    # Check if worktree path already exists
    if wt_path.exists():
        print_error(f"Worktree path already exists: {wt_path}")
        sys.exit(1)

    # Determine branch name
    if branch is None:
        branch = get_branch_name(ticket_id, title)

    # Determine base repository
    if base_repo:
        repo_path = expand_path(base_repo)
    elif config.base_repo_path:
        repo_path = expand_path(config.base_repo_path)
    else:
        # Try to detect current git repo
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                capture_output=True,
                text=True,
                check=True
            )
            repo_path = Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            print_error("Not in a git repository and no base repository configured")
            print_info("Either run this command from a git repository, or configure base_repo_path in ~/.cc-control/config.yaml")
            sys.exit(1)

    console.print(f"\n[bold]Creating ticket {ticket_id}[/bold]\n")

    # Create git worktree
    try:
        print_info(f"Creating worktree at {wt_path}...")

        # Ensure parent directory exists
        wt_path.parent.mkdir(parents=True, exist_ok=True)

        # Create worktree and checkout branch
        subprocess.run(
            ['git', 'worktree', 'add', '-b', branch, str(wt_path)],
            cwd=str(repo_path),
            check=True,
            capture_output=True
        )

        print_success(f"Created worktree at {wt_path}")
        print_success(f"Created and checked out branch '{branch}'")

    except subprocess.CalledProcessError as e:
        print_error(f"Failed to create git worktree: {e}")
        if e.stderr:
            print_error(e.stderr.decode())
        sys.exit(1)

    # Create ticket
    ticket = create_ticket(
        ticket_id=ticket_id,
        title=title,
        branch=branch,
        worktree_path=str(wt_path),
    )

    # Create tmux session
    print_info("Creating tmux session...")
    session_mgr = TmuxSessionManager()
    if not session_mgr.create_session(ticket):
        print_warning("Failed to create tmux session, but ticket was created")

    # Initialize status file
    print_info("Initializing status file...")
    init_status_file(ticket_id)

    # Add to registry
    try:
        registry.add(ticket)
        print_success(f"\nTicket {ticket_id} created successfully!")

    except Exception as e:
        print_error(f"Failed to add ticket to registry: {e}")
        # Clean up
        print_info("Cleaning up...")
        session_mgr.kill_session(ticket.tmux_session)
        subprocess.run(['git', 'worktree', 'remove', str(wt_path)], check=False)
        sys.exit(1)

    # Print next steps
    console.print("\n[bold blue]Next steps:[/bold blue]")
    console.print(f"  • Attach to agent terminal: [cyan]ccc attach {ticket_id} agent[/cyan]")
    console.print(f"  • View all tickets: [cyan]ccc list[/cyan]")
    console.print(f"  • Open in editor: [cyan]cd {wt_path} && cursor .[/cyan]\n")


@cli.command()
@click.option('--status', '-s', type=click.Choice(['active', 'complete', 'blocked', 'all']), default='all',
              help='Filter by status')
def list(status: str):
    """
    List all tickets with their current status.

    \b
    Examples:
        ccc list
        ccc list --status active
    """
    registry = TicketRegistry()

    if status == 'all':
        tickets = registry.list_all()
    else:
        tickets = registry.list_by_status(status)

    if not tickets:
        print_info("No tickets found")
        if status != 'all':
            print_info(f"Try 'ccc list' to see all tickets")
        return

    # Create table
    table = Table(title=f"Command Center Tickets ({len(tickets)})", show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="green")
    table.add_column("Branch", style="blue")
    table.add_column("Updated", style="yellow")

    for ticket in tickets:
        # Get status symbol
        status_symbols = {
            'active': '●',
            'complete': '✓',
            'blocked': '⚠',
        }
        symbol = status_symbols.get(ticket.status, '○')

        # Get agent status if available
        agent_status = read_agent_status(ticket.id)
        if agent_status and agent_status.current_task:
            status_text = f"{symbol} {agent_status.status}: {agent_status.current_task[:30]}"
        else:
            status_text = f"{symbol} {ticket.status}"

        table.add_row(
            ticket.id,
            ticket.title[:40],
            status_text,
            ticket.branch[:40],
            format_time_ago(ticket.updated_at)
        )

    console.print(table)

    # Print summary
    active_count = len([t for t in tickets if t.status == 'active'])
    complete_count = len([t for t in tickets if t.status == 'complete'])
    blocked_count = len([t for t in tickets if t.status == 'blocked'])

    console.print(f"\n{len(tickets)} tickets total ", end="")
    console.print(f"([green]{active_count} active[/green], ", end="")
    console.print(f"[dim]{complete_count} complete[/dim], ", end="")
    console.print(f"[yellow]{blocked_count} blocked[/yellow])\n")


@cli.command()
@click.argument('ticket_id')
@click.option('--keep-worktree', is_flag=True, help='Keep the git worktree (only remove from registry)')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompt')
def delete(ticket_id: str, keep_worktree: bool, force: bool):
    """
    Delete a ticket and clean up its resources.

    TICKET_ID: The ticket to delete

    \b
    Examples:
        ccc delete IN-413
        ccc delete IN-413 --keep-worktree
        ccc delete IN-413 --force
    """
    registry = TicketRegistry()

    # Check if ticket exists
    ticket = registry.get(ticket_id)
    if ticket is None:
        print_error(f"Ticket {ticket_id} not found")
        sys.exit(1)

    # Confirm deletion
    if not force:
        console.print(f"\n[bold yellow]About to delete ticket {ticket_id}:[/bold yellow]")
        console.print(f"  Title: {ticket.title}")
        console.print(f"  Worktree: {ticket.worktree_path}")
        console.print(f"  Tmux session: {ticket.tmux_session}")

        if not keep_worktree:
            console.print("\n[bold red]This will remove the worktree and all uncommitted changes![/bold red]")

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
                ['git', 'worktree', 'remove', ticket.worktree_path, '--force'],
                check=True,
                capture_output=True
            )
            print_success("Removed git worktree")
        except subprocess.CalledProcessError as e:
            print_warning(f"Failed to remove worktree: {e}")
            print_info("You may need to remove it manually:")
            print_info(f"  git worktree remove {ticket.worktree_path}")

    # Remove from registry
    print_info("Removing from registry...")
    registry.delete(ticket_id)

    print_success(f"\nTicket {ticket_id} deleted successfully")


@cli.command()
@click.argument('ticket_id')
@click.argument('window', type=click.Choice(['agent', 'server', 'tests']))
def attach(ticket_id: str, window: str):
    """
    Attach to a tmux window for a ticket.

    TICKET_ID: The ticket to attach to

    WINDOW: Which terminal to attach to (agent, server, or tests)

    \b
    Examples:
        ccc attach IN-413 agent
        ccc attach IN-413 server
        ccc attach IN-413 tests
    """
    registry = TicketRegistry()

    # Check if ticket exists
    ticket = registry.get(ticket_id)
    if ticket is None:
        print_error(f"Ticket {ticket_id} not found")
        sys.exit(1)

    # Attach to session
    session_mgr = TmuxSessionManager()
    session_mgr.attach_to_window(ticket.tmux_session, window)


@cli.group()
def status():
    """Manage agent status for tickets."""
    pass


@status.command('update')
@click.argument('ticket_id')
@click.option('--status', '-s', required=True,
              type=click.Choice(['idle', 'working', 'complete', 'blocked', 'error']),
              help='Agent status')
@click.option('--task', '-t', help='Current task description')
@click.option('--blocked', is_flag=True, help='Mark as blocked')
@click.option('--question', '-q', help='Add a question')
def status_update(ticket_id: str, status: str, task: Optional[str], blocked: bool, question: Optional[str]):
    """
    Update agent status for a ticket.

    \b
    Examples:
        ccc status update IN-413 --status working --task "Adding validation"
        ccc status update IN-413 --status blocked --question "Use Zod or Joi?"
        ccc status update IN-413 --status complete
    """
    registry = TicketRegistry()

    # Check if ticket exists
    if not registry.exists(ticket_id):
        print_error(f"Ticket {ticket_id} not found")
        sys.exit(1)

    # Update status
    if update_status_file(ticket_id, status, task, blocked, question):
        print_success(f"Updated status for {ticket_id}")
        if task:
            print_info(f"Task: {task}")
        if blocked:
            print_warning("Marked as blocked")
    else:
        print_error("Failed to update status")
        sys.exit(1)


@status.command('show')
@click.argument('ticket_id')
def status_show(ticket_id: str):
    """
    Show agent status for a ticket.

    \b
    Examples:
        ccc status show IN-413
    """
    registry = TicketRegistry()

    # Check if ticket exists
    if not registry.exists(ticket_id):
        print_error(f"Ticket {ticket_id} not found")
        sys.exit(1)

    # Read status
    agent_status = read_agent_status(ticket_id)

    if agent_status is None:
        print_warning(f"No status file found for {ticket_id}")
        print_info("Agent may not have started yet")
        return

    # Display status
    console.print(f"\n[bold]Agent Status: {ticket_id}[/bold]\n")
    console.print(f"Status: [{_get_status_color(agent_status.status)}]{agent_status.status}[/]")

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


@cli.command()
def config():
    """Initialize or reconfigure Command Center."""
    init_config()


@cli.command()
def version():
    """Show version information."""
    console.print(f"\nCommand Center v{__version__}")
    console.print(f"Tmux: {get_tmux_version()}\n")


def _get_status_color(status: str) -> str:
    """Get color for status display."""
    colors = {
        'working': 'green',
        'complete': 'blue',
        'blocked': 'yellow',
        'error': 'red',
        'idle': 'white',
    }
    return colors.get(status, 'white')


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


if __name__ == '__main__':
    main()
