
from gi.repository import GdkPixbuf
from gi.repository import Gtk
import time

from kuwo import Net
from kuwo import Widgets


class Artists(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.first_show = False

        self.buttonbox = Gtk.Box()
        self.pack_start(self.buttonbox, False, False, 0)

        button_home = Gtk.Button('歌手')
        button_home.connect('clicked', self.on_button_home_clicked)
        self.buttonbox.pack_start(button_home, False, False, 0)

        self.label = Gtk.Label('')
        self.buttonbox.pack_start(self.label, False, False, 20)

        # checked, name, artist, album, rid, artistid, albumid
        self.liststore_songs = Gtk.ListStore(bool, str, str, str, 
                int, int, int)
        control_box = Widgets.ControlBox(self.liststore_songs, app)
        self.buttonbox.pack_end(control_box, False, False, 0)

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

        self.scrolled_artists = Gtk.ScrolledWindow()
        self.scrolled_artists.get_vadjustment().connect('value-changed',
                self.on_scrolled_artists_scrolled)
        self.box_artists.pack_start(self.scrolled_artists, True, True, 0)

        # logo, name, nid, num of songs
        self.liststore_artists = Gtk.ListStore(GdkPixbuf.Pixbuf, str, int, 
                str)
        iconview_artists = Widgets.IconView(self.liststore_artists)
        iconview_artists.connect('item_activated', 
                self.on_iconview_artists_item_activated)
        self.scrolled_artists.add(iconview_artists)

        self.scrolled_songs = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_songs, True, True, 0)

        treeview_songs = Widgets.TreeViewSongs(self.liststore_songs, app)
        self.scrolled_songs.add(treeview_songs)

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

    def append_artists(self, init=False):
        if init:
            self.liststore_artists.clear()
            self.artists_page = 0
            self.scrolled_artists.get_vadjustment().set_value(0)
        selection = self.treeview_cate.get_selection()
        result = selection.get_selected()
        if result is None or len(result) != 2:
            return
        model, _iter = result
        pref_index = self.combo_pref.get_active()
        catid = model[_iter][1]
        prefix = self.liststore_pref[pref_index][1]
        artists, self.artists_total = Net.get_artists(catid, 
                self.artists_page, prefix)
        if self.artists_total == 0:
            return

        #self.artists_appended_timestamp = time.time()
        i = len(self.liststore_artists)
        for artist in artists:
            self.liststore_artists.append([self.app.theme['anonymous'],
                artist['name'], int(artist['id']), 
                artist['music_num']+'首歌曲', ])
            Net.update_artist_logo(self.liststore_artists, i, 0, 
                    artist['pic'])
            i += 1

    def on_iconview_artists_item_activated(self, iconview, path):
        model = iconview.get_model()
        self.label.set_label(model[path][1])
        self.curr_artist_name = model[path][1]
        self.append_songs(init=True)

    def append_songs(self, init=False):
        def _append_songs(songs_args, error=None):
            songs, self.songs_total = songs_args
            if self.songs_total == 0:
                return
            for song in songs:
                self.liststore_songs.append([True, song['SONGNAME'], 
                    song['ARTIST'], song['ALBUM'], 
                    int(song['MUSICRID'][6:]), int(song['ARTISTID']), 
                    int(song['ALBUMID']), ]) 
            # automatically load more songs
            self.songs_page += 1
            if self.songs_page < self.songs_total - 1:
                self.append_songs()

        if init:
            self.songs_page = 0
            self.box_artists.hide()
            self.buttonbox.show_all()
            self.scrolled_songs.show_all()
            self.liststore_songs.clear()
        Net.async_call(Net.get_artist_songs, _append_songs, 
                self.curr_artist_name, self.songs_page)

    # Song window
    def on_button_home_clicked(self, btn):
        self.box_artists.show_all()
        self.scrolled_songs.hide()
        self.buttonbox.hide()

    # scrolled windows
    def on_scrolled_artists_scrolled(self, adj):
        if Widgets.reach_scrolled_bottom(adj) and \
                self.artists_page < self.artists_total - 1:
            self.artists_page += 1
            self.append_artists()
