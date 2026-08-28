import socket

DEFAULT_SOCKET_PATH = '/tmp/rpi-lcd-menu.sock'


class DisplayController:
    """Client for controlling the LCD display from another process.

    Usage::

        from rpilcdmenu import DisplayController
        ctrl = DisplayController()
        ctrl.toggle()   # turn off if on, or on if off
        ctrl.off()      # turn display off
        ctrl.on()       # turn display on
        ctrl.status()   # returns 'on' or 'off'

        ctrl.brightness(50)   # 100, 75, 50 or 25 -- the only levels there are
        ctrl.brightness()     # the level currently on the panel
    """

    def __init__(self, socket_path=DEFAULT_SOCKET_PATH):
        self._socket_path = socket_path

    def _send(self, command):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(self._socket_path)
            s.sendall(command.encode())
            s.shutdown(socket.SHUT_WR)
            return s.recv(32).decode().strip()

    def toggle(self):
        """Toggle display on/off."""
        return self._send('toggle')

    def off(self):
        """Turn display off."""
        return self._send('off')

    def on(self):
        """Turn display on."""
        return self._send('on')

    def status(self):
        """Return 'on' or 'off'."""
        return self._send('status')

    def brightness(self, level=None):
        """Get or set panel brightness.

        No argument returns the current level as an int; with one, sets it and
        returns 'ok'. Must be 100, 75, 50 or 25 -- all the hardware has -- and
        raises ValueError otherwise. 25 is the dimmest step, not off.
        """
        if level is None:
            return int(self._send('brightness'))

        response = self._send('brightness %s' % (level,))
        if response == 'error':
            raise ValueError("brightness must be 100, 75, 50 or 25, got %r"
                             % (level,))
        return response
