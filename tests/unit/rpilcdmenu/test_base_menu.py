from unittest import mock
from rpilcdmenu.base_menu import BaseMenu

def test_basemenu_can_be_initialized_entered_and_exited():
    base_menu = BaseMenu(mock.Mock())
    base_menu.start()
    base_menu.exit()


def test_basemenu_can_append_scroll_and_select_menuitems():
    base_menu = BaseMenu()
    base_menu.start()

    menuitem_mock = mock.Mock()
    target_menuitem_mock = mock.Mock()
    target_menuitem_mock.action = mock.Mock()

    base_menu.append_item(menuitem_mock)
    base_menu.append_item(target_menuitem_mock)

    base_menu.processDown()
    base_menu.processDown()
    base_menu.processUp()
    base_menu.processUp()
    base_menu.processDown()

    base_menu.processEnter()

    target_menuitem_mock.action.assert_called_once()


def test_basemenu_process_process_enter_renders_submenu_when_submenu_item_selected():
    base_menu = BaseMenu()
    base_menu.start()

    submenu_mock = mock.Mock()
    submenu_mock.__class__ = BaseMenu

    menuitem_mock = mock.Mock()
    menuitem_mock.action = mock.Mock()
    menuitem_mock.action.return_value = submenu_mock

    base_menu.append_item(menuitem_mock)

    assert submenu_mock == base_menu.processEnter()


def test_basemenu_clearDisplay_exists():
    base_menu = BaseMenu(mock.Mock())
    base_menu.clearDisplay()


def test_basemenu_debug_returns_subitem_debug_info():
    base_menu = BaseMenu()
    base_menu.start()

    menuitem_mock = mock.Mock()
    submenuitem_mock = mock.Mock()
    submenuitem_mock.submenu = mock.Mock()
    submenuitem_mock.submenu.debug = mock.Mock()
    submenuitem_mock.submenu.__class__ = BaseMenu
    base_menu.append_item(menuitem_mock)
    base_menu.append_item(submenuitem_mock)

    base_menu.debug()
    submenuitem_mock.submenu.debug.assert_called_once()


def test_basemenu_enter_on_an_empty_menu_does_nothing():
    # The plugin leaves a menu empty whenever every item was skipped (no title),
    # and a button press then reaches processEnter. This used to raise IndexError.
    base_menu = BaseMenu()
    base_menu.start()

    assert base_menu.processEnter() is base_menu


def test_basemenu_scrolling_an_empty_menu_leaves_a_usable_index():
    # Not just "does not raise": both wraps used to leave current_option at -1
    # or 1, so the *next* enter press was the one that blew up.
    base_menu = BaseMenu()
    base_menu.start()

    base_menu.processUp()
    assert base_menu.current_option == 0
    base_menu.processDown()
    assert base_menu.current_option == 0


def test_basemenu_a_remembered_index_past_the_end_selects_the_last_item():
    # Menus are restored from history with their old cursor position. Remove a
    # favourite and the list comes back shorter, leaving the index past the end.
    base_menu = BaseMenu()
    first, last = mock.Mock(), mock.Mock()
    base_menu.append_item(first)
    base_menu.append_item(last)
    base_menu.current_option = 7

    base_menu.processEnter()

    last.action.assert_called_once()
    first.action.assert_not_called()
    assert base_menu.current_option == 1


def test_basemenu_a_negative_index_selects_the_first_item():
    base_menu = BaseMenu()
    first = mock.Mock()
    base_menu.append_item(first)
    base_menu.current_option = -3

    base_menu.processEnter()

    first.action.assert_called_once()
    assert base_menu.current_option == 0
