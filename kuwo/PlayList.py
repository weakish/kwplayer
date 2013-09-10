
from gi.repository import Gtk
import json
import os
import sqlite3

class PLTab(Gtk.ScrolledWindow):
    def __init__(self, songs):
        super().__init__()

        # checked, name, artist, album, rid, artistid, albumid, filepath
        self.liststore = Gtk.ListStore(bool, str, str, str, int, int, int, 
                str)
        if songs is not None:
            for song in songs:
                self.liststore.append((True, ) + song[1:])

        treeview = Gtk.TreeView(model=self.liststore)
        self.add(treeview)

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


class PlayList(Gtk.Box):
    def __init__(self, app):
        super().__init__()

        self.app = app

        self.conn = sqlite3.connect(app.conf['song-db'])
        self.cursor = self.conn.cursor()
        self.playlists = None

        box_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.pack_start(box_left, False, False, 0)

        self.liststore_lists = Gtk.ListStore(str, bool)
        treeview_lists = Gtk.TreeView(model=self.liststore_lists)
        treeview_lists.set_headers_visible(False)
        list_name = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn('List Name', list_name, text=0)
        treeview_lists.append_column(col_name)
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
        self.pack_start(self.notebook, True, True, 0)

        self.first_run = False

    def do_destroy(self):
        self.conn.commit()
        self.conn.close()
        self.dump_playlist()

    def after_init(self):
        pass

    def first(self):
        if self.first_run:
            return
        self.first_run = True
        self.first_init_table()
        self.first_load_playlist()

    def first_init_table(self):
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
        self.conn.commit()

    def first_load_playlist(self):
        print('playlist load playlist()')
        filepath = self.app.conf['playlists']
        _default = [
                ('本地缓存', True, [0]),
                ('正在缓存', True, []),
                ('默认列表', True, []),
                ]
        if os.path.exists(filepath):
            with open(filepath) as fh:
                self.playlists = json.loads(fh.read())
        else:
            self.playlists = _default

        for playlist in self.playlists:
            self.liststore_lists.append(playlist[:2])
            if playlist[2] == [0]:
                songs = self.get_all_songs()
            else:
                songs = self.get_songs(playlist[2])
            tab = PLTab(songs)
            self.notebook.append_page(tab, Gtk.Label(playlist[0]))
            tab.show_all()

    def get_all_songs(self):
        sql = 'SELECT * FROM `songs`'
        return self.cursor.execute(sql)

    def get_songs(self, lists):
        if len(lists) == 0:
            return None
        sql = ''.join([
            'SELECT * FROM `songs` WHERE rid in (',
            ','.join([str(i) for i in lists]),
            ')',
            ])
        return self.cursor.execute(sql).fetchall()

    def dump_playlist(self):
        if self.playlists is None:
            return
        with open(self.app.conf['playlists'], 'w') as fh:
            fh.write(json.dumps(self.playlists))


    def append(self, song):
        pass

    def cache(self, song):
        pass



    def play_song(self, song):
        '''
        If song is in default_list, return it.
        Elif song is in cache_list, copy it to default_list and return it.
        Else return None
        '''
        print('play song()')
        sql = 'SELECT * FROM `songs` WHERE rid=? LIMIT 1'
        result = self.cursor.execute(sql, (song['rid'], ))
        song = result.fetchone()
        if song is None:
            return None
        names = ('id', 'name', 'artist', 'album', 'rid', 'artistid', 'albumid', 'filepath')
        return dict(zip(names, song))
        #if self.playlists[

    def append_song(self, song):
        sql = '''INSERT INTO `songs`(
        name, artist, album, rid, artistid, albumid, filepath
        ) values(?, ?, ?, ?, ?, ?, ?)'''
        self.cursor.execute(sql, [song['name'], song['artist'], 
            song['album'], song['rid'], song['artistid'], song['albumid'],
            song['filepath'], ])
