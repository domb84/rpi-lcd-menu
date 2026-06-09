from rpilcdmenu import RpiLCDMenu


class RpiLCDSubMenu(RpiLCDMenu):
    def __init__(self, base_menu):
        """
        Initialize SubMenu
        """
        self.lcd = base_menu.lcd
        self.scrolling_menu = base_menu.scrolling_menu
        self.lcd_queue = base_menu.lcd_queue

        # Deliberately skip RpiLCDMenu.__init__ (it would re-init the hardware
        # and spin up a second worker thread) and call BaseMenu.__init__
        # directly, reusing the parent's display and queue. This is why the
        # explicit two-argument super() is used rather than a bare super().
        super(RpiLCDMenu, self).__init__(base_menu)
