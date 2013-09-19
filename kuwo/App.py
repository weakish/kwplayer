
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gtk
import os
import sys

from kuwo import Config
from kuwo.Artists import Artists
from kuwo.Lrc import Lrc
from kuwo.MV import MV
from kuwo.Player import Player
from kuwo.PlayList import PlayList
from kuwo.Preferences import Preferences
from kuwo.Radio import Radio
from kuwo.Search import Search
from kuwo.Themes import Themes
from kuwo.TopCategories import TopCategories
from kuwo.TopList import TopList


GObject.threads_init()

class App:
    def __init__(self):
        self.app = Gtk.Application.new('org.gtk.kuwo', 0)
        self.app.connect('startup', self.on_app_startup)
        self.app.connect('activate', self.on_app_activate)
        self.app.connect('shutdown', self.on_app_shutdown)

        self.conf = Config.load_conf()
        self.theme = Config.load_theme(self.conf['theme'])

    def run(self, argv):
        self.app.run(argv)

    def on_app_startup(self, app):
        self.window = Gtk.ApplicationWindow.new(app)
        self.window.set_default_size(*self.conf['window-size'])
        self.window.set_title(Config.APPNAME)
        self.window.props.hide_titlebar_when_maximized = True

        self.window.set_icon(self.theme['app-logo'])

        self.window.connect('check-resize', self.on_main_window_resized)
        app.add_window(self.window)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.add(box)

        self.player = Player(self)
        box.pack_start(self.player, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.props.tab_pos = Gtk.PositionType.BOTTOM
        #self.notebook.props.tab_pos = Gtk.PositionType.LEFT
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
        # signal should be connected after all pages in notebook all added.
        self.init_notebook()
        self.notebook.connect('switch-page', self.on_notebook_switch_page)

        # load styles
        self.load_styles()

        self.window.show_all()

        # make some changes after main window is shown.
        self.artists.after_init()
        self.lrc.after_init()
        self.mv.after_init()
        self.player.after_init()
        self.radio.after_init()
        self.search.after_init()
        self.themes.after_init()
        self.topcategories.after_init()
        self.toplist.after_init()

    def on_app_shutdown(self, app):
        Config.dump_conf(self.conf)

    def on_main_window_resized(self, window, event=None):
        self.conf['window-size'] = window.get_size()

    def on_action_preferences_activate(self, action, param):
        dialog = Preferences(self)
        dialog.run()
        dialog.destroy()

    def on_action_about_activate(self, action, param):
        dialog = Gtk.AboutDialog()
        dialog.set_program_name(Config.APPNAME)
        dialog.set_logo(self.theme['app-logo'])
        dialog.set_version(Config.VERSION)
        dialog.set_comments('A simple music box')
        dialog.set_copyright('Copyright (c) 2013 LiuLang')
        dialog.set_website(Config.HOMEPAGE)
        dialog.set_license_type(Gtk.License.GPL_3_0)
        dialog.set_authors(['LiuLang <gsushzhsosgsu@gmail.com>',])
        dialog.run()
        dialog.destroy()

    def on_action_quit_activate(self, action, param):
        self.app.quit()

    def add_simple_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', callback)
        self.app.add_action(action)

    def init_notebook(self):
        self.lrc = Lrc(self)
        self.notebook.append_page(self.lrc, Gtk.Label('Lyrics'))

        self.playlist = PlayList(self)
        self.notebook.append_page(self.playlist, Gtk.Label('Playlist'))

        self.search = Search(self)
        self.notebook.append_page(self.search, Gtk.Label('Search'))

        self.toplist = TopList(self)
        self.notebook.append_page(self.toplist, Gtk.Label('Top List'))

        self.radio = Radio(self)
        self.notebook.append_page(self.radio, Gtk.Label('Radio'))

        self.mv = MV(self)
        self.notebook.append_page(self.mv, Gtk.Label('MV'))

        self.artists = Artists(self)
        self.notebook.append_page(self.artists, Gtk.Label('Artists'))

        self.topcategories = TopCategories(self)
        self.notebook.append_page(self.topcategories, 
                Gtk.Label('Categories'))

        self.themes = Themes(self)
        self.notebook.append_page(self.themes, Gtk.Label('Themes'))

    def on_notebook_switch_page(self, notebook, page, page_num):
        page.first()

    def load_styles(self):
        style_file = os.path.join(self.conf['theme'], 'main.css')
        with open(style_file, 'rb') as fh:
            css = fh.read()

        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
