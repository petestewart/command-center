"""
Widgets package for Command Center TUI.

This package contains reusable widgets for the TUI interface.

Phase 1 widgets are in the parent widgets.py for backward compatibility.
Phase 3 widgets (agent tracking) are in this package.
"""

from ccc.tui.widgets.agent_card import AgentCard
from ccc.tui.widgets.agents_pane import AgentsPane

__all__ = [
    'AgentCard',
    'AgentsPane',
]
