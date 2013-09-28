
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
import json
import os
import random
import sqlite3
import threading

from kuwo import Config
from kuwo import Net
from kuwo import Widgets


class NormalSongTab(Gtk.ScrolledWindow):
    def __init__(self, app, list_name):
        super().__init__()
        self.app = app
        self.list_name = list_name

        # name, artist, album, rid, artistid, albumid
        self.liststore = Gtk.ListStore(str, str, str, int, int, int)

        self.treeview = Gtk.TreeView(model=self.liststore)
        self.treeview.set_headers_visible(False)
        self.treeview.set_search_column(0)
        self.treeview.props.reorderable = True
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.treeview.connect('row_activated', 
                self.on_treeview_row_activated)
        self.add(self.treeview)

        song_name = Gtk.CellRendererText()
        col_song = Widgets.TreeViewColumnText('Name', song_name, text=0)
        self.treeview.append_column(col_song)

        artist = Gtk.CellRendererText()
        col_artist = Widgets.TreeViewColumnText('Aritst', artist, text=1)
        self.treeview.append_column(col_artist)

        album = Gtk.CellRendererText()
        col_album = Widgets.TreeViewColumnText('Album', album, text=2)
        self.treeview.append_column(col_album)

        if list_name != 'Cached':
            delete = Gtk.CellRendererPixbuf(icon_name='user-trash-symbolic')
            col_delete = Widgets.TreeViewColumnIcon('Delete', delete)
            self.treeview.append_column(col_delete)
            self.connect('key-press-event', self.on_key_pressed)
        
    def on_key_pressed(self, widget, event):
        if event.keyval == Gdk.KEY_Delete:
            selection = self.treeview.get_selection()
            model, paths = selection.get_selected_rows()
            # paths needs to be reversed, or else an IndexError throwed.
            for path in reversed(paths):
                model.remove(model[path].iter)

    def on_treeview_row_activated(self, treeview, path, column):
        model = treeview.get_model()
        index = treeview.get_columns().index(column)
        song = Widgets.song_row_to_dict(model[path], start=0)
        if index == 0:
            self.app.playlist.play_song(song, list_name=self.list_name)
        elif index == 1:
            self.app.search.search_artist(song['artist'])
        elif index == 2:
            self.app.search.search_album(song['album'])
        elif index == 3:
            model.remove(model[path].iter)

