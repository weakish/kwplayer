
from kuwo import Cache
from gi.repository import Gst

class Player:
    def __init__(self, uri):
        self.app = app
        self._player = Gst.ElementFactory.make('playbin', 'player')
        self._player.set_property('uri', uri)

    def pause(self):
        self._player.set_state(Gst.State.PAUSE)

    def play(self):
        self._player.set_state(Gst.State.PLAYING)
