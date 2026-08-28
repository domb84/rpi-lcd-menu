import pytest
import sys
import datetime
from time import perf_counter
from unittest.mock import Mock, MagicMock, patch, call

from rpilcdmenu.rpi_lcd_hwd import RpiLCDHwd


def test_rpilcdhwd_cannot_be_initialized_without_gpio_support():
    with patch.dict(sys.modules, {'RPi.GPIO': None}):
        with pytest.raises(ImportError):
            RpiLCDHwd()


def test_rpilcdhwd_imports_gpio_and_initializes_provided_gpio_pins_in_bcm_mode():
    GPIO_mock = Mock()
    GPIO_mock.setup = Mock()
    GPIO_mock.OUT = 'out'
    GPIO_mock.IN = 'in'
    GPIO_mock.BCM = 'BCM'
    GPIO_mock.setmode = Mock()
    RPi_mock = Mock()
    RPi_mock.GPIO = GPIO_mock

    with patch.dict(sys.modules, {'RPi': RPi_mock, 'RPi.GPIO': Mock()}):
        RpiLCDHwd(1, 2, [3, 4, 5, 6])

        GPIO_mock.setmode.assert_called_once_with(GPIO_mock.BCM)

        setup_calls = [
            call(1, GPIO_mock.OUT),
            call(2, GPIO_mock.OUT),
            call(3, GPIO_mock.OUT),
            call(4, GPIO_mock.OUT),
            call(5, GPIO_mock.OUT),
            call(6, GPIO_mock.OUT)
        ]

        GPIO_mock.setup.assert_has_calls(setup_calls, any_order=True)


def test_rpilcdhwd_initDisplay_configures_proper_lcd_settings():
    RPi_mock = Mock()
    RPi_mock.GPIO = MagicMock()

    with patch.dict(sys.modules, {'RPi': RPi_mock, 'RPi.GPIO': Mock()}):
        lcd = RpiLCDHwd(1, 2, [3, 4, 5, 6])

        lcd.write4bits = Mock()
        lcd.initDisplay()

        assert lcd.write4bits.mock_calls == [
            call(0x33),           # force 8-bit, then
            call(0x32),           # back down to 4-bit, in step
            call(0x28),           # function set: 4-bit, 2 line, 5x8
            call(0x0C),           # display on, cursor off, blink off
            call(0x06),           # entry mode: left to right, no shift
            call(0x02),           # return home, resetting the display shift
        ]


def test_rpilcdhwd_resync_repeats_the_handshake_without_the_power_on_wait():
    RPi_mock = Mock()
    RPi_mock.GPIO = MagicMock()

    with patch.dict(sys.modules, {'RPi': RPi_mock, 'RPi.GPIO': Mock()}):
        lcd = RpiLCDHwd(1, 2, [3, 4, 5, 6])

        lcd.write4bits = Mock()
        lcd.delayMicroseconds = Mock()
        lcd.resync()

        assert lcd.write4bits.mock_calls == [
            call(0x33), call(0x32), call(0x28), call(0x0C), call(0x06), call(0x02),
        ]
        # The 15ms Vcc settle belongs to power-on only; a resync happens mid-run
        # and would drop a frame for nothing.
        assert call(15000) not in lcd.delayMicroseconds.mock_calls


def test_rpilcdhwd_resync_does_not_switch_a_disabled_display_back_on():
    # A resync while the display is off (the dimmer) must not undo that: it
    # resends the control byte it already holds, not the power-on default.
    RPi_mock = Mock()
    RPi_mock.GPIO = MagicMock()

    with patch.dict(sys.modules, {'RPi': RPi_mock, 'RPi.GPIO': Mock()}):
        lcd = RpiLCDHwd(1, 2, [3, 4, 5, 6])
        lcd.initDisplay()
        lcd.display_off()

        lcd.write4bits = Mock()
        lcd.resync()

        assert call(RpiLCDHwd.LCD_DISPLAYCONTROL | RpiLCDHwd.LCD_CURSOROFF
                    | RpiLCDHwd.LCD_BLINKOFF) in lcd.write4bits.mock_calls
        assert lcd.display_toggle == 'off'


