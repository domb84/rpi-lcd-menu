from rpilcdmenu import RpiLCDMenu


class RpiLCDSubMenu(RpiLCDMenu):
    def __init__(self, base_menu, scrolling_menu=False):
        """
        Initialize SubMenu
        """
        self.lcd = base_menu.lcd
        self.scrolling_menu = scrolling_menu

        super(RpiLCDMenu, self).__init__(base_menu)
