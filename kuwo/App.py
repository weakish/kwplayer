
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gst
from gi.repository import Gtk
import os
import sys

from kuwo import Config
from kuwo.Artists import Artists
from kuwo.Lrc import Lrc
from kuwo.Player import Player
from kuwo.PlayList import PlayList
from kuwo.TopList import TopList


GObject.threads_init()

class App:
    def __init__(self):
        self.app = Gtk.Application.new('org.gtk.kuwo', 0)
        self.app.connect('startup', self.on_app_startup)
        self.app.connect('activate', self.on_app_activate)
        self.app.connect('shutdown', self.on_app_shutdown)

        self.conf = Config.load_conf()
        # TODO: check theme is not None
        self.theme = Config.load_theme(self.conf)

    def run(self, argv):
        self.app.run(argv)

    def on_app_startup(self, app):
        self.window = Gtk.ApplicationWindow.new(app)
        self.window.set_default_size(*self.conf['window-size'])
        self.window.set_title('KW Player')
        self.window.set_border_width(5)
        self.window.props.hide_titlebar_when_maximized = True

        self.window.set_icon(self.theme['app-logo'])

        self.window.connect('check-resize', self.on_main_window_resized)
        app.add_window(self.window)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.add(box)

        self.player = Player(self)
        box.pack_start(self.player, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.props.margin_top = 7
        self.notebook.props.tab_pos = Gtk.PositionType.BOTTOM
        box.pack_start(self.notebook, True, True, 0)

        builder = Gtk.Builder()
        builder.add_from_file(Config.MENUS)
        builder.connect_signals(self)
        appmenu = builder.get_object('appmenu')
        app.set_app_menu(appmenu)
        
        self.add_simple_action('preferences', 
                self.on_action_preferences_activate)
        self.add_simple_action('about', self.on_action_about_activate)
        self.add_simple_action('quit', self.on_action_quit_activate)

    def on_app_activate(self, app):
        # init Gst so that play works ok.
        Gst.init_check(sys.argv)

        # TODO: init others
        # signal should be connected after all pages in notebook all added.
        self.init_notebook()
        self.notebook.connect('switch-page', self.on_notebook_switch_page)

        self.window.show_all()

        # make some changes after main window is shown.
        self.player.after_init()
        self.toplist.after_init()
        self.artists.after_init()

    def on_app_shutdown(self, app):
        Config.dump_conf(self.conf)

    def on_main_window_resized(self, window, event=None):
        self.conf['window-size'] = window.get_size()

    def on_action_preferences_activate(self, action, param):
        print('prefereces action')

    def on_action_about_activate(self, action, param):
        print('about action')

    def on_action_quit_activate(self, action, param):
        print('quit actition')
        self.app.quit()

    def add_simple_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', callback)
        self.app.add_action(action)

    def init_notebook(self):
        self.lrc = Lrc(self)
        self.notebook.append_page(self.lrc, Gtk.Label('Lrc'))

        self.playlist = PlayList(self)
        self.notebook.append_page(self.playlist, Gtk.Label('Playlist'))

        self.toplist = TopList(self)
        self.notebook.append_page(self.toplist, Gtk.Label('TopList'))

        self.artists = Artists(self)
        self.notebook.append_page(self.artists, Gtk.Label('Artists'))

    def on_notebook_switch_page(self, notebook, page, page_num):
        page.first()
