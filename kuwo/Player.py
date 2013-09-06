
from kuwo import Cache
from gi.repository import Gst

class Player:
    def __init__(self):
        self._player = None

    def load(self, filepath):
        if self._player is not None:
            self.pause()
            del self._player
        self._player = Gst.ElementFactory.make('playbin', 'player')
        self._player.set_property('uri', 'file://' + filepath)

    def pause(self):
        if self._player is not None:
            self._player.set_state(Gst.State.PAUSED)

    def play(self):
        if self._player is not None:
            self._player.set_state(Gst.State.PLAYING)
