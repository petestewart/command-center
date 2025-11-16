"""
Custom widgets for Command Center TUI.
"""

# We need to be careful here - Python will treat 'ccc.tui.widgets' as this package
# But we also have ccc/tui/widgets.py which has the old widgets
# The solution: rename this package or be explicit about imports

# Import new widgets from this directory
from ccc.tui.widgets.status_bar import StatusBar
from ccc.tui.widgets.button_bar import ButtonBar

# For backward compatibility, we need to also export the old widgets
# We'll import them from the parent widgets.py module by being explicit
import importlib.util
import sys
from pathlib import Path

# Load the widgets.py file directly
widgets_file = Path(__file__).parent.parent / 'widgets.py'
spec = importlib.util.spec_from_file_location("ccc.tui._widgets_legacy", widgets_file)
if spec and spec.loader:
    widgets_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(widgets_module)

    FileCheckboxList = widgets_module.FileCheckboxList
    MultiLineInput = widgets_module.MultiLineInput
    LogViewer = widgets_module.LogViewer
    StreamingOutput = widgets_module.StreamingOutput
    ProgressBarWidget = widgets_module.ProgressBarWidget
    TodoListWidget = widgets_module.TodoListWidget

__all__ = [
    'StatusBar',
    'ButtonBar',
    'FileCheckboxList',
    'MultiLineInput',
    'LogViewer',
    'StreamingOutput',
    'ProgressBarWidget',
    'TodoListWidget',
]
