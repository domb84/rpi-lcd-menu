import pytest
from unittest.mock import Mock, MagicMock, patch, call
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


def _queued_delays(menu):
    return [delay for _frame, delay in list(menu.lcd_queue.queue)]


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
def test_rpilcdmenu_lcd_render_homes_the_cursor_and_breaks_lines(LCDHwdMock):
    menu = _menu(LCDHwdMock)
    menu.lcd.reset_mock()

    menu.lcd_render("ab\ncd")

    assert menu.lcd.write4bits.mock_calls == [
        call(LCDHwdMock.LCD_SETDDRAMADDR),
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


# --- autoscroll ------------------------------------------------------------

@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_rpilcdmenu_message_autoscroll_generates_scroll_frames(LCDHwdMock):
    menu = _menu(LCDHwdMock)

    menu.message("ABCDEFGHIJKLMNOPQRST\nx", autoscroll=True)  # line1 is 20 chars

    frames = _queued_frames(menu)
    # frame 0 + one forward frame per character (range 1..len) + 16 reverse
    # frames bringing it back + a final frame returning to the start.
    assert len(frames) == 20 + 16 + 2
    # First frame shows the left-aligned start of the text...
    assert frames[0] == _frame("ABCDEFGHIJKLMNOP", "x")
    # ...the next has scrolled one character to the left...
    assert frames[1] == _frame("BCDEFGHIJKLMNOPQ", "")
    # ...and the sequence ends back where it started so it can loop cleanly.
    assert frames[-1] == frames[0]


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_rpilcdmenu_message_autoscroll_paces_frames(LCDHwdMock):
    menu = _menu(LCDHwdMock)

    menu.message("ABCDEFGHIJKLMNOPQRST\nx", autoscroll=True)

    delays = _queued_delays(menu)
    # First frame is held longer; every subsequent frame uses the scroll step.
    assert delays[0] == menu.SCROLL_HOLD
    assert set(delays[1:]) == {menu.SCROLL_INTERVAL}


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_rpilcdmenu_message_does_not_scroll_when_text_fits(LCDHwdMock):
    menu = _menu(LCDHwdMock)

    menu.message("short\nalso short", autoscroll=True)

    # Nothing is longer than the display, so there is a single frame with no
    # pacing delay even though autoscroll was requested.
    assert _queued_frames(menu) == [_frame("short", "also short")]
    assert _queued_delays(menu) == [0.0]


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_rpilcdmenu_message_clears_pending_frames(LCDHwdMock):
    menu = _menu(LCDHwdMock)

    menu.message("first")
    menu.message("second")

    # A new message drops whatever was still queued from the previous one.
    assert _queued_frames(menu) == [_frame("second")]


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_rpilcdmenu_render_autoscrolls_when_scrolling_menu_enabled(LCDHwdMock):
    menu = _menu(LCDHwdMock, scrolling_menu=True)
    menu.append_item(_item("a really long menu item that overflows"))

    menu.render()

    # The long item produces a scrolling sequence rather than a single frame.
    assert len(_queued_frames(menu)) > 1


# --- worker pacing ---------------------------------------------------------

class _StopLoop(Exception):
    """Sentinel used to break the worker's infinite loop in tests."""


@patch('rpilcdmenu.rpi_lcd_menu.sleep')
@patch('rpilcdmenu.rpi_lcd_menu.monotonic')
@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_worker_subtracts_render_time_from_delay(LCDHwdMock, monotonic_mock, sleep_mock):
    menu = _menu(LCDHwdMock)
    menu.lcd_queue = Mock()
    menu.lcd_queue.get.side_effect = [("frame\nframe", 0.2), _StopLoop()]
    monotonic_mock.side_effect = [10.0, 10.05]  # rendering took 50ms

    with pytest.raises(_StopLoop):
        menu._lcd_queue_processor()

    # Slept only for the remainder of the 0.2s step, not the full 0.2s.
    sleep_mock.assert_called_once_with(pytest.approx(0.15))


@patch('rpilcdmenu.rpi_lcd_menu.sleep')
@patch('rpilcdmenu.rpi_lcd_menu.monotonic')
@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_worker_skips_sleep_when_render_outlasts_delay(LCDHwdMock, monotonic_mock, sleep_mock):
    menu = _menu(LCDHwdMock)
    menu.lcd_queue = Mock()
    menu.lcd_queue.get.side_effect = [("frame\nframe", 0.2), _StopLoop()]
    monotonic_mock.side_effect = [10.0, 10.5]  # rendering overran the 0.2s step

    with pytest.raises(_StopLoop):
        menu._lcd_queue_processor()

    sleep_mock.assert_not_called()


# --- display toggle ---------------------------------------------------------

@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_display_off_sets_flag_and_calls_hardware(LCDHwdMock):
    menu = _menu(LCDHwdMock)

    menu.display_off()

    assert menu._display_off is True
    menu.lcd.display_off.assert_called_once()


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_display_on_clears_flag_and_calls_hardware(LCDHwdMock):
    menu = _menu(LCDHwdMock)
    menu._display_off = True

    menu.display_on()

    assert menu._display_off is False
    menu.lcd.display_on.assert_called_once()


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_display_on_rerenders_last_frame(LCDHwdMock):
    menu = _menu(LCDHwdMock)
    menu._display_off = True
    menu._last_frame = _frame("hello")
    menu.lcd_render = Mock()

    menu.display_on()

    menu.lcd_render.assert_called_once_with(_frame("hello"))


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_display_on_skips_rerender_when_no_last_frame(LCDHwdMock):
    menu = _menu(LCDHwdMock)
    menu._display_off = True
    menu.lcd_render = Mock()

    menu.display_on()

    menu.lcd_render.assert_not_called()


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_toggle_display_turns_off_when_on(LCDHwdMock):
    menu = _menu(LCDHwdMock)

    menu.toggle_display()

    assert menu._display_off is True
    menu.lcd.display_off.assert_called_once()


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_toggle_display_turns_on_when_off(LCDHwdMock):
    menu = _menu(LCDHwdMock)
    menu._display_off = True

    menu.toggle_display()

    assert menu._display_off is False
    menu.lcd.display_on.assert_called_once()


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_worker_skips_lcd_render_when_display_is_off(LCDHwdMock):
    menu = _menu(LCDHwdMock)
    menu._display_off = True
    menu.lcd_queue = Mock()
    menu.lcd_queue.get.side_effect = [(_frame("hello"), 0.0), _StopLoop()]
    menu.lcd_render = Mock()

    with pytest.raises(_StopLoop):
        menu._lcd_queue_processor()

    menu.lcd_render.assert_not_called()


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_worker_tracks_last_frame_when_display_is_on(LCDHwdMock):
    menu = _menu(LCDHwdMock)
    menu.lcd_queue = Mock()
    frame = _frame("hello")
    menu.lcd_queue.get.side_effect = [(frame, 0.0), _StopLoop()]

    with pytest.raises(_StopLoop):
        menu._lcd_queue_processor()

    assert menu._last_frame == frame


def _menu_with_resync(LCDHwdMock, interval):
    LCDHwdMock.return_value = MagicMock()
    return RpiLCDMenu(start_worker=False, resync_interval=interval)


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_lcd_render_resyncs_the_controller_every_interval_frames(LCDHwdMock):
    menu = _menu_with_resync(LCDHwdMock, 3)
    menu.lcd.reset_mock()

    for _ in range(3):
        menu.lcd_render(_frame("x"))
    menu.lcd.resync.assert_not_called()

    menu.lcd_render(_frame("x"))
    menu.lcd.resync.assert_called_once()


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_lcd_render_never_resyncs_when_the_interval_is_zero(LCDHwdMock):
    menu = _menu_with_resync(LCDHwdMock, 0)
    menu.lcd.reset_mock()

    for _ in range(50):
        menu.lcd_render(_frame("x"))

    menu.lcd.resync.assert_not_called()


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_resync_reloads_the_defined_glyphs(LCDHwdMock):
    # CGRAM is as exposed to a desynced bus as the screen is, and the meter is
    # drawn entirely out of it, so a resync that left the glyphs alone would
    # leave the corruption in place.
    menu = _menu_with_resync(LCDHwdMock, 600)
    bitmap = [0x1F] * 8
    menu.create_char(2, bitmap)
    menu.lcd.reset_mock()

    menu.resync_display()

    menu.lcd.resync.assert_called_once()
    menu.lcd.create_char.assert_called_once_with(2, bitmap)


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_resync_display_redraws_the_last_frame(LCDHwdMock):
    menu = _menu_with_resync(LCDHwdMock, 600)
    menu.render_frame(_frame("hello"))
    menu.lcd.reset_mock()

    menu.resync_display()

    # Resyncing does not clear the screen, so the redraw is what actually gets
    # the garbage off it.
    assert call(ord("h"), True) in menu.lcd.write4bits.mock_calls


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_resync_display_does_not_redraw_while_the_display_is_off(LCDHwdMock):
    menu = _menu_with_resync(LCDHwdMock, 600)
    menu.render_frame(_frame("hello"))
    menu.display_off()
    menu.lcd.reset_mock()

    menu.resync_display()

    menu.lcd.resync.assert_called_once()
    menu.lcd.write4bits.assert_not_called()


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_clearDisplay_forgets_the_last_frame(LCDHwdMock):
    menu = _menu_with_resync(LCDHwdMock, 600)
    menu.render_frame(_frame("hello"))

    menu.clearDisplay()

    assert menu._last_frame is None


@patch('rpilcdmenu.rpi_lcd_menu.RpiLCDHwd')
def test_clearDisplay_takes_the_display_lock(LCDHwdMock):
    # retrotuner-ui fires this off a threading.Timer, so it races the worker
    # thread on the data pins unless it locks -- two writers is a guaranteed
    # nibble desync.
    menu = _menu_with_resync(LCDHwdMock, 600)
    held = []
    menu.lcd.write4bits.side_effect = lambda *a, **k: held.append(menu._lcd_lock.locked())

    menu.clearDisplay()

    assert held == [True]
