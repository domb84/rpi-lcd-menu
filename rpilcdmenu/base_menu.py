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

    def processUp(self):
        """
        User triggered up event
        """
        if self.current_option == 0:
            self.current_option = len(self.items) - 1
        else:
            self.current_option -= 1
        self.render()
        return self

    def processDown(self):
        """
        User triggered down event
        """
        if self.current_option == len(self.items) - 1:
            self.current_option = 0
        else:
            self.current_option += 1
        self.render()
        return self

    def processEnter(self):
        """
        User triggered enter event
        """
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

