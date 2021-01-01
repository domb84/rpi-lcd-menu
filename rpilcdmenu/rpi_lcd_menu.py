from rpilcdmenu.base_menu import BaseMenu
from rpilcdmenu.rpi_lcd_hwd import RpiLCDHwd
from time import sleep

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

        def render(render_text):
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

                len1 = len(splitlines[0])
                try:
                    len2 = len(splitlines[1])
                except:
                    len2 = 0

                # add one to the longest length so it scrolls off screen
                if len1 < len2:
                    text_length = len2 + 1
                else:
                    text_length = len1 + 1

                # render for 16x2
                fixed_text = self.render_16x2(text, 0)

                # render the output
                render(fixed_text)

                # show the text for one second
                sleep(1)

                # render for 16x2 then
                # scroll the message right to left
                # start 1 character in as we've already rendered the first character
                for index in range(1, text_length):

                    # render at 16x2
                    fixed_text = self.render_16x2(text, index)

                    # clear display before render
                    self.clearDisplay()

                    # render the output
                    render(fixed_text)

                    # wait a little between renders
                    sleep(0.05)


                # render for 16x2
                fixed_text = self.render_16x2(text, 0)

                # clear display before render
                self.clearDisplay()

                # render the output
                render(fixed_text)

                return self

            except Exception as e:
                print("Autoscroll error: %s" % e)


        else:

            fixed_text = self.render_16x2(text, 0)

            # render the output
            render(fixed_text)

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


    def render_16x2(self, text, index):
        # print("text input %s" % text)
        # print("index: %s" % index)
        try:
            lines = text.split('\n')
            line1 = lines[0]
            try:
                line2 = lines[1]
            except:
                line2 = ''
            last_char = index + 15
            line1_vfd = "{:<16}".format(line1[index:last_char])
            line2_vfd = "{:<16}".format(line2[index:last_char])
            return ("%s\n%s" % (line1_vfd, line2_vfd))
        except Exception as e:
            print("Render error: %s" % e)
