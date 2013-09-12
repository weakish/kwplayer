

from gi.repository import Gtk


class Lrc(Gtk.ScrolledWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.buf = Gtk.TextBuffer()
        self.buf.set_text('Lrc loading...')
        self.textview = Gtk.TextView(buffer=self.buf)
        self.add(self.textview)

    def after_init(self):
        pass

    def first(self):
        pass
