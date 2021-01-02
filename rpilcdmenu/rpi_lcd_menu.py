from time import sleep

from rpilcdmenu.base_menu import BaseMenu
from rpilcdmenu.rpi_lcd_hwd import RpiLCDHwd


class RpiLCDMenu(BaseMenu):
    def __init__(self, pin_rs=26, pin_e=19, pins_db=[13, 6, 5, 21], GPIO=None):
        """
        Initialize menu
        """

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
        print(text)

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

        if autoscroll==True:

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
                        print("Half of line 1 is: %s" % half)
                        # split it in half
                        line2 = line1[half:]
                        line1 = line1[0:half]
                        print("line 1: %s" % line1)
                        print("line 2: %s" % line2)
                    else:
                        #  render nothing if theres nothing on line 2
                        line2 = ''

                    # set lenth of line 2
                    len2 = len(line2)
                    final_text = ("%s\n%s" % (line1, line2))

                # process 2 lines
                elif len(splitlines) == 2:
                    len1 = len(splitlines[0])
                    len2 = len(splitlines[1])
                    final_text = text

                else:
                    len1 = len(splitlines[0])
                    len2 = len(splitlines[1])
                    final_text = text

                # add one to the longest length so it scrolls off screen
                if len1 < len2:
                    text_length = len2 + 1
                else:
                    text_length = len1 + 1

                # render for 16x2
                fixed_text = self.render_16x2(final_text)

                # render the output
                lcd_render(fixed_text)

                # show the text for one second
                sleep(1)

                # render for 16x2 then
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
                    sleep(0.05)


                # render for 16x2
                fixed_text = self.render_16x2(text)

                # clear display before render
                self.clearDisplay()

                # render the output
                lcd_render(fixed_text)

                return self

            except Exception as e:
                print("Autoscroll error: %s" % e)


        else:

            fixed_text = self.render_16x2(text)

            # render the output
            lcd_render(fixed_text)

            return self

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
            self.message(options)
            return self

        options = ">" + self.items[self.current_option].text

        if self.current_option + 1 < len(self.items):
            options += "\n " + self.items[self.current_option + 1].text
        else:
            options += "\n " + self.items[0].text

        self.message(options)

        return self

    def render_16x2(self, text, index=0):
        # render incoming text as 16x2
        try:
            lines = text.split('\n')

            # process a single line
            if len(lines) < 2:
                line1 = lines[0]

                # if theres one line and its longer than 16 characters, split it onto line 2
                if len(line1) > 16:
                    line2 = line1[16:32]
                    line1 = line1[0:16]
                    print("line 1: %s" % line1)
                    print("line 2: %s" % line2)
                else:
                    #  render nothing if theres nothing on line 2
                    line2 = ''

            # process 2 lines
            elif len(lines) == 2:
                line1 = lines[0]
                line2 = lines[1]

            # TODO deal with more than 3 lines. For now just deal with the first 2.
            else:
                line1 = lines[0]
                line2 = lines[1]

            # pad out the text if its less than 16 characters  long
            last_char = index + 16
            line1_vfd = "{:<16}".format(line1[index:last_char])
            line2_vfd = "{:<16}".format(line2[index:last_char])
            print("vfd line 1: %s" % line1_vfd)
            print("vfd line 2: %s" % line2_vfd)

            return ("%s\n%s" % (line1_vfd, line2_vfd))


        except Exception as e:
            print("Render error: %s" % e)
