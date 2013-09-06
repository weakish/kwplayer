
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk
import sys

from kuwo import Config
from kuwo import Cache
from kuwo.Player import Player

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
        self.window.set_title('KuWo Player')
        self.window.props.hide_titlebar_when_maximized = True

        self.window.set_icon(self.theme['app-logo'])

        self.window.connect('check-resize', self.on_main_window_resized)
        app.add_window(self.window)
        self.builder = Gtk.Builder()
        for ui in Config.UI_FILES:
            self.builder.add_from_file(ui)
        self.window.add(self.ui('box_main'))
        self.builder.connect_signals(self)
        
        appmenu = self.builder.get_object('appmenu')
        app.set_app_menu(appmenu)
        
        self.add_simple_action('preferences', 
                self.on_action_preferences_activate)
        self.add_simple_action('about', self.on_action_about_activate)
        self.add_simple_action('quit', self.on_action_quit_activate)

    def on_app_activate(self, app):
        self.player = None
        Gst.init_check(sys.argv)

        self.song = Cache.Song(self)
        self.song.connect('downloaded', self.on_song_downloaded)

        self.init_player()
        self.init_nodes()
        self.init_notebook_main()
        # TODO: init others

        self.window.show_all()
        self.ui('toolbutton_pause').hide()

    def on_app_shutdown(self, app):
        Config.dump_conf(self.conf)
        Cache.close()
        self.song.close()

    def on_main_window_resized(self, window, event=None):
        self.conf['window-size'] = window.get_size()

    def on_action_preferences_activate(self, action, param):
        print('prefereces action')

    def on_action_about_activate(self, action, param):
        print('about action')

    def on_action_quit_activate(self, action, param):
        print('quit actition')
        self.app.quit()


    # Utilities
    def ui(self, widget, container={}):
        if widget in container:
            return container[widget]

        container[widget] = self.builder.get_object(widget)
        return container[widget]

    def add_simple_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', callback)
        self.app.add_action(action)


    # Player
    def init_player(self):
        self.ui('toolbar_player').get_style_context().add_class(
                Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)

        self.ui('image_player_logo').set_from_pixbuf(
                self.theme['anonymous'])

    def on_action_player_previous_activate(self, action):
        pass
    def on_action_player_next_activate(self, action):
        pass
    def on_action_player_play_activate(self, action):
        self.ui('toolbutton_play').hide()
        self.ui('toolbutton_pause').show_all()
        self.player.play()

    def on_action_player_pause_activate(self, widget):
        self.ui('toolbutton_pause').hide()
        self.ui('toolbutton_play').show_all()
        self.player.pause()

    def on_action_player_repeat_activate(self, action):
        pass
    def on_action_player_repeat_one_activate(self, action):
        pass
    def on_action_player_shuffle_activate(self, action):
        pass

    def on_song_downloaded(self, song_obj, song_info):
        if isinstance(self.player, Player):
            self.on_action_player_pause_activate(None)
        uri = 'file://' + conf['song-dir'] + song_info[filename])
        print('will play uri:', uri)
        self.player = Player(uri)
        self.on_action_player_play_activate(None)

    # side nodes
    def init_nodes(self):
        model = self.ui('liststore_nodes')
        model.clear()
        for node in Config.NODES:
            model.append(node)

    def on_treeview_selection_nodes_changed(self, selection, 
            inited=[]):
        print(selection.get_selected())

        model, tree_iter = selection.get_selected()
        path = model.get_path(tree_iter)
        nid = model[path][1]
        index = path.get_indices()[0]
        #print(model, tree_iter, path, type(path), index)
        methods = [
                self.init_toplist,
                self.init_mv,
                self.init_artists,
                self.init_hot_categories,
                self.init_broadcasting,
                self.init_language,
                self.init_people,
                self.init_festival,
                self.init_temper,
                self.init_scene,
                self.init_genre,
                self.init_playlist,
                self.init_search,
                self.init_download,
                ]
        if index not in inited:
            inited.append(index)
            methods[index](nid)

    # notebook_main
    def init_notebook_main(self):
        note = self.ui('notebook_main')
        #page_toplist = Node.TopList(self)
        label = Gtk.Label('hello')
        note.append_page(self.ui('box_toplist'), label)



    # Common signal handlers for song list
    def on_cellrenderer_toggled(self, liststore, path):
        '''
        Use connect_swap()
        '''
        liststore[path][0] = not liststore[path][0]

    def on_treeview_songs_row_activated(self, treeview, path, column):
        liststore = treeview.get_model()
        index = treeview.get_columns().index(column)
        song = {
                'name': liststore[path][1],
                'artist': liststore[path][2],
                'album': liststore[path][3],
                'rid': liststore[path][7],
                'artistid': liststore[path][8],
                'albumid': liststore[path][9],
                }

        if index in (1, 4):
            # level 1
            self.player.pause()
            self.song.play_song(song)
        elif index == 2:
            print('will search artist')
        elif index == 3:
            print('will search album')
        elif index == 5:
            # level 2
            self.song.append_playlist(song)
        elif index == 6:
            # level 3
            self.song.cache_song(song)



    # toplist
    def init_toplist(self, nid):
        self.ui('scrolledwindow_toplist_nodes').show_all()
        self.ui('scrolledwindow_toplist_songs').hide()
        self.ui('buttonbox_toplist').hide()

        nodes = Cache.Node(nid).get_nodes()
        #print(nodes)

        liststore = self.ui('liststore_toplist_nodes')
        i = 0
        for node in nodes:
            liststore.append([self.theme['anonymous'], 
                node['disname'], node['sourceid'], ])
            Cache.update_liststore_image(liststore, i, 0, node['pic'])
            i += 1

    def on_button_toplist_clicked(self, btn):
        '''
        Back to top list from sublist
        '''
        self.ui('scrolledwindow_toplist_nodes').show_all()
        self.ui('scrolledwindow_toplist_songs').hide()
        self.ui('buttonbox_toplist').hide()
    
    def on_iconview_toplist_nodes_item_activated(self, iconview, path):
        print('iconview:', iconview)
        model = iconview.get_model()
        self.ui('buttonbox_toplist').show_all()
        self.ui('label_toplist').set_label(model[path][1])
        self.show_toplist_songs(model[path][2])

    def show_toplist_songs(self, nid):
        self.ui('scrolledwindow_toplist_nodes').hide()
        self.ui('scrolledwindow_toplist_songs').show_all()
        toplist = Cache.TopList(nid)
        songs = toplist.get_songs()
        #print('songs:', songs)

        liststore = self.ui('liststore_toplist_songs')
        for song in songs:
            liststore.append([True, song['name'], song['artist'], 
                song['album'], self.theme['play'], self.theme['add'],
                self.theme['download'], song['id'], song['artistid'],
                song['albumid']])

    # mv
    def init_mv(self):
        pass


    # artists
    def init_artists(self):
        pass


    # hot categories
    def init_hot_categories(self):
        pass


    # broadcasting
    def init_broadcasting(self):
        pass


    # language
    def init_language(self):
        pass


    # people
    def init_people(self):
        pass


    # festival
    def init_festival(self):
        pass


    # temper
    def init_temper(self):
        pass


    # scene
    def init_scene(self):
        pass


    # genre
    def init_genre(self):
        pass


    # playlist
    def init_playlist(self):
        pass


    # search
    def init_search(self):
        pass


    # download
    def init_download(self):
        pass
