from time import sleep

from rpilcdmenu.base_menu import BaseMenu
from rpilcdmenu.rpi_lcd_hwd import RpiLCDHwd


class RpiLCDMenu(BaseMenu):
    def __init__(self, pin_rs=26, pin_e=19, pins_db=[13, 6, 5, 21], GPIO=None, scrolling_menu=False):
        """
        Initialize menu
        """

        self.scrolling_menu = scrolling_menu
        self.lcd = RpiLCDHwd(pin_rs, pin_e, pins_db, GPIO)

        self.lcd.initDisplay()
        self.clearDisplay()

        super(self.__class__, self).__init__()

    def clearDisplay(self):
        """
        Clear LCD Screen
        """
        self.lcd.write4bits(RpiLCDHwd.LCD_CLEARDISPLAY)  # command to clear display
        self.lcd.delayMicroseconds(3000)  # 3000 microsecond sleep, clearing the display takes a long time

        return self

    def message(self, text, autoscroll=False):
        """ Send long string to LCD. 17th char wraps to second line"""
        def lcd_render(render_text):
            i = 0
            lines = 0

            for char in render_text:
                if char == '\n':
                    self.lcd.write4bits(0xC0)  # next line
                    i = 0
                    lines += 1
                else:
                    self.lcd.write4bits(ord(char), True)
                    i = i + 1

                if i == 16:
                    self.lcd.write4bits(0xC0)  # last char of the line

        try:
            splitlines = text.split('\n')

            # process a single line
            if len(splitlines) < 2:
                line1 = splitlines[0]

                # if theres one line and its longer than 16 characters, split it onto line 2
                len1 = len(line1)
                if len1 > 16:
                    #  // will return an integer
                    half = (len1 // 2)
                    # split it in half
                    line2 = line1[half:]
                    line1 = line1[0:half]
                else:
                    #  line 2 is nothing if line1 is not more than 16 characters
                    line2 = ''

                # recalculate lengths for scoller
                len1 = len(line1)
                len2 = len(line2)
                final_text = ("%s\n%s" % (line1, line2))

            # process 2 lines
            elif len(splitlines) == 2:
                # set lengeths for scoller but other wise leave the text
                len1 = len(splitlines[0])
                len2 = len(splitlines[1])
                final_text = text

            else:
                # TODO process more than 2 lines. Currently they just get cropped.
                len1 = len(splitlines[0])
                len2 = len(splitlines[1])
                final_text = text

            # print("Final text is: %s" % final_text)

            # TODO needs to be interruptable somehow
            if autoscroll == True:
                # add one to the longest length so it scrolls off screen
                if len1 < len2:
                    text_length = len2
                else:
                    text_length = len1

                # render for 16x2
                fixed_text = self.render_16x2(final_text)
                # render the output
                lcd_render(fixed_text)

                # only scroll if needed
                if text_length > 16:

                    # add one to the longest length so it scrolls off screen
                    text_length = text_length + 1

                    # show the text for one second
                    sleep(1)

                    # scroll the message right to left
                    # start 1 character in as we've already rendered the first character
                    for index in range(1, text_length):
                        # render at 16x2
                        fixed_text = self.render_16x2(final_text, index)

                        # clear display before render
                        self.clearDisplay()

                        # render the output
                        lcd_render(fixed_text)

                        # wait a little between renders
                        sleep(0.025)

                    # render for 16x2
                    fixed_text = self.render_16x2(final_text)

                    # clear display before render
                    self.clearDisplay()

                    # render the output
                    lcd_render(fixed_text)

                return self

            else:
                # just show the text if theres no autoscroll
                fixed_text = self.render_16x2(final_text)

                # render the output
                lcd_render(fixed_text)

                return self


        except Exception as e:
            print("Autoscroll error: %s" % e)

    def displayTestScreen(self):
        """
        Display test screen to see if your LCD screen is wokring
        """
        self.message('Hum. body 36,6\xDFC\nThis is test')

        return self

    def render(self):
        """
        Render menu
        """
        self.clearDisplay()

        if len(self.items) == 0:
            self.message('Menu is empty')
            return self
        elif len(self.items) <= 2:
            options = (self.current_option == 0 and ">" or " ") + self.items[0].text
            if len(self.items) == 2:
                options += "\n" + (self.current_option == 1 and ">" or " ") + self.items[1].text
            print(options)
            if self.scrolling_menu == True:
                self.message(options, autoscroll=True)
            else:
                self.message(options)
            return self

        options = ">" + self.items[self.current_option].text

        if self.current_option + 1 < len(self.items):
            options += "\n " + self.items[self.current_option + 1].text
        else:
            options += "\n " + self.items[0].text

        if self.scrolling_menu == True:
            self.message(options, autoscroll=True)
        else:
            self.message(options)

        return self

    def render_16x2(self, text, index=0):

        # incoming text will already have been cleaned up and split with a line break
        # by the message function


        try:
            # render incoming text as 16x2 by taking the starting index and adding 16
            # for each line

            lines = text.split('\n')
            line1 = lines[0]
            line2 = lines[1]
            # pad out the text if its less than 16 characters  long
            last_char = index + 16
            line1_vfd = "{:<16}".format(line1[index:last_char])
            line2_vfd = "{:<16}".format(line2[index:last_char])

            # print("Line lengths:\n%s\n%s" % (len(line1_vfd), len(line2_vfd)))
            return ("%s\n%s" % (line1_vfd, line2_vfd))


        except Exception as e:
            print("Render error: %s" % e)
