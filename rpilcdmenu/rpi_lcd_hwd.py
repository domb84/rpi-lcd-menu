from time import sleep


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

    def __init__(self, pin_rs=26, pin_e=19, pins_db=[13, 6, 5, 21], GPIO=None,
                 command_delay_us=COMMAND_DELAY_US):
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
        # Power-on init needs generous settle times; normal writes do not, so
        # these longer delays live here rather than in write4bits.
        self.delayMicroseconds(15000)  # wait > 15ms after Vcc rises
        self.write4bits(0x33)  # initialization
        self.delayMicroseconds(4500)   # wait > 4.1ms
        self.write4bits(0x32)  # initialization
        self.delayMicroseconds(150)
        self.write4bits(0x28)  # 2 line 5x7 matrix
        self.write4bits(0x0C)  # turn cursor off 0x0E to enable cursor
        self.write4bits(0x06)  # shift cursor right

        self.displaycontrol = self.LCD_DISPLAYON | self.LCD_CURSOROFF | self.LCD_BLINKOFF
        self.displayfunction = self.LCD_4BITMODE | self.LCD_1LINE | self.LCD_5x8DOTS
        self.displayfunction |= self.LCD_2LINE

        # Initialize to default text direction (for romance languages)
        self.displaymode = self.LCD_ENTRYLEFT | self.LCD_ENTRYSHIFTDECREMENT
        self.write4bits(self.LCD_ENTRYMODESET | self.displaymode)  # set the entry mode

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

    def pulseEnable(self):
        # The enable pulse must be > 450ns and commands need > 37us to settle.
        self.GPIO.output(self.pin_e, False)
        self.delayMicroseconds(1)
        self.GPIO.output(self.pin_e, True)
        self.delayMicroseconds(1)
        self.GPIO.output(self.pin_e, False)
        self.delayMicroseconds(1)

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
