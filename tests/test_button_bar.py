"""Tests for button_bar widget."""

import pytest
from textual.widgets import Button

from ccc.tui.widgets.button_bar import ButtonBar


class TestButtonBar:
    """Tests for ButtonBar widget."""

    def test_button_bar_class_exists(self):
        """Test ButtonBar class exists."""
        assert ButtonBar is not None

    def test_button_bar_has_compose_method(self):
        """Test ButtonBar has compose method."""
        button_bar = ButtonBar()
        assert hasattr(button_bar, 'compose')
        assert callable(button_bar.compose)

    def test_button_clicked_message(self):
        """Test ButtonClicked message initialization."""
        message = ButtonBar.ButtonClicked("btn_plan")
        assert message.button_id == "btn_plan"

    def test_active_pane_default_value(self):
        """Test active_pane default value is defined in class."""
        # Check that the reactive property exists on the class
        assert hasattr(ButtonBar, 'active_pane')


class TestButtonBarIntegration:
    """Integration tests for ButtonBar widget.

    These tests would require running a Textual app, which is more complex.
    For now, we test the basic structure and leave full integration testing
    for manual testing or end-to-end tests.
    """

    def test_button_bar_has_expected_css(self):
        """Test ButtonBar has CSS defined."""
        assert hasattr(ButtonBar, 'DEFAULT_CSS')
        assert isinstance(ButtonBar.DEFAULT_CSS, str)
        assert 'ButtonBar' in ButtonBar.DEFAULT_CSS

    def test_button_bar_message_class_exists(self):
        """Test ButtonClicked message class exists."""
        assert hasattr(ButtonBar, 'ButtonClicked')
        assert callable(ButtonBar.ButtonClicked)