class PlayList(Gtk.Box):
    def __init__(self, app):
        super().__init__()

        self.app = app
        self.first_show = False
        self.tabs = {}
        # self.lists_name contains playlists name
        self.lists_name = []
        # use curr_playing to locate song in treeview
        self.curr_playing = [None, None]

        self.cache_enabled = False
        self.cache_job = None
        self.cache_timeout = 0

        self.conn = sqlite3.connect(Config.SONG_DB)
        self.cursor = self.conn.cursor()

        box_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.pack_start(box_left, False, False, 0)

        # disname, name, deletable
        self.liststore_left = Gtk.ListStore(str, str, bool)
        self.treeview_left = Gtk.TreeView(model=self.liststore_left)
        self.treeview_left.set_headers_visible(False)
        list_name = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn('List Name', list_name, text=0)
        self.treeview_left.append_column(col_name)
        tree_sel = self.treeview_left.get_selection()
        tree_sel.connect('changed', self.on_tree_selection_left_changed)
        box_left.pack_start(self.treeview_left, True, True, 0)

        toolbar = Gtk.Toolbar()
        # TODO, connect signals
        toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_INLINE_TOOLBAR)
        toolbar.props.show_arrow = False
        toolbar.props.toolbar_style = Gtk.ToolbarStyle.ICONS
        toolbar.props.icon_size = 1
        add_btn = Gtk.ToolButton()
        add_btn.set_name('Add')
        add_btn.set_icon_name('list-add-symbolic')
        toolbar.insert(add_btn, 0)
        remove_btn = Gtk.ToolButton()
        remove_btn.set_name('Remove')
        remove_btn.set_icon_name('list-remove-symbolic')
        toolbar.insert(remove_btn, 1)
        export_btn = Gtk.ToolButton()
        export_btn.set_name('Export')
        export_btn.set_icon_name('media-eject-symbolic')
        toolbar.insert(export_btn, 2)
        box_left.pack_start(toolbar, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.props.show_tabs = False
        self.pack_start(self.notebook, True, True, 0)

        # Use this trick to accelerate startup speed of app.
        GLib.timeout_add(1500, self.init_ui)

    def do_destroy(self):
        self.conn.commit()
        self.conn.close()
        self.dump_playlists()

    def after_init(self):
        pass

    def first(self):
        pass

    def init_ui(self):
        self.init_table()
        self.load_playlists()
        return False

    def init_table(self):
        sql = '''
        CREATE TABLE IF NOT EXISTS `songs` (
        name CHAR,
        artist CHAR,
        album CHAR,
        rid INTEGER,
        artistid INTEGER,
        albumid INTEGER
        )
        '''
        self.cursor.execute(sql)
        self.conn.commit()

    def dump_playlists(self):
        filepath = Config.PLS_JSON
        names = [list(p) for p in self.liststore_left]
        playlists = {'_names_': names}
        for name in names:
            list_name = name[1]
            if list_name == 'Cached':
                continue
            liststore = self.tabs[list_name].liststore
            playlists[list_name] = [list(p) for p in liststore]
        with open(filepath, 'w') as fh:
            fh.write(json.dumps(playlists))

    def load_playlists(self):
        filepath = Config.PLS_JSON
        _default = {
                '_names_': [
                    ['Cached', 'Cached', False],
                    ['Caching', 'Caching', False],
                    ['Default', 'Default', False],
                    ['Favorite', 'Favorite', False],
                    ],
                'Caching': [],
                'Default': [],
                'Favorite': [],
                }
        if os.path.exists(filepath):
            with open(filepath) as fh:
                playlists = json.loads(fh.read())
        else:
            playlists = _default

        for playlist in playlists['_names_']:
            self.liststore_left.append(playlist)
            list_name = playlist[1]
            if list_name == 'Cached':
                songs = self.get_all_cached_songs_from_db()
            else:
                songs = playlists[list_name]
            self.init_tab(list_name, songs)

    def init_tab(self, list_name, songs):
        scrolled_win = NormalSongTab(self.app, list_name)
        for song in songs:
            scrolled_win.liststore.append(song)
        if list_name == 'Caching':
            box_caching = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            buttonbox = Gtk.Box()
            box_caching.pack_start(buttonbox, False, False, 0)
            button_start = Gtk.Button('Start Caching')
            button_start.connect('clicked', self.switch_caching_daemon)
            buttonbox.pack_start(button_start, False, False, 0)
            box_caching.pack_start(scrolled_win, True, True, 0)
            self.notebook.append_page(box_caching, Gtk.Label('Caching'))
            box_caching.show_all()
        else:
            self.notebook.append_page(scrolled_win, Gtk.Label(list_name))
            scrolled_win.show_all()
        self.tabs[list_name] = scrolled_win

    # Side Panel
    def on_tree_selection_left_changed(self, tree_sel):
        model, tree_iter = tree_sel.get_selected()
        path = model.get_path(tree_iter)
        index = path.get_indices()[0]
        self.notebook.set_current_page(index)

    # Open API for others to call.
    def play_song(self, song, list_name='Default'):
        if not song:
            return
        liststore = self.tabs[list_name].liststore
        rid = song['rid']
        path = self.get_song_path_in_liststore(liststore, rid)
        if path is not None:
            # curr_playing contains: listname, path
            self.curr_playing = [list_name, path]
            song = Widgets.song_row_to_dict(liststore[path], start=0)
            self.app.player.load(song)
            return
        liststore.append(Widgets.song_dict_to_row(song))
        self.curr_playing = [list_name, len(liststore)-1, ]
        self.app.player.load(song)

    def play_songs(self, songs):
        if not songs or len(songs) == 0:
            return
        self.add_songs_to_playlist(songs, list_name='Default')
        self.play_song(songs[0])

    def add_song_to_playlist(self, song, list_name='Default'):
        liststore = self.tabs[list_name].liststore
        rid = song['rid']
        path = self.get_song_path_in_liststore(liststore, rid)
        if path is not None:
            return
        liststore.append(Widgets.song_dict_to_row(song))

    def add_songs_to_playlist(self, songs, list_name='Default'):
        print('PlayList.add_songs_to_playlist()')
        print('list name:', list_name)
        for song in songs:
            self.add_song_to_playlist(song, list_name=list_name)

    def cache_song(self, song):
        rid = song['rid']
        # first, check if this song exists in cached_db
        req = self.get_song_from_cached_db(rid)
        if req is not None:
            print('local cache exists, quit')
            return
        # second, check song in caching_liststore.
        liststore = self.tabs['Caching'].liststore
        path = self.get_song_path_in_liststore(liststore, rid)
        if path is not None:
            print('song is already in caching list, do nothing.')
            return
        liststore.append(Widgets.song_dict_to_row(song))

    def cache_songs(self, songs):
        for song in songs:
            self.cache_song(song)

    # song cache daemon
    def switch_caching_daemon(self, btn):
        print('switch caching daemon')
        if not self.cache_enabled:
            self.cache_enabled = True
            btn.set_label('Stop Caching')
            self.cache_timeout = GLib.timeout_add(5000, 
                    self.start_cache_daemon)
        else:
            self.cache_enabled = False
            if self.cache_timeout > 0:
                GLib.source_remove(self.cache_timeout)
            btn.set_label('Start Caching')

    def start_cache_daemon(self):
        if self.cache_enabled:
            if self.cache_job is None:
                self.do_cache_song_pool()
            return True
        else:
            return False

    def do_cache_song_pool(self):
        def _on_downloaded(widget, song_path, error=None):
            self.cache_job = None
            GLib.idle_add(self.on_song_downloaded, song_dict, 'Caching')

        list_name = 'Caching'
        liststore = self.tabs[list_name].liststore
        if len(liststore) == 0:
            print('Caching playlist is empty, please add some')
            return
        song_dict = Widgets.song_row_to_dict(liststore[0], start=0)
        print('song dict to download:', song_dict)
        self.cache_job = Net.AsyncSong(self.app)
        self.cache_job.connect('downloaded', _on_downloaded)
        self.cache_job.get_song(song_dict)

    # Others
    def on_song_downloaded(self, song_info, list_name=None):
        # copy this song from current playing list to cached_list.
        if song_info:
            self.append_cached_song(song_info)
        if list_name == 'Caching':
            path = 0
            liststore = self.tabs[list_name].liststore
            liststore.remove(liststore[path].iter)
        Gdk.Window.process_all_updates()

    def get_prev_song(self, repeat=False, shuffle=False):
        print('get prev song()')
        list_name = self.curr_playing[0]
        if list_name is None:
            return
        liststore = self.tabs[list_name].liststore
        path = self.curr_playing[1]
        song_nums = len(liststore)
        if song_nums == 0:
            return None
        if shuffle:
            path = random.randint(0, song_nums-1)
        elif path == 0:
            # Already reach top of the list, maybe we can repeat from bottom
            path = 0
        else:
            path = path - 1
        self.curr_playing[1] = path
        return Widgets.song_row_to_dict(liststore[path], start=0)

    def get_next_song(self, repeat=False, shuffle=False):
        print('get next song()')
        list_name = self.curr_playing[0]
        liststore = self.tabs[list_name].liststore
        path = self.curr_playing[1]
        song_nums = len(liststore)
        if song_nums == 0:
            return None

        if shuffle:
            path = random.randint(0, song_nums-1)
        elif path == song_nums - 1:
            if repeat is False:
                return None
            # repeat from the first song
            path = 0
        else:
            path = path + 1
        self.curr_playing[1] = path
        return Widgets.song_row_to_dict(liststore[path], start=0)

    def locate_curr_song(self):
        '''
        switch current playlist and select curr_song
        '''
        list_name = self.curr_playing[0]
        if list_name is None:
            return
        treeview = self.tabs[list_name].treeview
        liststore = treeview.get_model()
        path = self.curr_playing[1]
        treeview.set_cursor(path)

        left_path = 0
        for item in self.liststore_left:
            if list_name == self.liststore_left[left_path][1]:
                break
            left_path += 1
        selection_left = self.treeview_left.get_selection()
        selection_left.select_path(left_path)

    # DB operations
    def append_cached_song(self, song):
        '''
        When a new song is cached locally, call this function.
        Insert a new item to database and liststore_cached.
        '''
        # check this song already exists.
        req = self.get_song_from_cached_db(song['rid'])
        if req:
            return
        song_list = Widgets.song_dict_to_row(song)
        sql = 'INSERT INTO `songs` values(?, ?, ?, ?, ?, ?)'
        self.cursor.execute(sql, song_list)
        self.tabs['Cached'].liststore.append(song_list)

    def get_all_cached_songs_from_db(self):
        # TODO: use scrollbar to dynamically load.
        sql = 'SELECT * FROM `songs`'
        result = self.cursor.execute(sql)
        return result

    def get_song_from_cached_db(self, rid):
        sql = 'SELECT * FROM `songs` WHERE rid=? LIMIT 1'
        result = self.cursor.execute(sql, (rid, ))
        return result.fetchone()

    def get_song_path_in_liststore(self, liststore, rid, pos=3):
        i = 0
        for item in liststore:
            if item[pos] == rid:
                return i
            i += 1
        return None
