from rpilcdmenu import RpiLCDMenu


class RpiLCDSubMenu(RpiLCDMenu):
    def __init__(self, base_menu):
        """
        Initialize SubMenu
        """
        self._base_menu = base_menu
        self.lcd = base_menu.lcd
        self.scrolling_menu = base_menu.scrolling_menu
        self.lcd_queue = base_menu.lcd_queue

        # One display means one lock: the submenu has to serialise against the
        # parent's worker thread, not against a lock of its own that nothing
        # else takes. Sharing the CGRAM copy matters for the same reason -- a
        # resync from either menu has to be able to reload every glyph.
        self._lcd_lock = base_menu._lcd_lock
        self._cgram = base_menu._cgram
        self._resync_interval = base_menu._resync_interval

        # Deliberately skip RpiLCDMenu.__init__ (it would re-init the hardware
        # and spin up a second worker thread) and call BaseMenu.__init__
        # directly, reusing the parent's display and queue. This is why the
        # explicit two-argument super() is used rather than a bare super().
        super(RpiLCDMenu, self).__init__(base_menu)

    # The remaining display state is delegated rather than copied. It describes
    # the one physical screen, so a submenu that kept its own copy would drift:
    # switch the display off from a submenu and the parent would still think it
    # was on, and redraw a frame the submenu had already replaced.

    @property
    def _display_off(self):
        return self._base_menu._display_off

    @_display_off.setter
    def _display_off(self, value):
        self._base_menu._display_off = value

    @property
    def _last_frame(self):
        return self._base_menu._last_frame

    @_last_frame.setter
    def _last_frame(self, value):
        self._base_menu._last_frame = value

    @property
    def _frames_since_resync(self):
        return self._base_menu._frames_since_resync

    @_frames_since_resync.setter
    def _frames_since_resync(self, value):
        self._base_menu._frames_since_resync = value