def test_rpilcdmenu_write4bits_transfers_data_through_GPIO():
    RPi_mock = Mock()
    RPi_mock.GPIO = Mock()
    RPi_mock.GPIO.output = Mock()

    with patch.dict(sys.modules, {'RPi': RPi_mock, 'RPi.GPIO': Mock()}):
        lcd = RpiLCDHwd(1, 2, [3, 4, 5, 6])

        lcd.delayMicroseconds = Mock()
        lcd.pulseEnable = Mock()

        # 0x123 is masked to a byte (0x23); pins_db[i] -> data line DB(4 + i).
        # RS is driven, then the high nibble, then the low nibble.
        lcd.write4bits(0x123)
        assert RPi_mock.GPIO.output.mock_calls == [
            call(1, False),
            # high nibble of 0x23: DB4..DB7 = 0,0,1,0
            call(3, False),
            call(4, True),
            call(5, False),
            call(6, False),
            # low nibble of 0x23: DB4..DB7 = 1,1,0,0
            call(3, True),
            call(4, True),
            call(5, False),
            call(6, False),
        ]


def test_rpilcdmenu_delayMicroseconds_waits_given_microseconds():
    RPi_mock = Mock()
    RPi_mock.GPIO = Mock()

    with patch.dict(sys.modules, {'RPi': RPi_mock, 'RPi.GPIO': Mock()}):
        lcd = RpiLCDHwd(1, 2, [3, 4, 5, 6])

        start_time = datetime.datetime.now()

        lcd.delayMicroseconds(10)

        assert (datetime.datetime.now() - start_time).microseconds >= 10


def test_rpilcdmenu_pulseEnable_is_blinking_pin_e():
    RPi_mock = Mock()
    RPi_mock.GPIO = Mock()
    RPi_mock.GPIO.output = Mock()

    with patch.dict(sys.modules, {'RPi': RPi_mock, 'RPi.GPIO': Mock()}):
        lcd = RpiLCDHwd(1, 2, [3, 4, 5, 6])

        lcd.pulseEnable()

        assert RPi_mock.GPIO.output.mock_calls == [call(2, False), call(2, True), call(2, False)]


def _lcd_with_mock():
    RPi_mock = Mock()
    RPi_mock.GPIO = MagicMock()
    with patch.dict(sys.modules, {'RPi': RPi_mock, 'RPi.GPIO': Mock()}):
        lcd = RpiLCDHwd(1, 2, [3, 4, 5, 6])
        lcd.write4bits = Mock()
        lcd.displaycontrol = RpiLCDHwd.LCD_DISPLAYON | RpiLCDHwd.LCD_CURSOROFF | RpiLCDHwd.LCD_BLINKOFF
        return lcd


def test_display_off_sends_displaycontrol_command_with_display_bit_cleared():
    lcd = _lcd_with_mock()

    lcd.display_off()

    lcd.write4bits.assert_called_once_with(
        RpiLCDHwd.LCD_DISPLAYCONTROL | RpiLCDHwd.LCD_CURSOROFF | RpiLCDHwd.LCD_BLINKOFF
    )
    assert lcd.display_toggle == 'off'


def test_display_on_sends_displaycontrol_command_with_display_bit_set():
    lcd = _lcd_with_mock()
    lcd.displaycontrol = RpiLCDHwd.LCD_CURSOROFF | RpiLCDHwd.LCD_BLINKOFF  # display bit cleared

    lcd.display_on()

    lcd.write4bits.assert_called_once_with(
        RpiLCDHwd.LCD_DISPLAYCONTROL | RpiLCDHwd.LCD_DISPLAYON | RpiLCDHwd.LCD_CURSOROFF | RpiLCDHwd.LCD_BLINKOFF
    )
    assert lcd.display_toggle == 'on'


