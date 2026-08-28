"""Tests for the socket client the plugin holds as its dimmer handle.

The wire protocol is exercised from the server side in test_rpi_lcd_menu.py;
here only the client's own parsing and validation are under test, so _send is
stubbed rather than standing up a real unix socket.
"""
from unittest.mock import Mock

import pytest

from rpilcdmenu.display_controller import DisplayController


def _controller(reply):
    ctrl = DisplayController()
    ctrl._send = Mock(return_value=reply)
    return ctrl


def test_brightness_with_no_argument_queries_the_current_level():
    ctrl = _controller('75')

    assert ctrl.brightness() == 75
    ctrl._send.assert_called_once_with('brightness')


def test_brightness_with_a_level_sets_it_and_confirms():
    ctrl = _controller('ok')

    assert ctrl.brightness(50) == 'ok'
    ctrl._send.assert_called_once_with('brightness 50')


def test_brightness_raises_on_a_level_the_hardware_does_not_have():
    ctrl = _controller('error')

    with pytest.raises(ValueError):
        ctrl.brightness(60)


def test_the_existing_verbs_are_untouched():
    for command in ('toggle', 'off', 'on', 'status'):
        ctrl = _controller('ok')
        getattr(ctrl, command)()
        ctrl._send.assert_called_once_with(command)
