import queue
import threading
from time import monotonic, sleep

from rpilcdmenu.base_menu import BaseMenu
from rpilcdmenu.rpi_lcd_hwd import RpiLCDHwd

LCD_COLUMNS = 16
LCD_SECOND_LINE = 0xC0  # DDRAM address of the start of the second line


class RpiLCDMenu(BaseMenu):
    # Pacing for autoscroll, in seconds. SCROLL_HOLD is how long the first
    # frame stays on screen before scrolling starts; SCROLL_INTERVAL is the
    # period of each subsequent scroll step. Both are total per-frame times:
    # the worker subtracts the time spent rendering the frame so the on-screen
    # cadence matches these values rather than (render_time + value). Both run
    # on the worker thread so callers never block. Tune these to taste.
    SCROLL_HOLD = 1.0
    SCROLL_INTERVAL = 0.1

    def __init__(self, pin_rs=26, pin_e=19, pins_db=[13, 6, 5, 21], GPIO=None,
                 scrolling_menu=False, start_worker=True):
        """
        Initialize menu
        """
        super().__init__()

        self.scrolling_menu = scrolling_menu
        self.lcd_queue = queue.Queue()

        # Build and initialise the display up front (on this thread) so there is
        # no window where self.lcd is missing while the worker spins up.
        self.lcd = RpiLCDHwd(pin_rs, pin_e, pins_db, GPIO)
        self.lcd.initDisplay()
        self.clearDisplay()  # clear once in case of existing corruption

        self.worker = None
        if start_worker:
            self.worker = threading.Thread(target=self._lcd_queue_processor, daemon=True)
            self.worker.start()

    def clearDisplay(self):
        """
        Clear LCD Screen
        """
        self.lcd.write4bits(RpiLCDHwd.LCD_CLEARDISPLAY)
        self.lcd.delayMicroseconds(3000)  # clearing the display takes a long time

        return self

    def lcd_render(self, render_text):
        """Render a pre-formatted "<line1>\n<line2>" string to the display."""
        # Return home rather than clear, to avoid the long clear-display delay
        # and the flicker it causes.
        self.lcd.write4bits(RpiLCDHwd.LCD_RETURNHOME)

        for char in render_text:
            if char == '\n':
                self.lcd.write4bits(LCD_SECOND_LINE)
            else:
                self.lcd.write4bits(ord(char), True)

    def message(self, text, autoscroll=False):
        """Show text on the display.

        A single line longer than the display is split across both lines. When
        ``autoscroll`` is set, lines longer than the display scroll right to
        left; otherwise they are cropped.
        """
        self._clear_queue()

        frames = self.build_frames(text, autoscroll)
        scrolling = len(frames) > 1
        for index, frame in enumerate(frames):
            if not scrolling:
                delay = 0.0
            elif index == 0:
                delay = self.SCROLL_HOLD
            else:
                delay = self.SCROLL_INTERVAL
            self.lcd_queue.put((frame, delay))

        return self

    def build_frames(self, text, autoscroll=False):
        """Return the list of 16x2 frame strings needed to display ``text``."""
        final_text, len1, len2 = self._layout(text)
        frames = [self.render_16x2(final_text)]

        text_length = max(len1, len2)
        if not autoscroll or text_length <= LCD_COLUMNS:
            return frames

        # Scroll the text off to the left, then bring it back from the right.
        for index in range(1, text_length + 1):
            frames.append(self.render_16x2(final_text, index))
        for index in range(LCD_COLUMNS):
            frames.append(self.render_16x2_reverse(final_text, index))
        frames.append(self.render_16x2(final_text))

        return frames

    def _layout(self, text):
        """Normalise ``text`` to a "<line1>\n<line2>" string plus raw lengths.

        The lengths are the unpadded line lengths, used to decide how far to
        scroll.
        """
        lines = text.split('\n')

        if len(lines) == 1:
            line1 = lines[0]
            if len(line1) > LCD_COLUMNS:
                # split on the first space past the midpoint, keeping words whole
                split = line1.find(' ', len(line1) // 2) + 1
                line2 = line1[split:].ljust(len(line1[:split]))
                line1 = line1[:split]
            else:
                line2 = ''
        else:
            # Two (or more, cropped to two) explicit lines, padded to width.
            line1, line2 = lines[0], lines[1]

        len1, len2 = len(line1), len(line2)
        final_text = f"{line1.ljust(LCD_COLUMNS)}\n{line2.ljust(LCD_COLUMNS)}"
        return final_text, len1, len2

    def displayTestScreen(self):
        """
        Display test screen to see if your LCD screen is working
        """
        self.message('Hum. body 36,6\xDFC\nThis is test')

        return self

    def render(self):
        """
        Render menu
        """
        if len(self.items) == 0:
            self.message('Menu is empty')
            return self

        if len(self.items) <= 2:
            options = (">" if self.current_option == 0 else " ") + self.items[0].text
            if len(self.items) == 2:
                options += "\n" + (">" if self.current_option == 1 else " ") + self.items[1].text
        else:
            options = ">" + self.items[self.current_option].text
            next_option = (self.current_option + 1) % len(self.items)
            options += "\n " + self.items[next_option].text

        self.message(options, autoscroll=self.scrolling_menu)
        return self

    def render_16x2(self, text, index=0):
        """Left-justified 16x2 frame, sliced from ``index`` (forward scroll)."""
        return self._slice_frame(text, slice(index, index + LCD_COLUMNS), '<')

    def render_16x2_reverse(self, text, index=0):
        """Right-justified 16x2 frame, showing ``[:index]`` (reverse scroll)."""
        return self._slice_frame(text, slice(0, index), '>')

    def _slice_frame(self, text, window, align):
        # Incoming text has already been cleaned up and split with a line break
        # by _layout(), so it always has (at least) two lines.
        lines = text.split('\n')
        line1 = f"{lines[0][window]:{align}{LCD_COLUMNS}}"
        line2 = f"{lines[1][window]:{align}{LCD_COLUMNS}}"
        return f"{line1}\n{line2}"

    def _clear_queue(self):
        """Drop any frames still waiting to be rendered."""
        try:
            while True:
                self.lcd_queue.get_nowait()
                self.lcd_queue.task_done()
        except queue.Empty:
            pass

    def _lcd_queue_processor(self):
        while True:
            frame, delay = self.lcd_queue.get()
            start = monotonic()
            self.lcd_render(frame)
            self.lcd_queue.task_done()
            # ``delay`` is the desired total time the frame is on screen, so
            # discount the time already spent rendering it. If rendering took
            # longer than ``delay`` we just move on with no extra sleep.
            if delay:
                remaining = delay - (monotonic() - start)
                if remaining > 0:
                    sleep(remaining)
