class BaseMenu:
    """
    A generic menu
    """
    def __init__(self, parent=None):
        """
        Initialize basic menu
        """
        self.items = []
        self.parent = parent
        self.current_option = 0
        self.selected_option = -1

    def start(self):
        """
        Start and render menu
        """
        self.current_option = 0
        self.selected_option = -1
        self.render()

        return self

    def debug(self, level=1):
        """
        print menu items in console
        """
        for item in self.items:
            if hasattr(item, 'submenu') and isinstance(item.submenu, BaseMenu):
                print(f"|{'--' * (level + 1)}[{item}]")
                item.submenu.debug(level + 1)
            else:
                print(f"|{'--' * level}>{item}")
        return self

    def append_item(self, item):
        """
        Add an item to the end of the menu
        :param MenuItem item: The item to be added
        """
        item.menu = self
        self.items.append(item)
        return self

    def render(self):
        """
        Render menu
        """
        pass

    def clearDisplay(self):
        """
        Clear the screen/
        """
        pass

    def _selected_index(self):
        """The row the cursor is on, pulled back into range, or None if empty.

        current_option is public state that callers assign to directly -- a
        remembered position restored onto a menu that has since lost items
        leaves it past the end, where every items[] lookup raises IndexError
        rather than just selecting the wrong row.
        """
        if not self.items:
            self.current_option = 0
            return None
        self.current_option = max(0, min(self.current_option, len(self.items) - 1))
        return self.current_option

    def processUp(self):
        """
        User triggered up event
        """
        if self._selected_index() is not None:
            self.current_option = (self.current_option - 1) % len(self.items)
        self.render()
        return self

    def processDown(self):
        """
        User triggered down event
        """
        if self._selected_index() is not None:
            self.current_option = (self.current_option + 1) % len(self.items)
        self.render()
        return self

    def processEnter(self):
        """
        User triggered enter event
        """
        if self._selected_index() is None:
            # Nothing to activate; render() already shows that the menu is empty.
            return self
        action_result = self.items[self.current_option].action()
        if isinstance(action_result, BaseMenu):
            return action_result
        return self

    def exit(self):
        """
        exit submenu and return parent
        """
        if self.parent is not None:
            self.parent.render()
        return self.parent

    def remove_item(self, item):
        """
        Remove an item from the menu
        :param MenuItem item: The item to be removed
        """
        item.menu = self
        self.items.remove(item)
        return self