def test_display_off_is_noop_before_init():
    lcd = _lcd_with_mock()
    lcd.displaycontrol = None

    lcd.display_off()

    lcd.write4bits.assert_not_called()


def test_displayToggle_delegates_to_display_off_and_display_on():
    lcd = _lcd_with_mock()
    lcd.display_off = Mock(return_value=lcd)
    lcd.display_on = Mock(return_value=lcd)

    lcd.display_toggle = 'on'
    lcd.displayToggle()
    lcd.display_off.assert_called_once()

    lcd.display_toggle = 'off'
    lcd.displayToggle()
    lcd.display_on.assert_called_once()


def test_rpilcdmenu_pulseEnable_does_not_sleep():
    # The enable holds must be busy-waits: sleep() has a floor of tens of
    # microseconds however small a value you pass it, so three nominal 1us
    # delays here used to dominate every byte written -- ~180us per nibble.
    RPi_mock = Mock()
    RPi_mock.GPIO = Mock()

    with patch.dict(sys.modules, {'RPi': RPi_mock, 'RPi.GPIO': Mock()}):
        lcd = RpiLCDHwd(1, 2, [3, 4, 5, 6])
        lcd.delayMicroseconds = Mock()

        lcd.pulseEnable()

        lcd.delayMicroseconds.assert_not_called()


def test_rpilcdmenu_pulseEnable_holds_e_high_for_the_configured_time():
    # ...but the pulse still has to be held. Without this the width is however
    # long one GPIO call happens to take, which shortens under load and drops
    # nibbles. Assert on the wait rather than the clock: a real timing
    # measurement here would be flaky on a loaded CI box.
    RPi_mock = Mock()
    RPi_mock.GPIO = Mock()

    with patch.dict(sys.modules, {'RPi': RPi_mock, 'RPi.GPIO': Mock()}):
        lcd = RpiLCDHwd(1, 2, [3, 4, 5, 6], enable_pulse_us=3)
        lcd.busyWaitMicroseconds = Mock()

        lcd.pulseEnable()

        # One hold with E high, one after the falling edge for the cycle time.
        assert lcd.busyWaitMicroseconds.mock_calls == [call(3), call(3)]


def test_rpilcdmenu_busyWaitMicroseconds_spins_for_at_least_the_requested_time():
    RPi_mock = Mock()
    RPi_mock.GPIO = Mock()

    with patch.dict(sys.modules, {'RPi': RPi_mock, 'RPi.GPIO': Mock()}):
        lcd = RpiLCDHwd(1, 2, [3, 4, 5, 6])

        start = perf_counter()
        lcd.busyWaitMicroseconds(50)
        assert perf_counter() - start >= 50 / 1000000.0


def test_rpilcdmenu_write4bits_still_paces_the_controller():
    # The 37us an instruction needs to settle comes from here, not pulseEnable.
    # Exactly one delay per byte, before the data goes out.
    RPi_mock = Mock()
    RPi_mock.GPIO = Mock()

    with patch.dict(sys.modules, {'RPi': RPi_mock, 'RPi.GPIO': Mock()}):
        lcd = RpiLCDHwd(1, 2, [3, 4, 5, 6])
        lcd.delayMicroseconds = Mock()

        lcd.write4bits(0x23)

        lcd.delayMicroseconds.assert_called_once_with(RpiLCDHwd.COMMAND_DELAY_US)
        assert lcd.delayMicroseconds.call_args_list[0] == call(50)


def test_brightness_defaults_to_full():
    lcd = _lcd_with_mock()

    assert lcd.brightness == 100


def test_set_brightness_folds_the_level_into_the_function_set():
    # 0x28 is the function set already in force, so on a display without the
    # attenuator these are a harmless re-issue of it.
    lcd = _lcd_with_mock()
    lcd.displayfunction = RpiLCDHwd.DEFAULT_DISPLAYFUNCTION

    for percent, expected in ((100, 0x28), (75, 0x29), (50, 0x2A), (25, 0x2B)):
        lcd.write4bits.reset_mock()
        lcd.set_brightness(percent)
        lcd.write4bits.assert_called_once_with(expected)
        assert lcd.brightness == percent


