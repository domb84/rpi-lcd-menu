"""End-to-end check that a lost nibble is survivable.

The driver has no RW line, so it can never read the busy flag and every delay
in it is a fixed guess. When one of those guesses is wrong the controller drops
a nibble and the 4-bit bus desyncs: from then on every byte is assembled from
the low nibble of one write and the high nibble of the next.

These tests run the real driver against a fake HD44780 that models that
pairing, so the failure can be reproduced (and the recovery proved) without the
hardware. The symptom the fake reproduces is the one the display actually
showed: line 2 freezing while line 1 flickers, because the "move to line 2"
command is never seen intact and all 32 characters of every frame land on
line 1.
"""

from unittest.mock import patch

import pytest

from rpilcdmenu.rpi_lcd_menu import RpiLCDMenu

PIN_RS, PIN_E = 1, 2
PINS_DB = [3, 4, 5, 6]

LINE1_ADDR = 0x00
LINE2_ADDR = 0x40


class FakeHD44780:
    """A GPIO stand-in that decodes the bus the way the controller does.

    Only the parts this driver exercises: 8/4-bit mode, DDRAM addressing,
    clear, home, and character writes. ``drop_next_nibble`` is the fault
    injection -- exactly one nibble vanishes, as if an enable pulse had been
    too short to be seen.
    """

    BCM = 'BCM'
    OUT = 'out'

    def __init__(self):
        self.mode_8bit = True  # the controller's power-on default
        self.pending = None
        self.enable = False
        self.rs = False
        self.data = [False] * len(PINS_DB)
        self.drop_next_nibble = False

        self.ddram = bytearray(b' ' * 0x80)
        self.cursor = LINE1_ADDR
        self.bytes_seen = []

    # -- GPIO surface -----------------------------------------------------
    def setwarnings(self, _flag):
        pass

    def setmode(self, _mode):
        pass

    def setup(self, _pin, _direction):
        pass

    def output(self, pin, value):
        value = bool(value)
        if pin == PIN_RS:
            self.rs = value
        elif pin == PIN_E:
            if self.enable and not value:  # data is latched on the falling edge
                self._latch_nibble()
            self.enable = value
        else:
            self.data[PINS_DB.index(pin)] = value

    # -- controller behaviour ---------------------------------------------
    def _latch_nibble(self):
        nibble = sum(1 << i for i, bit in enumerate(self.data) if bit)

        if self.drop_next_nibble:
            self.drop_next_nibble = False
            return

        if self.mode_8bit:
            # In 8-bit mode DB0-DB3 are not wired, so only the high nibble of
            # the byte ever arrives and every latch is a complete byte.
            self._execute(self.rs, nibble << 4)
        elif self.pending is None:
            self.pending = nibble
        else:
            self._execute(self.rs, (self.pending << 4) | nibble)
            self.pending = None

    def _execute(self, rs, value):
        self.bytes_seen.append((rs, value))

        if rs:
            self.ddram[self.cursor] = value
            self.cursor = (self.cursor + 1) % 0x80
            return

        if value & 0xE0 == 0x20:  # function set
            self.mode_8bit = bool(value & 0x10)
            self.pending = None
        elif value & 0x80:  # set DDRAM address
            self.cursor = value & 0x7F
        elif value & 0xFE == 0x02:  # return home
            self.cursor = LINE1_ADDR
        elif value == 0x01:  # clear display
            self.ddram = bytearray(b' ' * 0x80)
            self.cursor = LINE1_ADDR

    def screen(self):
        line1 = self.ddram[LINE1_ADDR:LINE1_ADDR + 16].decode('latin-1')
        line2 = self.ddram[LINE2_ADDR:LINE2_ADDR + 16].decode('latin-1')
        return [line1, line2]


@pytest.fixture
def menu():
    """A real menu driving the fake controller, with the delays stubbed out.

    The delays are what make this driver slow (sleep() has a floor of tens of
    microseconds on Linux and 15ms on Windows), and nothing here is timing
    dependent -- the fake latches on edges, not on the clock.
    """
    gpio = FakeHD44780()
    with patch('rpilcdmenu.rpi_lcd_hwd.sleep'):
        menu = RpiLCDMenu(PIN_RS, PIN_E, PINS_DB, gpio, start_worker=False)
        menu.lcd.busyWaitMicroseconds = lambda _us: None
        yield menu, gpio


def _frame(line1, line2):
    return "%s\n%s" % (line1.ljust(16), line2.ljust(16))


def test_frames_render_to_both_lines_while_the_bus_is_in_step(menu):
    menu, gpio = menu

    menu.render_frame(_frame("first line", "second line"))

    assert gpio.screen() == ["first line      ", "second line     "]


def test_a_single_lost_nibble_kills_the_second_line(menu):
    # The reported symptom, reproduced: one dropped nibble and every byte after
    # it is misassembled, so the 0xC0 that selects line 2 is never seen and all
    # 32 characters pile onto line 1. Nothing detects this and nothing recovers
    # from it -- before resync() existed, only restarting the process did.
    menu, gpio = menu
    menu.render_frame(_frame("first line", "second line"))

    gpio.drop_next_nibble = True
    menu.render_frame(_frame("new content", "new second line"))

    assert gpio.screen()[1] == "second line     "  # frozen at the old frame
    assert gpio.screen()[0] != "new content     "

    # ...and it stays broken for every frame after, not just the one that
    # dropped the nibble.
    menu.render_frame(_frame("later frame", "later second"))
    assert gpio.screen()[1] == "second line     "


def test_resync_recovers_the_bus_within_one_frame(menu):
    menu, gpio = menu
    gpio.drop_next_nibble = True
    menu.render_frame(_frame("garbled", "garbled"))

    menu.resync_display()

    assert gpio.mode_8bit is False
    assert gpio.screen() == ["garbled         ", "garbled         "]


def test_the_periodic_resync_recovers_the_bus_on_its_own(menu):
    # No caller has to notice anything is wrong: the resync that lcd_render
    # runs every RESYNC_FRAME_INTERVAL frames is enough on its own, which is
    # the whole point -- a desync is undetectable from this side of the bus.
    menu, gpio = menu
    menu._resync_interval = 3

    gpio.drop_next_nibble = True
    for _ in range(5):
        menu.render_frame(_frame("steady", "state"))

    assert gpio.screen() == ["steady          ", "state           "]


def test_resync_restores_the_glyphs_a_desync_may_have_corrupted(menu):
    menu, gpio = menu
    bitmap = [0x11] * 8
    menu.create_char(0, bitmap)

    gpio.drop_next_nibble = True
    menu.render_frame(_frame("bars", "bars"))

    mark = len(gpio.bytes_seen)
    menu.resync_display()

    # CGRAM is as exposed to a desynced bus as the screen is, and the meter is
    # drawn entirely out of it, so the resync has to rewrite the glyphs too.
    during_resync = gpio.bytes_seen[mark:]
    start = during_resync.index((False, 0x40)) + 1
    assert [value for _rs, value in during_resync[start:start + 8]] == bitmap
