
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
from kuwo.Themes import Themes
from kuwo.Player import Player
from kuwo.PlayList import PlayList
from kuwo.Radio import Radio
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
        # TODO: check theme is not None
        self.theme = Config.load_theme(self.conf)

    def run(self, argv):
        self.app.run(argv)

    def on_app_startup(self, app):
        self.window = Gtk.ApplicationWindow.new(app)
        self.window.set_default_size(*self.conf['window-size'])
        self.window.set_title(Config.APPNAME)
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
        self.radio.after_init()
        self.artists.after_init()
        self.topcategories.after_init()
        self.themes.after_init()

    def on_app_shutdown(self, app):
        Config.dump_conf(self.conf)

    def on_main_window_resized(self, window, event=None):
        self.conf['window-size'] = window.get_size()

    def on_action_preferences_activate(self, action, param):
        dialog = Gtk.Dialog('Preferences', self.window, 0,
                    (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE,))
        dialog.set_default_size(600, 320)
        dialog.set_border_width(5)
        box = dialog.get_content_area()
        box.props.margin_left = 15

        label_audio = Gtk.Label('<b>Prefered Audio Format</b>')
        label_audio.set_use_markup(True)
        label_audio.props.halign = Gtk.Align.START
        label_audio.props.xalign = 0
        label_audio.props.margin_bottom = 10
        box.pack_start(label_audio, False, False, 0)
        radio_mp3 = Gtk.RadioButton('MP3 (faster)')
        radio_mp3.props.margin_left = 15
        radio_mp3.connect('toggled', self.on_pref_audio_toggled)
        box.pack_start(radio_mp3, False, False, 0)
        radio_ape = Gtk.RadioButton('APE (better)')
        radio_ape.join_group(radio_mp3)
        radio_ape.props.margin_left = 15
        radio_ape.set_active(self.conf['use-ape'])
        radio_ape.connect('toggled', self.on_pref_audio_toggled)
        box.pack_start(radio_ape, False, False, 0)

        label_video = Gtk.Label('<b>Prefered Video Format</b>')
        label_video.set_use_markup(True)
        label_video.props.halign = Gtk.Align.START
        label_video.props.xalign = 0
        label_video.props.margin_top = 20
        label_video.props.margin_bottom = 10
        box.pack_start(label_video, False, False, 0)
        radio_mp4 = Gtk.RadioButton('MP4 (faster)')
        radio_mp4.props.margin_left = 15
        radio_mp4.connect('toggled', self.on_pref_video_toggled)
        box.pack_start(radio_mp4, False, False, 0)
        radio_mkv = Gtk.RadioButton('MKV (better)')
        radio_mkv.props.margin_left = 15
        radio_mkv.join_group(radio_mp4)
        radio_mkv.set_active(self.conf['use-mkv'])
        radio_mkv.connect('toggled', self.on_pref_video_toggled)
        box.pack_start(radio_mkv, False, False, 0)

        box.show_all()
        dialog.run()
        dialog.destroy()

    def on_pref_audio_toggled(self, radiobtn):
        self.conf['use-ape'] = radiobtn.get_group()[0].get_active()
        Config.dump_conf(self.conf)

    def on_pref_video_toggled(self, radiobtn):
        # radio_group[0] is MKV
        self.conf['use-mkv'] = radiobtn.get_group()[0].get_active()
        Config.dump_conf(self.conf)

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
        self.notebook.append_page(self.lrc, Gtk.Label('歌词'))

        self.playlist = PlayList(self)
        self.notebook.append_page(self.playlist, Gtk.Label('播放列表'))

        self.toplist = TopList(self)
        self.notebook.append_page(self.toplist, Gtk.Label('热播榜'))

        self.radio = Radio(self)
        self.notebook.append_page(self.radio, Gtk.Label('电台'))

        self.artists = Artists(self)
        self.notebook.append_page(self.artists, Gtk.Label('歌手'))

        self.topcategories = TopCategories(self)
        self.notebook.append_page(self.topcategories, Gtk.Label('热门分类'))

        self.themes = Themes(self)
        self.notebook.append_page(self.themes, Gtk.Label('心情主题'))

    def on_notebook_switch_page(self, notebook, page, page_num):
        page.first()
