
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gst
from gi.repository import Gtk
import os
import sys

from kuwo import Config
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

        self.notebook = Gtk.Notebook()
        box.pack_start(self.notebook, True, True, 0)

        self.player = Player(self)
        box.pack_start(self.player, False, False, 0)

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

        self.toplist = TopList(self)
        self.notebook.append_page(self.toplist, Gtk.Label('热播榜'))

        self.playlist = PlayList(self)
        self.notebook.append_page(self.playlist, Gtk.Label('播放列表'))

    def on_notebook_switch_page(self, notebook, page, page_num):
        page.first()

#    def on_treeview_selection_nodes_changed(self, selection, 
#            inited=[]):
#
#        model, tree_iter = selection.get_selected()
#        path = model.get_path(tree_iter)
#        nid = model[path][1]
#        index = path.get_indices()[0]
#        methods = [
#                self.init_toplist,
#                self.init_mv,
#                self.init_artists,
#                self.init_hot_categories,
#                self.init_broadcasting,
#                self.init_language,
#                self.init_people,
#                self.init_festival,
#                self.init_temper,
#                self.init_scene,
#                self.init_genre,
#                self.init_playlist,
#                self.init_search,
#                self.init_download,
#                ]
#        if index not in inited:
#            inited.append(index)
#            methods[index](nid)
#        # switch to specific tab
#        self.ui('notebook_main').set_current_page(index)








    # Common signal handlers for song list
#    def on_cellrenderer_toggled(self, liststore, path):
#        '''
#        Use connect_swap()
#        '''
#        liststore[path][0] = not liststore[path][0]
#
#
#
#    # toplist
#    def init_toplist(self, nid):
#        self.ui('scrolledwindow_toplist_nodes').show_all()
#        self.ui('scrolledwindow_toplist_songs').hide()
#        self.ui('buttonbox_toplist').hide()
#
#        nodes = Cache.Node(nid).get_nodes()
#
#        liststore = self.ui('liststore_toplist_nodes')
#        liststore.clear()
#        i = 0
#        for node in nodes:
#            liststore.append([self.theme['anonymous'], 
#                node['disname'], node['sourceid'], ])
#            Cache.update_liststore_image(liststore, i, 0, node['pic'])
#            i += 1
#
#    def on_button_toplist_clicked(self, btn):
#        '''
#        Back to top list from sublist
#        '''
#        self.ui('scrolledwindow_toplist_nodes').show_all()
#        self.ui('scrolledwindow_toplist_songs').hide()
#        self.ui('buttonbox_toplist').hide()
#    
#
#    # mv
#    def init_mv(self, nid):
#        pass
#
#
#    # artists
#    def init_artists(self, nid):
#        liststore_prefix = self.ui('liststore_artists_prefix')
#        liststore_prefix.append(('All', ''))
#        for ch in string.ascii_uppercase:
#            liststore_prefix.append((ch, ch.lower()))
#        liststore_prefix.append(('#', '%23'))
#        self.ui('combobox_artists_prefix').set_active(0)
#        
#        liststore_country = self.ui('liststore_artists_country')
#        for country in Config.ARTISTS_COUNTRY:
#            liststore_country.append(country)
#        self.ui('combobox_artists_country').set_active(0)
#
#        self.ui('scrolledwindow_artists_songs').hide()
#
#        artists = Cache.Artists().get_artists(0, 0)
#        liststore = self.ui('liststore_artists')
#        i = 0
#        for artist in artists:
#            print('artist:', artist)
#            print('artist:', artist)
#            liststore.append([self.theme['anonymous'], artist['name'],
#                int(artist['id'])])
#            Cache.update_liststore_image(liststore, i, 0, artist['pic'])
#            i += 1
#
#
#    def on_button_artists_clicked(self, btn):
#        self.ui('scrolledwindow_artists_songs').hide()
#        self.ui('scrolledwindow_artists').show_all()
#        self.ui('buttonbox_artists').hide()
#
#    def on_iconview_artists_item_activated(self, iconview, path):
#        model = iconview.get_model()
#        self.ui('buttonbox_artists').show_all()
#        self.ui('label_artists').set_label(model[path][1])
#        self.show_artists_songs(model[path][1])
#
#    def show_artists_songs(self, artist):
#        self.ui('scrolledwindow_artists').hide()
#        self.ui('scrolledwindow_artists_songs').show_all()
#        self.artist = Cache.ArtistSong(artist)
#        songs = self.artist.get_songs()
#
#
#        liststore = self.ui('liststore_artists_songs')
#        liststore.clear()
#        for song in songs:
#            liststore.append([True, song['NAME'], song['ALBUM'],
#                int(song['MUSICRID'][6:]), int(song['ALBUMID']), 
#                self.theme['play'], self.theme['add'],
#                self.theme['download']])
#
