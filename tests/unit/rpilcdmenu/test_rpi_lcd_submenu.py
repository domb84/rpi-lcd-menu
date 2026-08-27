from unittest import mock

from rpilcdmenu.rpi_lcd_menu import RpiLCDMenu
from rpilcdmenu.rpi_lcd_submenu import RpiLCDSubMenu


def test_rpilcdmenu_can_be_initialized():
    base_menu_mock = mock.Mock()
    submenu = RpiLCDSubMenu(base_menu_mock)
    assert isinstance(submenu, RpiLCDSubMenu)


@mock.patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_submenu_shares_the_parents_display_state(LCDHwdMock):
    # The submenu drives the same physical display as its parent, so it has to
    # share the lock (or it serialises against nothing) and the on/off and
    # last-frame state (or the two menus disagree about what is on screen).
    LCDHwdMock.return_value = mock.MagicMock()
    base = RpiLCDMenu(start_worker=False)
    submenu = RpiLCDSubMenu(base)

    assert submenu._lcd_lock is base._lcd_lock
    assert submenu._cgram is base._cgram

    submenu.display_off()
    assert base._display_off is True

    base.render_frame("a\nb")
    assert submenu._last_frame == "a\nb"