def test_set_brightness_refuses_levels_the_hardware_does_not_have():
    # 60% does not exist. Rounding it to 50 would hide a hardware limit behind
    # an API that looks continuous.
    lcd = _lcd_with_mock()
    lcd.displayfunction = RpiLCDHwd.DEFAULT_DISPLAYFUNCTION

    for bad in (0, 10, 37, 60, 80, 99):
        with pytest.raises(ValueError):
            lcd.set_brightness(bad)

    assert lcd.brightness == 100
    lcd.write4bits.assert_not_called()


def test_set_brightness_normalises_a_float_level_to_an_int():
    # The socket parses its argument with float(), so 75.0 arrives here.
    lcd = _lcd_with_mock()
    lcd.displayfunction = RpiLCDHwd.DEFAULT_DISPLAYFUNCTION

    lcd.set_brightness(75.0)

    assert lcd.brightness == 75
    assert isinstance(lcd.brightness, int)


def test_set_brightness_keeps_the_rest_of_the_function_set():
    # Clobbering the bus width or line count would take the display out with it.
    lcd = _lcd_with_mock()
    lcd.displayfunction = RpiLCDHwd.DEFAULT_DISPLAYFUNCTION

    lcd.set_brightness(25)

    assert lcd.displayfunction & ~RpiLCDHwd.LCD_BRIGHTNESS_MASK == \
        RpiLCDHwd.DEFAULT_DISPLAYFUNCTION


def test_set_brightness_rejects_values_off_the_scale():
    lcd = _lcd_with_mock()
    lcd.displayfunction = RpiLCDHwd.DEFAULT_DISPLAYFUNCTION

    for bad in (-1, 101, 1000):
        with pytest.raises(ValueError):
            lcd.set_brightness(bad)
    for bad in ('50', None, True):
        with pytest.raises(TypeError):
            lcd.set_brightness(bad)

    assert lcd.brightness == 100      # nothing was applied


def test_resync_preserves_brightness():
    # Why brightness lives in displayfunction: resync() resends it every
    # RESYNC_FRAME_INTERVAL frames, ~10s at 60fps.
    RPi_mock = Mock()
    RPi_mock.GPIO = MagicMock()

    with patch.dict(sys.modules, {'RPi': RPi_mock, 'RPi.GPIO': Mock()}):
        lcd = RpiLCDHwd(1, 2, [3, 4, 5, 6])
        lcd.initDisplay()
        lcd.set_brightness(50)

        lcd.write4bits = Mock()
        lcd.resync()

        assert call(0x2A) in lcd.write4bits.mock_calls
        assert lcd.brightness == 50


def test_brightness_set_before_init_is_applied_by_init():
    RPi_mock = Mock()
    RPi_mock.GPIO = MagicMock()

    with patch.dict(sys.modules, {'RPi': RPi_mock, 'RPi.GPIO': Mock()}):
        lcd = RpiLCDHwd(1, 2, [3, 4, 5, 6])
        lcd.set_brightness(25)      # nothing on the bus yet to write to

        lcd.write4bits = Mock()
        lcd.initDisplay()

        assert call(0x2B) in lcd.write4bits.mock_calls


def test_brightness_survives_the_display_being_switched_off_and_on():
    # Different registers: Function Set vs Display Control.
    lcd = _lcd_with_mock()
    lcd.displayfunction = RpiLCDHwd.DEFAULT_DISPLAYFUNCTION
    lcd.set_brightness(50)

    lcd.display_off()
    lcd.display_on()

    assert lcd.brightness == 50
    assert lcd.displayfunction & RpiLCDHwd.LCD_BRIGHTNESS_MASK == 2
