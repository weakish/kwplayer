
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

class TreeViewCommonSong(Gtk.TreeView):
    def __init__(self, **keys):
        super().__init__(**keys)
        self.set_headers_visible(False)
        self.set_search_column(0)
        self.props.reorderable = True
        selection = self.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        # rubber_banding selection method causes some problem.
        #self.set_rubber_banding(True)

        self.connect('key-press-event', self.on_key_pressed)

    def on_key_pressed(self, widget, event):
        if event.keyval == Gdk.KEY_Delete:
            selection = self.get_selection()
            model, paths = selection.get_selected_rows()
            # paths needs to be reversed, or else an IndexError throwed.
            for path in reversed(paths):
                model.remove(model[path].iter)

class NormalSongTab(Gtk.ScrolledWindow):
    def __init__(self, liststore):
        super().__init__()

        self.treeview = TreeViewCommonSong(model=liststore)
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

        delete = Gtk.CellRendererPixbuf(icon_name='user-trash-symbolic')
        col_delete = Widgets.TreeViewColumnIcon('Delete', delete)
        self.treeview.append_column(col_delete)
        

class PlayList(Gtk.Box):
    def __init__(self, app):
        super().__init__()

        self.app = app
        self.first_show = False
        # self.liststores contains all playlists
        self.liststores = {}
        # self.lists_name contains playlists name, except `Cached`.
        self.lists_name = []
        self.treeviews = {}
        self.curr_playing = [None, None]

        self.cache_enabled = False
        self.cache_job = None
        self.cache_timeout = 0
        self.curr_caching = [None, None]

        # Use `check_same_thread=False to share sqlite connections between
        # threads
        # FIXME: got segmantation falt
        self.conn = sqlite3.connect(Config.SONG_DB)
        #        check_same_thread=False)
        self.cursor = self.conn.cursor()

        box_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.pack_start(box_left, False, False, 0)

        # disname, name, deletable
        self.liststore_left = Gtk.ListStore(str, str, bool)
        treeview_left = Gtk.TreeView(model=self.liststore_left)
        self.treeviews['_left_'] = treeview_left
        treeview_left.set_headers_visible(False)
        list_name = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn('List Name', list_name, text=0)
        treeview_left.append_column(col_name)
        tree_sel = treeview_left.get_selection()
        tree_sel.connect('changed', self.on_tree_selection_left_changed)
        box_left.pack_start(treeview_left, True, True, 0)

        toolbar = Gtk.Toolbar()
        toolbar.get_style_context().add_class(
                Gtk.STYLE_CLASS_INLINE_TOOLBAR)
                #Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)
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
        #GLib.idle_add(self.init_ui)
        GLib.timeout_add(1500, self.init_ui)

    def do_destroy(self):
        print('do destroy()')
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
        albumid INTEGER,
        filepath CHAR
        )
        '''
        self.cursor.execute(sql)
        self.conn.commit()

    def dump_playlists(self):
        filepath = Config.PLS_JSON
        names = [list(p) for p in self.liststore_left]
        playlists = {'_names_': names}
        for name in names:
            if name[1] == 'Cached':
                continue
            playlists[name[1]] = [list(p) for p in self.liststores[name[1]]]
        with open(filepath, 'w') as fh:
            fh.write(json.dumps(playlists))

    def load_playlists(self):
        filepath = Config.PLS_JSON
        _default = {
                '_names_': [
                    ['已缓存', 'Cached', False],
                    ['正在缓存', 'Caching', False],
                    ['默认列表', 'Default', False],
                    ['喜爱', 'Favorite', False],
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
            list_name = playlist[1]
            self.liststore_left.append(playlist)
            if list_name == 'Cached':
                self.init_cached_tab()
                continue
            elif list_name == 'Caching':
                self.init_caching_tab(playlists['Caching'])
            else:
                self.init_normal_song_tab(list_name, playlists[list_name])
            self.lists_name.append(list_name)

    def init_cached_tab(self):
        songs = self.get_all_cached_songs_from_db()

        # name, artist, album, rid, artistid, albumid, filepath
        liststore = Gtk.ListStore(str, str, str, int, int, 
                int, str)
        self.liststores['Cached'] = liststore
        if songs is not None:
            for song in songs:
                liststore.append(song)
        treeview = TreeViewCommonSong(model=liststore)
        self.treeviews['Cached'] = treeview
        treeview.connect('row_activated', 
                self.on_treeview_songs_row_activated, 'Cached')
        name = Gtk.CellRendererText()
        col_name = Widgets.TreeViewColumnText('Name', name, text=0)
        treeview.append_column(col_name)
        artist = Gtk.CellRendererText()
        col_artist = Widgets.TreeViewColumnText('Artist', artist, text=1)
        treeview.append_column(col_artist)
        album = Gtk.CellRendererText()
        col_album = Widgets.TreeViewColumnText('Album', album, text=2)
        treeview.append_column(col_album)

        scrolled_cached = Gtk.ScrolledWindow()
        scrolled_cached.add(treeview)
        self.notebook.append_page(scrolled_cached, Gtk.Label('Cached'))
        scrolled_cached.show_all()

    def init_caching_tab(self, songs):
        box_caching = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        buttonbox = Gtk.Box()
        box_caching.pack_start(buttonbox, False, False, 0)
        button_start = Gtk.Button('Start Caching')
        button_start.connect('clicked', self.switch_caching_daemon)
        buttonbox.pack_start(button_start, False, False, 0)

        # name, artist, album, rid, artistid, 
        # albumid, filepath
        liststore = Gtk.ListStore(str, str, str, int, int, int, str)
        self.liststores['Caching'] = liststore
        for song in songs:
            liststore.append(song)

        treeview = TreeViewCommonSong(model=liststore)
        scrolled_caching = NormalSongTab(liststore)
        self.treeviews['Caching'] = scrolled_caching.treeview
        scrolled_caching.treeview.connect('row_activated', 
                self.on_treeview_songs_row_activated, 'Caching')
        box_caching.pack_start(scrolled_caching, True, True, 0)

        self.notebook.append_page(box_caching, Gtk.Label('Caching'))
        box_caching.show_all()

    def init_normal_song_tab(self, list_name, songs):
        # name, artist, album, rid, artistid, albumid, filepath
        liststore = Gtk.ListStore(str, str, str, int, int, int, str)
        self.liststores[list_name] = liststore
        for song in songs:
            liststore.append(song)
        scrolled_win = NormalSongTab(liststore)
        self.treeviews[list_name] = scrolled_win.treeview
        scrolled_win.treeview.connect('row_activated', 
                self.on_treeview_songs_row_activated, list_name)
        self.notebook.append_page(scrolled_win, Gtk.Label(list_name))
        scrolled_win.show_all()

    # Side Panel
    def on_tree_selection_left_changed(self, tree_sel):
        '''
        Use left side treeview to switch notebook pages.
        '''
        model, tree_iter = tree_sel.get_selected()
        path = model.get_path(tree_iter)
        index = path.get_indices()[0]
        self.notebook.set_current_page(index)

    # Cached Tab
    def on_treeview_songs_row_activated(self, treeview, path, 
            column, _list_name):
        model = treeview.get_model()
        index = treeview.get_columns().index(column)
        song = Widgets.song_row_to_dict(model[path], start=0)
        song = Widgets.song_row_to_dict(model[path], start=0, withpath=True)
        #self.play_song(song, list_name=_list_name)
        if index == 0:
            self.play_song(song, list_name=_list_name)
        elif index == 1:
            print('will search artist')
        elif index == 2:
            print('will search album')
        elif index == 3:
            print('will delete song from liststore:', song, _list_name)
            model.remove(model[path].iter)

    # Open API for others to call.
    def play_song(self, song, list_name='Default'):
        '''
        If song is in cached_list, set its filepath.
        Else set filepath = ''
        And add this song to default_list
        song is always returned with `filepath` setted.
        So player should check `filepath` is ''
        '''
        liststore = self.liststores[list_name]
        rid = song['rid']
        path = self.get_song_path_in_liststore(liststore, rid)
        if path is not None:
            # curr_playing contains: listname, path
            self.curr_playing = [list_name, path]
            song = Widgets.song_row_to_dict(liststore[path], start=0)
            self.app.player.load(song)
            return
        req = self.get_song_from_cached_db(rid)
        if req is not None:
            song['filepath'] = req[6]
        else:
            song['filepath'] = ''
        liststore.append(Widgets.song_dict_to_row(song))
        self.curr_playing = [list_name, len(liststore)-1, ]
        self.app.player.load(song)

    def play_songs(self, songs):
        self.add_songs_to_playlist(songs, list_name='Default')
        self.play_song(songs[0])

    def add_song_to_playlist(self, song, list_name='Default'):
        liststore = self.liststores[list_name]
        rid = song['rid']
        path = self.get_song_path_in_liststore(liststore, rid)
        if path is not None:
            return
        req = self.get_song_from_cached_db(rid)
        if req is not None:
            song['filepath'] = req[6]
        else:
            song['filepath'] = ''
        liststore.append(Widgets.song_dict_to_row(song))

    def add_songs_to_playlist(self, songs, list_name='Default'):
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
        liststore = self.liststores['Caching']
        path = self.get_song_path_in_liststore(liststore, rid)
        if path is not None:
            print('song is already in caching list, do nothing.')
            return
        song['filepath'] = ''
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
        def on_downloaded(song_info, error):
            print('song_info:', song_info, 'error:', error)
            if song_info is not None:
                self.on_song_downloaded(song_info, is_cache=True)
            self.cache_job = None

        list_name = ''
        path = 0
        for list_name in self.lists_name:
            if len(self.liststores[list_name]) == 0:
                continue
            path = 0
            for row in self.liststores[list_name]:
                if row[6] == '':
                    break
        if len(self.liststores[list_name]) == 0:
            print('all playlists are empty, please add some')
            return
        print('current list_name is:', list_name)
        liststore = self.liststores[list_name]
        self.curr_caching = [list_name, path]
        song_dict = Widgets.song_row_to_dict(liststore[path], start=0)
        print('song dict to download:', song_dict)
        self.cache_job = Net.AsyncSong(self.app)
        self.cache_job.get_song(song_dict, on_downloaded)

    # Others
    def on_song_downloaded(self, song, is_cache=False):
        print('on song downloaded(), is_cache:', is_cache)
        if is_cache:
            current = self.curr_caching
        else:
            current = self.curr_playing
        list_name = current[0]
        path = current[1]
        liststore = self.liststores[list_name]
        print('list_name:', list_name, 'path:', path, 'liststore:', liststore)

        # update filepath ins current liststore
        liststore[path][6] = song['filepath']

        # copy this song from current playing list to cached_list.
        self.append_cached_song(song)

        # if this song is in caching_list, move it to cached_list.
        if list_name == 'Caching':
            print('will remove song from caching_list')
            print('liststore[path].iter:', liststore[path].iter)
            print('thread:', threading.current_thread())
            liststore.remove(liststore[path].iter)

    def get_prev_song(self, repeat=False, shuffle=False):
        print('get prev song()')
        liststore = self.liststores[self.curr_playing[0]]
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
        liststore = self.liststores[self.curr_playing[0]]
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
        if self.curr_playing[0] is None:
            return
        list_name = self.curr_playing[0]
        liststore = self.liststores[list_name]
        treeview = self.treeviews[list_name]
        path = self.curr_playing[1]
        treeview.set_cursor(path)

        left_path = 0
        for item in self.liststore_left:
            if list_name == self.liststore_left[left_path][1]:
                break
            left_path += 1
        selection_left = self.treeviews['_left_'].get_selection()
        selection_left.select_path(left_path)
        # TODO: switch page in self.app.notebook
        # TODO: radio list

    # DB operations
    def append_cached_song(self, song):
        '''
        When a new song is cached locally, call this function.
        Insert a new item to database and liststore_cached.
        '''
        song_list = Widgets.song_dict_to_row(song)
        sql = 'INSERT INTO `songs` values(?, ?, ?, ?, ?, ?, ?)'
        self.cursor.execute(sql, song_list)
        self.liststores['Cached'].append(song_list)

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
