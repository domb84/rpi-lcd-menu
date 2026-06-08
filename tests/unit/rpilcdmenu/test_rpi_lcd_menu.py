from mock import Mock, MagicMock, patch, call
from rpilcdmenu.rpi_lcd_menu import RpiLCDMenu


def _menu(LCDHwdMock, scrolling_menu=False):
    """Build a menu with a mocked display and no background worker thread."""
    LCDHwdMock.return_value = MagicMock()
    return RpiLCDMenu(start_worker=False, scrolling_menu=scrolling_menu)


def _line(text):
    return text.ljust(16)


def _frame(line1, line2=""):
    return "%s\n%s" % (_line(line1), _line(line2))


def _queued_frames(menu):
    return [frame for frame, _delay in list(menu.lcd_queue.queue)]


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_rpilcdmenu_imports_gpio_and_initializes_with_clear_screen(LCDHwdMock):
    LCDHwdMockInstance = MagicMock()
    LCDHwdMock.return_value = LCDHwdMockInstance

    GPIOMock = Mock()
    RpiLCDMenu(1, 2, [3, 4, 5, 6], GPIOMock, start_worker=False)

    LCDHwdMock.assert_called_once_with(1, 2, [3, 4, 5, 6], GPIOMock)
    LCDHwdMockInstance.initDisplay.assert_called_once()
    LCDHwdMockInstance.write4bits.assert_called_once_with(LCDHwdMock.LCD_CLEARDISPLAY)
    LCDHwdMockInstance.delayMicroseconds.assert_called_once_with(3000)


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_rpilcdmenu_lcd_render_returns_home_and_breaks_lines(LCDHwdMock):
    menu = _menu(LCDHwdMock)
    menu.lcd.reset_mock()

    menu.lcd_render("ab\ncd")

    assert menu.lcd.write4bits.mock_calls == [
        call(LCDHwdMock.LCD_RETURNHOME),
        call(ord("a"), True),
        call(ord("b"), True),
        call(0xC0),
        call(ord("c"), True),
        call(ord("d"), True),
    ]


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_rpilcdmenu_message_pads_single_short_line(LCDHwdMock):
    menu = _menu(LCDHwdMock)

    menu.message("1")

    assert _queued_frames(menu) == [_frame("1")]


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_rpilcdmenu_message_crops_long_unsplittable_line(LCDHwdMock):
    menu = _menu(LCDHwdMock)

    menu.message("1" * 16 + "2")

    # No space to split on, so the text lands on the second line and is cropped.
    assert _queued_frames(menu) == [_frame("", "1" * 16)]


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_rpilcdmenu_message_is_trimmed_to_two_lines(LCDHwdMock):
    menu = _menu(LCDHwdMock)

    menu.message("1\n1\n1")

    assert _queued_frames(menu) == [_frame("1", "1")]


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_rpilcdmenu_displayTestScreen_enqueues_a_frame(LCDHwdMock):
    menu = _menu(LCDHwdMock)

    menu.displayTestScreen()

    frames = _queued_frames(menu)
    assert len(frames) == 1
    assert "This is test" in frames[0]


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_rpilcdmenu_render_empty_menu(LCDHwdMock):
    menu = _menu(LCDHwdMock)

    menu.render()

    assert _queued_frames(menu) == [_frame("Menu is empty")]


def _item(text):
    item = Mock()
    item.text = text
    return item


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_rpilcdmenu_render_two_items_menu(LCDHwdMock):
    menu = _menu(LCDHwdMock)
    menu.append_item(_item("item1"))
    menu.append_item(_item("item2"))

    menu.render()

    assert _queued_frames(menu) == [_frame(">item1", " item2")]


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_rpilcdmenu_render_multiple_items_menu(LCDHwdMock):
    menu = _menu(LCDHwdMock)
    menu.append_item(_item("item1"))
    menu.append_item(_item("item2"))
    menu.append_item(_item("item3"))

    menu.processDown()
    menu.render()

    assert _queued_frames(menu) == [_frame(">item2", " item3")]


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_rpilcdmenu_render_multiple_items_rewind_menu(LCDHwdMock):
    menu = _menu(LCDHwdMock)
    menu.append_item(_item("item1"))
    menu.append_item(_item("item2"))
    menu.append_item(_item("item3"))

    menu.processDown()
    menu.processDown()
    menu.render()

    assert _queued_frames(menu) == [_frame(">item3", " item1")]
