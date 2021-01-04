from rpilcdmenu import RpiLCDMenu


class RpiLCDSubMenu(RpiLCDMenu):
    def __init__(self, base_menu, scrolling_menu=False):
        """
        Initialize SubMenu
        """
        self.lcd = base_menu.lcd

        super(RpiLCDMenu, self, scrolling_menu).__init__(base_menu)
