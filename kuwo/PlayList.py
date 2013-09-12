
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
import json
import os
import random
import sqlite3

from kuwo import Net

class PlayList(Gtk.Box):
    def __init__(self, app):
        super().__init__()

        self.app = app

        # Use `check_same_thread=False to share sqlite connections between
        # threads
        self.conn = sqlite3.connect(app.conf['song-db'], 
                check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.caching_job = None

        self.names = ('name', 'artist', 'album', 'rid', 'artistid', 
                'albumid', 'filepath')

        box_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.pack_start(box_left, False, False, 0)

        self.liststore_lists = Gtk.ListStore(str, bool)
        treeview_lists = Gtk.TreeView(model=self.liststore_lists)
        treeview_lists.set_headers_visible(False)
        list_name = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn('List Name', list_name, text=0)
        treeview_lists.append_column(col_name)
        tree_sel = treeview_lists.get_selection()
        tree_sel.connect('changed', self.on_tree_sel_changed)
        box_left.pack_start(treeview_lists, True, True, 0)

        toolbar = Gtk.Toolbar()
        toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)
        toolbar.props.show_arrow = False
        toolbar.props.toolbar_style = Gtk.ToolbarStyle.ICONS
        toolbar.props.icon_size = 1
        box_left.pack_start(toolbar, False, False, 0)

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

        self.notebook = Gtk.Notebook()
        self.notebook.props.show_tabs = False
        self.pack_start(self.notebook, True, True, 0)

        #GObject.idle_add(self.init_ui)
        GLib.timeout_add(500, self.init_ui)

    def do_destroy(self):
        self.conn.commit()
        self.conn.close()
        self.dump_playlist()

    def after_init(self):
        pass

    def first(self):
        pass

    def init_ui(self):
        self.init_table()
        self.load_playlist()
        return False

    def init_table(self):
        sql = '''
        CREATE TABLE IF NOT EXISTS `songs` (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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

        sql = '''
        CREATE TABLE IF NOT EXISTS `caching` (
        NAME CHAR,
        artist CHAR,
        album CHAR,
        rid INTEGER,
        artistid INTEGER,
        albumid INTEGER,
        filepath CHAR,
        status INT,
        percent INT
        )
        '''
        self.cursor.execute(sql)
        self.conn.commit()

    def load_playlist(self):
        filepath = self.app.conf['playlists']
        _default = {
                'Caching': ('Caching', True, []),
                'Default Playlist': ('Default Playlist', True, []),
                'custom': [],
                }
        if os.path.exists(filepath):
            with open(filepath) as fh:
                playlists = json.loads(fh.read())
        else:
            playlists = _default

        self.init_cached_tab()
        self.init_caching_tab()

    def init_cached_tab(self):
        self.liststore_lists.append(['Cached', True])
        songs = self.get_all_cached_songs_from_db()

        scrolled_cached = Gtk.ScrolledWindow()
        # checked, name, artist, album, rid, artistid, albumid, filepath
        self.liststore_cached = Gtk.ListStore(bool, str, str, str, 
                int, int, int, str)
        if songs is not None:
            for song in songs:
                self.liststore_cached.append((True, ) + song[1:])

        treeview = Gtk.TreeView(model=self.liststore_cached)
        treeview.set_search_column(1)
        treeview.connect('row_activated', 
                self.on_treeview_cached_row_activated)
        scrolled_cached.add(treeview)

        checked = Gtk.CellRendererToggle()
        col_check = Gtk.TreeViewColumn('Checked', checked, active=0)
        treeview.append_column(col_check)

        name = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn('Name', name, text=1)
        treeview.append_column(col_name)

        artist = Gtk.CellRendererText()
        col_artist = Gtk.TreeViewColumn('Artist', artist, text=2)
        treeview.append_column(col_artist)

        album = Gtk.CellRendererText()
        col_album = Gtk.TreeViewColumn('Album', album, text=3)
        treeview.append_column(col_album)

        self.notebook.append_page(scrolled_cached, Gtk.Label('Cached'))
        scrolled_cached.show_all()

    def init_caching_tab(self):
        self.liststore_lists.append(['Caching', True])
        box_caching = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        scrolled_caching = Gtk.ScrolledWindow()
        box_caching.pack_start(scrolled_caching, True, True, 0)

        # checked, name, artist, album, rid, artistid, albumid, filepath
        # status, percent
        self.liststore_caching = Gtk.ListStore(bool, str, str, str, 
                int, int, int, str, int, int)
        songs = self.get_all_caching_songs_from_db()
        if songs is not None:
            for song in songs:
                self.liststore_caching.append((True, ) + song)

        treeview = Gtk.TreeView(model=self.liststore_caching)

        checked = Gtk.CellRendererToggle()
        col_check = Gtk.TreeViewColumn('Checked', checked, active=0)
        treeview.append_column(col_check)

        name = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn('Name', name, text=1)
        treeview.append_column(col_name)

        artist = Gtk.CellRendererText()
        col_artist = Gtk.TreeViewColumn('Artist', artist, text=2)
        treeview.append_column(col_artist)

        album = Gtk.CellRendererText()
        col_album = Gtk.TreeViewColumn('Album', album, text=3)
        treeview.append_column(col_album)

        percent = Gtk.CellRendererProgress()
        col_percent = Gtk.TreeViewColumn('Process', percent, value=9)
        treeview.append_column(col_percent)

        scrolled_caching.add(treeview)

        buttonbox = Gtk.Box(spacing=5)
        box_caching.pack_start(buttonbox, False, False, 0)

        def on_button_selectall_toggled(btn):
            pass

        button_selectall = Gtk.ToggleButton('Select All')
        button_selectall.set_active(True)
        button_selectall.connect('toggled', on_button_selectall_toggled)
        buttonbox.pack_start(button_selectall, False, False, 0)

        button_start = Gtk.Button('Start')
        buttonbox.pack_start(button_start, False, False, 0)

        button_pause = Gtk.Button('Pause')
        buttonbox.pack_start(button_pause, False, False, 0)

        button_remove = Gtk.Button('Remove')
        buttonbox.pack_start(button_remove, False, False, 0)

        self.notebook.append_page(box_caching, Gtk.Label('Caching'))
        box_caching.show_all()



    def dump_playlist(self):
        '''
         Dump all the liststores
        '''
        return 

    # Side Panel
    def on_tree_sel_changed(self, tree_sel):
        '''
        Left side panel to switch notebook pages.
        '''
        model, tree_iter = tree_sel.get_selected()
        path = model.get_path(tree_iter)
        index = path.get_indices()[0]
        self.notebook.set_current_page(index)


    # Cached Tab
    def on_treeview_cached_row_activated(self, treeview, path, column):
        song = dict(zip(self.names, self.liststore_cached[path][1:]))
        self.app.player.load(song)

    # Open API for others to call.
    def play_song(self, song):
        '''
        If song is in cached_list, return it.
        Elif song is caching, remove it and return None
        Else return None
        '''
        print('play song()')
        req = self.get_song_from_cached_db(song['rid'])
        if req is not None:
            return dict(zip(self.names, req[1:]))

        if len(self.liststore_caching) == 0:
            return None

        i = 0
        for item in self.liststore_caching:
            if item[4] == song['rid']:
                break
            i += 1
        if i == len(self.liststore_caching) - 1:
            return None
        song_caching = self.liststore_caching[i]
        if song_caching[8] == 0:
            self.liststore_caching.remove(song_caching.iter)
            self.remove_song_from_caching_db(song['rid'])
            return None
        else:
            return dict(zip(self.names, song_caching[1:8]))

    def append_song(self, song):
        pass

    def cache_songs(self, songs):
        for song in songs:
            self.cache_song(song)

    def cache_song(self, song):
        print('cache song()')
        # first, check if this song exists in cached_db
        exists = self.get_song_from_cached_db(song['rid'])
        if exists is not None:
            print('local cache exists, quit')
            return

        # second, insert song to self.liststore_caching and db
        exists = self.get_song_from_liststore(self.liststore_caching, song)
        if exists is not None:
            print('song is already in caching list, do nothing.')
            return

        song_list = [
                True, song['name'], song['artist'], song['album'],
                song['rid'], song['artistid'], song['albumid'], '', 0, 0,
                ]
        self.liststore_caching.append(song_list)

        if self.caching_job is None:
            self.do_cache_song_pool()

    def do_cache_song_pool(self):
        '''
        This function can be started after process started.
        '''
        def on_chunk_received(widget, song, percent):
            print('on chunk received')
            print(song, percent)
            path = self.get_song_from_liststore(self.liststore_caching, song)
            if path is None:
                return
            self.liststore_caching[path][9] = percent

        def on_downloaded(widget, song):
            print('on downloaded()', song)
            if song is not None:
                Gdk.threads_enter()
                self.append_cached_song(song)
                self.remove_caching_song(song)
                Gdk.threads_leave()
            self.do_cache_song_pool()

        print('do_cache_song_pool()')

        if len(self.liststore_caching) == 0:
            print('liststore caching is empty')
            self.caching_job = None
            return

        song_caching = self.liststore_caching[0]
        song_dict = dict(zip(self.names, song_caching[1:8]))
        if self.caching_job is None:
            self.caching_job = Net.AsyncSong()
            self.caching_job.connect('chunk-received', on_chunk_received)
            self.caching_job.connect('downloaded', on_downloaded)
        print('will call get_song()')
        print(song_dict)
        self.caching_job.get_song(song_dict)

    # 
    def get_next_song(self, song, repeat=False, shuffle=False):
        song_nums = len(self.liststore_cached)
        if song_nums == 0:
            return None

        if shuffle:
            path = random.randint(0, song_nums-1)
            return dict(zip(self.names, self.liststore_cached[path][1:]))

        path = self.get_song_from_liststore(self.liststore_cached, song)
        if path == song_nums - 1:
            if repeat is False:
                return None
            return dict(zip(self.names, self.liststore_cached[path][1:]))
        return dict(zip(self.names, self.liststore_cached[path+1][1:]))


    # DB operations
    def append_cached_song(self, song):
        '''
        When a new song is cached locally, call this function.
        Insert a new item to database and liststore_cached.
        '''
        song_list = [
                song['name'], song['artist'], song['album'], song['rid'], 
                song['artistid'], song['albumid'], song['filepath'], 
                ]
        sql = '''INSERT INTO `songs`(
        name, artist, album, rid, artistid, albumid, filepath
        ) values(?, ?, ?, ?, ?, ?, ?)'''
        self.cursor.execute(sql, song_list)
        self.liststore_cached.append([True, ] + song_list)

    def get_all_cached_songs_from_db(self):
        sql = 'SELECT * FROM `songs`'
        return self.cursor.execute(sql)

    def get_all_caching_songs_from_db(self):
        sql = 'SELECT * FROM `caching`'
        return self.cursor.execute(sql)

    def get_song_from_cached_db(self, rid):
        sql = 'SELECT * FROM `songs` WHERE rid=? LIMIT 1'
        result = self.cursor.execute(sql, (rid, ))
        return result.fetchone()

    def get_song_from_liststore(self, liststore, song):
        i = 0
        for item in liststore:
            if item[4] == song['rid']:
                break
            i += 1
        if i == len(liststore):
            return None
        return i

    def remove_song_from_caching_db(self, rid):
        sql = 'DELETE FROM `caching` WHERE rid=?'
        self.cursor.execute(sql, (rid, ))

    def remove_caching_song(self, song):
        print('song will removed from caching db:', song)
        i = self.get_song_from_liststore(self.liststore_caching, song)
        song_caching = self.liststore_caching[i]
        self.liststore_caching.remove(song_caching.iter)
        self.remove_song_from_caching_db(song['rid'])
