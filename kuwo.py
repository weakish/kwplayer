#!/usr/bin/env python3


from gi.repository import Gtk

from kuwo import Config
from kuwo.Handler import Handler


def main():
    builder = Gtk.Builder()
    builder.add_from_file(Config.UI_FILE)

    handler = Handler(builder)
    builder.connect_signals(handler)

    handler.run()

if __name__ == '__main__':
    main()
