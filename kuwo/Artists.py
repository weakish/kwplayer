
from gi.repository import Gtk
from gi.repository import GdkPixbuf
import time

from kuwo import Net


class Artists(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.first_show = False

        self.buttonbox = Gtk.Box()
        self.pack_start(self.buttonbox, False, False, 0)

        button_home = Gtk.Button('Artists')
        button_home.connect('clicked', self.on_button_home_clicked)
        self.buttonbox.pack_start(button_home, False, False, 0)

        self.label = Gtk.Label('')
        self.buttonbox.pack_start(self.label, False, False, 20)

        button_cache = Gtk.Button('Cache')
        button_cache.connect('clicked', self.on_button_cache_clicked)
        self.buttonbox.pack_end(button_cache, False, False, 0)

        button_play = Gtk.Button('Play')
        self.buttonbox.pack_end(button_play, False, False, 0)

        button_selectall = Gtk.ToggleButton('Select All')
        button_selectall.set_active(True)
        #button_selectall.connect('toggled', self.on_button_selectall_toggled)
        self.buttonbox.pack_end(button_selectall, False, False, 0)

        self.box_artists = Gtk.Box()
        self.pack_start(self.box_artists, True, True, 0)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box_artists.pack_start(box, False, False, 0)

        # name, id
        self.liststore_cate = Gtk.ListStore(str, int)
        self.treeview_cate = Gtk.TreeView(model=self.liststore_cate)
        self.treeview_cate.props.headers_visible = False

        name = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn('Name', name, text=0)
        self.treeview_cate.append_column(col_name)
        box.pack_start(self.treeview_cate, False, False, 0)

        self.liststore_pref = Gtk.ListStore(str, str)
        self.combo_pref = Gtk.ComboBox(model=self.liststore_pref)
        cell_name = Gtk.CellRendererText()
        self.combo_pref.pack_start(cell_name, True)
        self.combo_pref.add_attribute(cell_name, 'text', 0)
        self.combo_pref.props.margin_top = 15
        box.pack_start(self.combo_pref, False, False, 0)

        scrolled_artists = Gtk.ScrolledWindow()
        adj = scrolled_artists.get_vadjustment()
        adj.connect('value-changed', self.on_artists_window_scrolled)
        self.box_artists.pack_start(scrolled_artists, True, True, 0)

        # logo, name, nid
        self.liststore_artists = Gtk.ListStore(GdkPixbuf.Pixbuf, str, int)
        iconview_artists = Gtk.IconView(model=self.liststore_artists)
        iconview_artists.set_pixbuf_column(0)
        iconview_artists.set_text_column(1)
        iconview_artists.set_item_width(95)
        iconview_artists.connect('item_activated', 
                self.on_iconview_artists_item_activated)
        scrolled_artists.add(iconview_artists)

        self.scrolled_songs = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_songs, True, True, 0)

        # checked, name, artist, album, rid, artistid, albumid
        # play, add, cache
        self.liststore_songs = Gtk.ListStore(bool, str, str, str, int, int,
                int, GdkPixbuf.Pixbuf, GdkPixbuf.Pixbuf, GdkPixbuf.Pixbuf)
        treeview_songs = Gtk.TreeView(model=self.liststore_songs)
        treeview_songs.set_headers_visible(False)
        treeview_songs.connect('row_activated', 
                self.on_treeview_songs_row_activated)
        self.scrolled_songs.add(treeview_songs)

        checked = Gtk.CellRendererToggle()
        checked.connect('toggled', self.on_song_checked)
        column_check = Gtk.TreeViewColumn('Checked', checked, active=0)
        treeview_songs.append_column(column_check)

        name = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn('Name', name, text=1)
        col_name.props.sizing = Gtk.TreeViewColumnSizing.AUTOSIZE
        col_name.props.expand = True
        treeview_songs.append_column(col_name)

        artist = Gtk.CellRendererText()
        col_artist = Gtk.TreeViewColumn('Artist', artist, text=2)
        col_artist.props.sizing = Gtk.TreeViewColumnSizing.AUTOSIZE
        col_artist.props.expand = True
        treeview_songs.append_column(col_artist)

        album = Gtk.CellRendererText()
        col_album = Gtk.TreeViewColumn('Album', album, text=3)
        col_album.props.sizing = Gtk.TreeViewColumnSizing.AUTOSIZE
        col_album.props.expand = True
        treeview_songs.append_column(col_album)

        play = Gtk.CellRendererPixbuf()
        col_play = Gtk.TreeViewColumn('Play', play, pixbuf=7)
        col_play.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        col_play.props.fixed_width = 20
        treeview_songs.append_column(col_play)

        add = Gtk.CellRendererPixbuf()
        col_add = Gtk.TreeViewColumn('Add', add, pixbuf=8)
        col_add.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        col_add.props.fixed_width = 20
        treeview_songs.append_column(col_add)

        cache = Gtk.CellRendererPixbuf()
        col_cache = Gtk.TreeViewColumn('Cache', cache, pixbuf=9)
        col_cache.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        col_cache.props.fixed_width = 20
        treeview_songs.append_column(col_cache)

    def after_init(self):
        self.buttonbox.hide()
        self.scrolled_songs.hide()

    def first(self):
        if self.first_show:
            return
        self.first_show = True
        prefs = (
                ('All', ''), ('A', 'a'), ('B', 'b'), ('C', 'c'), ('D', 'd'),
                ('E', 'e'), ('F', 'f'), ('G', 'g'), ('H', 'h'), ('I', 'i'),
                ('J', 'j'), ('K', 'k'), ('L', 'l'), ('M', 'm'), ('N', 'n'),
                ('O', 'o'), ('P', 'p'), ('Q', 'q'), ('R', 'r'), ('S', 's'),
                ('T', 't'), ('U', 'u'), ('V', 'v'), ('W', 'w'), ('X', 'x'),
                ('Y', 'y'), ('Z', 'z'), ('#', '%26'),
                )
        for pref in prefs:
            self.liststore_pref.append(pref)
        self.combo_pref.set_active(0)
        self.combo_pref.connect('changed', self.on_cate_changed)

        cates = (
                ('热门歌手', 0),
                ('华语男', 1),
                ('华语女', 2),
                ('华语组合', 3),
                ('日韩男', 4),
                ('日韩女', 5),
                ('日韩组合', 6),
                ('欧美男', 7),
                ('欧美女', 8),
                ('欧美组合', 9),
                ('其他', 10),
                )
        for cate in cates:
            self.liststore_cate.append(cate)
        selection = self.treeview_cate.get_selection()
        #self.treeview_cate.connect('row_activated', self.on_cate_changed)
        selection.connect('changed', self.on_cate_changed)
        selection.select_path(0)

    def on_cate_changed(self, *args):
        self.append_artists(init=True)
        return True

    def on_artists_window_scrolled(self, adj):
        timestamp = time.time()
        if adj.get_upper() - adj.get_page_size() - adj.get_value() < 40 and\
                timestamp - self.artists_appended_timestamp > 2:
            self.artists_appended_timestamp = timestamp
            self.append_artists()
        else:
            print('on artists window scrolled, do nothing')

    def append_artists(self, init=False):
        if init:
            self.liststore_artists.clear()
            self.curr_artist_page = 0
        selection = self.treeview_cate.get_selection()
        result = selection.get_selected()
        if result is not None and len(result) == 2:
            model, _iter = result
        else:
            return
        pref_index = self.combo_pref.get_active()
        catid = model[_iter][1]
        prefix = self.liststore_pref[pref_index][1]
        artists_wrap = Net.get_artists(catid, self.curr_artist_page, prefix)
        if 'artistlist' in artists_wrap:
            artists = artists_wrap['artistlist']
        else:
            return

        artists_total = int(artists_wrap['total'])
        if artists_total < 200 * self.curr_artist_page:
            return

        self.artists_appended_timestamp = time.time()
        i = len(self.liststore_artists)
        for artist in artists:
            self.liststore_artists.append([self.app.theme['anonymous'],
                artist['name'], int(artist['id']), ])
            Net.update_artist_logo(self.liststore_artists, i, 0, 
                    artist['pic'])
            i += 1
        self.curr_artist_page += 1


    def on_iconview_artists_item_activated(self, iconview, path):
        model = iconview.get_model()
        self.label.set_label(model[path][1])
        self.curr_artist_name = model[path][1]
        self.curr_song_page = 0
        self.show_artists_songs()

    def show_artists_songs(self):
        self.box_artists.hide()
        self.buttonbox.show_all()
        self.scrolled_songs.show_all()
        songs_wrap = Net.get_artist_songs(self.curr_artist_name,
                self.curr_song_page)
        if songs_wrap is None:
            return
        songs = songs_wrap['abslist']
        self.liststore_songs.clear()
        for song in songs:
            self.liststore_songs.append([True, song['SONGNAME'], 
                song['ARTIST'], song['ALBUM'], int(song['MUSICRID'][6:]), 
                int(song['ARTISTID']), int(song['ALBUMID']), 
                self.app.theme['play'], self.app.theme['add'],
                self.app.theme['cache'], ])



    # Song window
    def on_button_home_clicked(self, btn):
        self.box_artists.show_all()
        self.scrolled_songs.hide()
        self.buttonbox.hide()

    def on_button_cache_clicked(self, btn):
        print('on button cache clicked')
        songs = [self.song_modelrow_to_dict(song) for song in self.liststore_songs if song[0]]
        #self.app.playlist.cache_songs(songs)

    def on_treeview_songs_row_activated(self, treeview, path, column):
        liststore = treeview.get_model()
        index = treeview.get_columns().index(column)
        song = self.song_modelrow_to_dict(liststore[path])

        if index in (1, 4):
            # level 1
            print('will play song')
            #self.app.player.load(song)
        elif index == 2:
            print('will search artist')
        elif index == 3:
            print('will search album')
        elif index == 5:
            # level 2
            print('will append song')
            #self.app.playlist.append_song(song)
        elif index == 6:
            # level 3
            print('will cache song')
            #self.app.playlist.cache_song(song)


    def on_song_checked(self, widget, path):
        self.liststore_songs[path][0] = not self.liststore_songs[path][0]

    def song_modelrow_to_dict(self, song_row):
        song = {
                'name': song_row[1],
                'artist': song_row[2],
                'album': song_row[3],
                'rid': song_row[4],
                'artistid': song_row[5],
                'albumid': song_row[6],
                'filepath': '',
                }
        return song
