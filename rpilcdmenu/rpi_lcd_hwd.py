from time import perf_counter, sleep


class RpiLCDHwd:

    # commands
    LCD_CLEARDISPLAY = 0x01
    LCD_RETURNHOME = 0x02
    LCD_ENTRYMODESET = 0x04
    LCD_DISPLAYCONTROL = 0x08
    LCD_CURSORSHIFT = 0x10
    LCD_FUNCTIONSET = 0x20
    LCD_SETCGRAMADDR = 0x40
    LCD_SETDDRAMADDR = 0x80

    # flags for display entry mode
    LCD_ENTRYRIGHT = 0x00
    LCD_ENTRYLEFT = 0x02
    LCD_ENTRYSHIFTINCREMENT = 0x01
    LCD_ENTRYSHIFTDECREMENT = 0x00

    # flags for display on/off control
    LCD_DISPLAYON = 0x04
    LCD_DISPLAYOFF = 0x00
    LCD_CURSORON = 0x02
    LCD_CURSOROFF = 0x00
    LCD_BLINKON = 0x01
    LCD_BLINKOFF = 0x00

    # flags for display/cursor shift
    LCD_DISPLAYMOVE = 0x08
    LCD_CURSORMOVE = 0x00
    LCD_MOVERIGHT = 0x04
    LCD_MOVELEFT = 0x00

    # flags for function set
    LCD_8BITMODE = 0x10
    LCD_4BITMODE = 0x00
    LCD_2LINE = 0x08
    LCD_1LINE = 0x00
    LCD_5x10DOTS = 0x04
    LCD_5x8DOTS = 0x00

    # Time to let a normal command settle. The HD44780 needs ~37us for most
    # instructions; clear/home need ~1.5ms and are paced by their callers.
    COMMAND_DELAY_US = 50

    # How long E is held high, and how long it is held low afterwards, in
    # microseconds. The datasheet minimums are 450ns high and a 1us full cycle,
    # so 1us for each satisfies both with margin. See pulseEnable().
    ENABLE_PULSE_US = 1

    # How long RETURNHOME and CLEARDISPLAY take to execute (~1.52ms).
    LONG_COMMAND_DELAY_US = 2000

    def __init__(self, pin_rs=26, pin_e=19, pins_db=[13, 6, 5, 21], GPIO=None,
                 command_delay_us=COMMAND_DELAY_US,
                 enable_pulse_us=ENABLE_PULSE_US):
        """
        LCD GPIO configuration
        """
        if not GPIO:
            import RPi.GPIO as GPIO
            GPIO.setwarnings(False)

        self.GPIO = GPIO
        self.pin_rs = pin_rs
        self.pin_e = pin_e
        self.pins_db = pins_db
        self.command_delay_us = command_delay_us
        self.enable_pulse_us = enable_pulse_us

        self.displaycontrol = None
        self.displayfunction = None
        self.displaymode = None
        self.display_toggle = 'on'

        self.GPIO.setmode(GPIO.BCM)
        self.GPIO.setup(self.pin_rs, GPIO.OUT)
        self.GPIO.setup(self.pin_e, GPIO.OUT)
        for pin in self.pins_db:
            self.GPIO.setup(pin, GPIO.OUT)

    def initDisplay(self):
        # Power-on init needs a generous settle time before the controller will
        # accept anything. Everything after that is the same handshake resync()
        # runs, so it lives there and can be repeated later.
        self.delayMicroseconds(15000)  # wait > 15ms after Vcc rises
        return self.resync()

    def resync(self):
        """Re-run the 4-bit handshake, recovering from a lost nibble.

        There is no RW line, so the busy flag can never be read and every delay
        in this driver is a fixed guess. When one of those guesses is wrong the
        controller misses (or gains) a nibble and the bus desyncs permanently:
        every following byte is assembled from the low nibble of one write and
        the high nibble of the next, so commands like "move to line 2" are never
        seen and nothing recovers on its own.

        The 0x33/0x32 sequence is the standard escape hatch. Between them they
        put the nibbles 3, 3, 3, 2 on the bus. Whichever of the two possible
        alignments the controller is on, some adjacent pair of those first three
        reads as the byte 0x33 -- "function set, 8-bit" -- which puts it in
        8-bit mode, where a byte is one nibble and alignment stops meaning
        anything. The trailing 0x2 is then read as 0x20, "function set, 4-bit",
        and it comes back into 4-bit mode in step with us.

        DDRAM survives this, so the display keeps its contents. Callers should
        redraw anyway, since whatever garbage prompted the resync is still on
        screen. RETURNHOME at the end resets the display shift, which a spurious
        shift command could otherwise have left set for good -- setting the
        DDRAM address does not undo it.
        """
        self.write4bits(0x33)  # initialization
        self.delayMicroseconds(4500)   # wait > 4.1ms
        self.write4bits(0x32)  # initialization
        self.delayMicroseconds(150)

        if self.displayfunction is None:
            self.displayfunction = self.LCD_4BITMODE | self.LCD_5x8DOTS | self.LCD_2LINE
        if self.displaycontrol is None:
            self.displaycontrol = self.LCD_DISPLAYON | self.LCD_CURSOROFF | self.LCD_BLINKOFF
        if self.displaymode is None:
            # Default text direction (for romance languages)
            self.displaymode = self.LCD_ENTRYLEFT | self.LCD_ENTRYSHIFTDECREMENT

        self.write4bits(self.LCD_FUNCTIONSET | self.displayfunction)  # 2 line 5x7 matrix
        # Resend the current control and entry state rather than hardcoded
        # defaults, so a resync while the display is switched off does not
        # switch it back on behind the caller.
        self.write4bits(self.LCD_DISPLAYCONTROL | self.displaycontrol)
        self.write4bits(self.LCD_ENTRYMODESET | self.displaymode)

        self.write4bits(self.LCD_RETURNHOME)
        self.delayMicroseconds(self.LONG_COMMAND_DELAY_US)

        return self

    def write4bits(self, bits, char_mode=False):
        """Send a byte to the LCD, high nibble first, over the 4-bit data bus.

        ``pins_db[i]`` is wired to data line DB(4 + i), so for each nibble we
        drive every data pin directly from the corresponding bit of ``bits``.
        """
        self.delayMicroseconds(self.command_delay_us)
        self.GPIO.output(self.pin_rs, char_mode)

        for shift in (4, 0):  # high nibble, then low nibble
            for i, pin in enumerate(self.pins_db):
                self.GPIO.output(pin, bool((bits >> (shift + i)) & 1))
            self.pulseEnable()

        return self

    def create_char(self, location, bitmap):
        """Define one of the 8 user characters in CGRAM.

        ``location`` is 0-7 and becomes the character code you write to show it
        (so chr(location) in a render string). ``bitmap`` is 8 rows of 5 pixels,
        each an int whose low 5 bits are the row, top row first.

        The HD44780 only has these 8 slots, so anything drawn from them has to
        reuse the same glyphs across the screen -- fine for bar graphs, which is
        what this exists for.
        """
        location &= 0x07
        self.write4bits(self.LCD_SETCGRAMADDR | (location << 3))
        for row in bitmap:
            self.write4bits(row & 0x1F, True)

        # Leave the controller addressing display RAM again, otherwise the next
        # character written would land in CGRAM and corrupt the glyph.
        self.write4bits(self.LCD_SETDDRAMADDR)

        return self

    def delayMicroseconds(self, microseconds):
        sleep(microseconds / 1000000.0)
        return self

    def busyWaitMicroseconds(self, microseconds):
        """Spin for ``microseconds``, for waits too short to sleep through.

        sleep() has a floor of tens of microseconds on Linux however small a
        value it is given, so it cannot express a sub-microsecond hold at all.
        Spinning on perf_counter() can: the loop costs a few hundred nanoseconds
        an iteration and burns CPU rather than yielding it, which is the right
        trade only for the ~1us holds in pulseEnable().
        """
        end = perf_counter() + microseconds / 1000000.0
        while perf_counter() < end:
            pass
        return self

    def pulseEnable(self):
        """Clock one nibble into the controller on the falling edge of E.

        E must be held high > 450ns and the full cycle must be > 1us. Those
        holds are busy-waits, not sleeps: sleep() cannot deliver a wait this
        short (its floor is tens of microseconds, which is why the three nominal
        1us delays that used to be here cost ~180us per nibble and dominated
        every write), but leaving the edges unguarded does not work either.
        Between those two versions this held E for exactly as long as one
        RPi.GPIO output call happened to take -- 0.4-2us depending on CPU clock,
        cache and contention, and shortest under sustained rendering, when the
        governor is pinned at full clock. That is Python overhead, not a
        guarantee, and undershooting it once desyncs the bus until resync().

        Data setup ahead of the rising edge is covered by the GPIO call that
        drives E low; the hold after the falling edge covers both data hold and
        the minimum cycle time before the next nibble.

        The 37us an instruction needs to settle is not this function's job --
        write4bits waits command_delay_us before each byte.
        """
        self.GPIO.output(self.pin_e, False)
        self.GPIO.output(self.pin_e, True)
        self.busyWaitMicroseconds(self.enable_pulse_us)
        self.GPIO.output(self.pin_e, False)
        self.busyWaitMicroseconds(self.enable_pulse_us)

        return self

    def display_off(self):
        """Turn off the display without clearing DDRAM content."""
        if self.displaycontrol is None:
            return self
        self.displaycontrol &= ~self.LCD_DISPLAYON
        self.write4bits(self.LCD_DISPLAYCONTROL | self.displaycontrol)
        self.display_toggle = 'off'
        return self

    def display_on(self):
        """Turn on the display, restoring content from DDRAM."""
        if self.displaycontrol is None:
            return self
        self.displaycontrol |= self.LCD_DISPLAYON
        self.write4bits(self.LCD_DISPLAYCONTROL | self.displaycontrol)
        self.display_toggle = 'on'
        return self

    def displayToggle(self):
        if self.display_toggle == 'on':
            self.display_off()
        else:
            self.display_on()
        return self
