
from gi.repository import GdkPixbuf
from gi.repository import Gtk
import time

from kuwo import Net
from kuwo import Widgets

class ArtistButton(Gtk.RadioButton):
    def __init__(self, parent, label, group, tab_index):
        super().__init__(label=label)
        self.props.draw_indicator = False
        if group is not None:
            self.join_group(group)
        self.tab = tab_index
        self.parent = parent
        parent.artist_buttons.pack_start(self, False, False, 0)
        self.connect('toggled', self.on_toggled)

    def on_toggled(self, btn):
        state = self.get_active()
        if not state:
            return
        self.parent.artist_notebook.set_current_page(self.tab)
        methods = [
                self.parent.show_artist_songs,
                self.parent.show_artist_albums,
                self.parent.show_artist_mv,
                self.parent.show_artist_similar,
                self.parent.show_artist_info,
                ]
        methods[self.tab]()


class Artists(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.first_show = False

        self.buttonbox = Gtk.Box()
        self.pack_start(self.buttonbox, False, False, 0)

        home_button = Gtk.Button('Artists')
        home_button.connect('clicked', self.on_home_button_clicked)
        self.buttonbox.pack_start(home_button, False, False, 0)
        self.artist_button = Gtk.Button('')
        self.artist_button.connect('clicked', self.on_artist_button_clicked)
        self.buttonbox.pack_start(self.artist_button, False, False, 0)
        # to show artist name or album name
        self.label = Gtk.Label('')
        self.buttonbox.pack_start(self.label, False, False, 20)

        # control_box for artist's songs
        # checked, name, artist, album, rid, artistid, albumid
        self.artist_songs_liststore = Gtk.ListStore(bool, str, str, str, 
                int, int, int)
        self.artist_control_box = Widgets.ControlBox(
                self.artist_songs_liststore, app)
        self.buttonbox.pack_end(self.artist_control_box, False, False, 0)

        # control box for artist's albums
        # checked, name, artist, album, rid, artistid, albumid
        self.album_songs_liststore = Gtk.ListStore(bool, str, str, str,
                int, int, int)
        self.album_control_box = Widgets.ControlBox(
                self.album_songs_liststore, app)
        self.buttonbox.pack_end(self.album_control_box, False, False, 0)

        # main notebook
        self.notebook = Gtk.Notebook()
        self.notebook.set_show_tabs(False)
        self.pack_start(self.notebook, True, True, 0)

        # Artists tab (tab 0)
        self.artists_tab = Gtk.Box()
        self.notebook.append_page(self.artists_tab, Gtk.Label('Artists'))
        #self.pack_start(self.box_artists, True, True, 0)

        # left panel of artists tab
        artists_left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.artists_tab.pack_start(artists_left_box, False, False, 0)
        # artists categories
        # name, id
        self.cate_liststore = Gtk.ListStore(str, int)
        self.cate_treeview = Gtk.TreeView(model=self.cate_liststore)
        self.cate_treeview.props.headers_visible = False
        name = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn('Name', name, text=0)
        self.cate_treeview.append_column(col_name)
        artists_left_box.pack_start(self.cate_treeview, False, False, 0)

        # artists prefix
        # disname, prefix
        self.pref_liststore = Gtk.ListStore(str, str)
        self.pref_combo = Gtk.ComboBox(model=self.pref_liststore)
        cell_name = Gtk.CellRendererText()
        self.pref_combo.pack_start(cell_name, True)
        self.pref_combo.add_attribute(cell_name, 'text', 0)
        self.pref_combo.props.margin_top = 15
        artists_left_box.pack_start(self.pref_combo, False, False, 0)

        # main window of artists
        self.artists_win = Gtk.ScrolledWindow()
        self.artists_win.get_vadjustment().connect('value-changed',
                self.on_artists_win_scrolled)
        self.artists_tab.pack_start(self.artists_win, True, True, 0)
        # pic, artist name, artist id, num of songs
        self.artists_liststore = Gtk.ListStore(GdkPixbuf.Pixbuf, str, int, 
                str)
        artists_iconview = Widgets.IconView(self.artists_liststore)
        artists_iconview.connect('item_activated', 
                self.on_artists_iconview_item_activated)
        self.artists_win.add(artists_iconview)

        # Artist tab (tab 1)
        self.artist_tab = Gtk.Box()
        self.notebook.append_page(self.artist_tab, Gtk.Label('Artist'))

        # left panel of artist
        self.artist_buttons = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.artist_tab.pack_start(self.artist_buttons, False, False, 0)

        self.artist_songs_button = ArtistButton(self, 'Songs', None, 0)
        self.artist_albums_button = ArtistButton(self, 'Albums',
                self.artist_songs_button, 1)
        self.artist_mv_button = ArtistButton(self, 'MV',
                self.artist_songs_button, 2)
        self.artist_similar_button = ArtistButton(self, 'Similar',
                self.artist_songs_button, 3)
        self.artist_info_button = ArtistButton(self, 'Info',
                self.artist_songs_button, 4)

        # main window of artist tab
        self.artist_notebook = Gtk.Notebook()
        self.artist_notebook.set_show_tabs(False)
        self.artist_tab.pack_start(self.artist_notebook, True, True, 0)

        # songs tab for artist (tab 0)
        self.artist_songs_tab = Gtk.ScrolledWindow()
        self.artist_notebook.append_page(self.artist_songs_tab, 
                Gtk.Label('Songs'))
        artist_songs_treeview = Widgets.TreeViewSongs(
                self.artist_songs_liststore, app)
        self.artist_songs_tab.add(artist_songs_treeview)


        # albums tab for artist (tab 1)
        self.artist_albums_tab = Gtk.ScrolledWindow()
        self.artist_notebook.append_page(self.artist_albums_tab,
                Gtk.Label('Albums'))
        # pic, album, albumid, artist, artistid, info
        self.artist_albums_liststore = Gtk.ListStore(GdkPixbuf.Pixbuf, 
                str, int, str, int, str)
        artist_albums_iconview = Widgets.IconView(
                self.artist_albums_liststore, tooltip=5)
        artist_albums_iconview.connect('item_activated',
                self.on_artist_albums_iconview_item_activated)
        self.artist_albums_tab.add(artist_albums_iconview)

        # MVs tab for artist (tab 2)
        self.artist_mv_tab = Gtk.ScrolledWindow()
        self.artist_notebook.append_page(self.artist_mv_tab, 
                Gtk.Label('MV'))
        # pic, name, artist, album, rid, artistid, albumid
        self.artist_mv_liststore = Gtk.ListStore(GdkPixbuf.Pixbuf, str, 
                str, str, int, int, int)
        artist_mv_iconview = Widgets.IconView(self.artist_mv_liststore,
                info_pos=2)
        artist_mv_iconview.connect('item_activated',
                self.on_artist_mv_iconview_item_activated)
        self.artist_mv_tab.add(artist_mv_iconview)

        # Similar tab for artist (tab 3)
        self.artist_similar_tab = Gtk.ScrolledWindow()
        self.artist_notebook.append_page(self.artist_similar_tab, 
                Gtk.Label('Similar'))
        # pic, artist name, artist id, num of songs
        self.artist_similar_liststore = Gtk.ListStore(GdkPixbuf.Pixbuf,
                str, int, str)
        artist_similar_iconview = Widgets.IconView(
                self.artist_similar_liststore, info_pos=3)
        artist_similar_iconview.connect('item_activated',
                self.on_artist_similar_iconview_item_activated)
        self.artist_similar_tab.add(artist_similar_iconview)

        # Info tab for artist (tab 4)
        artist_info_tab = Gtk.ScrolledWindow()
        self.artist_notebook.append_page(artist_info_tab,
                Gtk.Label('Info'))
        self.artist_info_textbuffer = Gtk.TextBuffer()
        artist_info_textview = Gtk.TextView()
        artist_info_textview.props.editable = False
        artist_info_textview.set_buffer(self.artist_info_textbuffer)
        artist_info_tab.add(artist_info_textview)


        # Album tab (tab 2)
        album_songs_tab = Gtk.ScrolledWindow()
        self.notebook.append_page(album_songs_tab, Gtk.Label('Album'))
        album_songs_treeview = Widgets.TreeViewSongs(
                self.album_songs_liststore, app)
        album_songs_tab.add(album_songs_treeview)

    def after_init(self):
        self.buttonbox.hide()

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
            self.pref_liststore.append(pref)
        self.pref_combo.set_active(0)
        self.pref_combo.connect('changed', self.on_cate_changed)

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
            self.cate_liststore.append(cate)
        selection = self.cate_treeview.get_selection()
        self.cate_treeview.connect('row_activated', self.on_cate_changed)
        selection.connect('changed', self.on_cate_changed)
        selection.select_path(0)

    def on_cate_changed(self, *args):
        self.append_artists(init=True)

    def append_artists(self, init=False):
        if init:
            self.artists_liststore.clear()
            self.artists_page = 0
            self.artists_win.get_vadjustment().set_value(0)
        selection = self.cate_treeview.get_selection()
        result = selection.get_selected()
        if result is None or len(result) != 2:
            return
        model, _iter = result
        pref_index = self.pref_combo.get_active()
        catid = model[_iter][1]
        prefix = self.pref_liststore[pref_index][1]
        # TODO: use async_call()
        artists, self.artists_total = Net.get_artists(catid, 
                self.artists_page, prefix)
        if self.artists_total == 0:
            return

        i = len(self.artists_liststore)
        for artist in artists:
            self.artists_liststore.append([self.app.theme['anonymous'],
                artist['name'], int(artist['id']), 
                artist['music_num']+'首歌曲', ])
            Net.update_artist_logo(self.artists_liststore, i, 0, 
                    artist['pic'])
            i += 1

    def on_artists_iconview_item_activated(self, iconview, path):
        model = iconview.get_model()
        artist = model[path][1]
        artistid = model[path][2]
        self.show_artist(artist, artistid)

    # Song window
    def on_home_button_clicked(self, btn):
        self.buttonbox.hide()
        self.notebook.set_current_page(0)

    # scrolled windows
    def on_artists_win_scrolled(self, adj):
        if Widgets.reach_scrolled_bottom(adj) and \
                self.artists_page < self.artists_total - 1:
            self.artists_page += 1
            self.append_artists()


    # open API other tabs can use.
    def show_artist(self, artist, artistid):
        self.curr_artist_name = artist
        self.curr_artist_id = artistid
        self.notebook.set_current_page(1)
        self.artist_songs_inited = False
        self.artist_albums_inited = False
        self.artist_mv_inited = False
        self.artist_similar_inited = False
        self.artist_info_inited = False

        self.buttonbox.show_all()
        self.artist_button.hide()
        self.album_control_box.hide()
        self.label.set_label(artist)
        # switch to `songs` tab
        if self.artist_songs_button.get_active():
            self.show_artist_songs()
        else:
            self.artist_songs_button.set_active(True)

    def show_artist_songs(self):
        if self.artist_songs_inited:
            return
        self.artist_songs_inited = True
        self.artist_control_box.show_all()
        self.append_artist_songs(init=True)

    def append_artist_songs(self, init=False):
        def _append_artist_songs(songs_args, error=None):
            songs, self.artist_songs_total = songs_args
            if self.artist_songs_total == 0:
                return
            for song in songs:
                self.artist_songs_liststore.append([True, song['name'], 
                    song['artist'], song['album'], 
                    int(song['musicrid']), int(song['artistid']), 
                    int(song['albumid']), ]) 
            # automatically load more songs
            self.artist_songs_page += 1
            if self.artist_songs_page < self.artist_songs_total - 1:
                self.append_artist_songs()

        if init:
            self.artist_songs_liststore.clear()
            self.artist_songs_page = 0
        Net.async_call(Net.get_artist_songs_by_id, _append_artist_songs, 
                self.curr_artist_id, self.artist_songs_page)

    def show_artist_albums(self):
        if self.artist_albums_inited:
            return
        self.artist_albums_inited = True
        self.artist_control_box.hide()
        self.append_artist_albums(init=True)

    def append_artist_albums(self, init=False):
        def _append_artist_albums(albums_args, error=None):
            albums, self.artist_albums_total = albums_args
            if self.artist_albums_total == 0:
                return
            i = len(self.artist_albums_liststore)
            for album in albums:
                if len(album['info']) == 0:
                    tooltip = Widgets.tooltip(album['name'])
                else:
                    tooltip = '<b>{0}</b>\n{1}'.format(
                            Widgets.tooltip(album['name']),
                            Widgets.tooltip(album['info']))
                self.artist_albums_liststore.append([
                    self.app.theme['anonymous'], album['name'],
                    int(album['albumid']), album['artist'],
                    int(album['artistid']), tooltip, ])
                Net.update_album_covers(self.artist_albums_liststore, i,
                        0, album['pic'])
                i += 1
            self.artist_albums_page += 1
            if self.artist_albums_page < self.artist_albums_total - 1:
                self.append_artist_albums()

        if init:
            self.artist_albums_liststore.clear()
            self.artist_albums_page = 0
        Net.async_call(Net.get_artist_albums, _append_artist_albums,
                self.curr_artist_id, self.artist_albums_page)

    def show_artist_mv(self):
        if self.artist_mv_inited:
            return
        self.artist_mv_inited = True
        self.artist_control_box.hide()
        self.append_artist_mv(init=True)

    def append_artist_mv(self, init=False):
        def _append_artist_mv(mv_args, error=None):
            mvs, self.artist_mv_total = mv_args
            if self.artist_mv_total == 0:
                return
            i = len(self.artist_mv_liststore)
            for mv in mvs:
                self.artist_mv_liststore.append([
                    self.app.theme['anonymous'], mv['name'], mv['artist'],
                    '', int(mv['musicid']), int(mv['artistid']), 0, ])
                Net.update_mv_image(self.artist_mv_liststore, i, 0,
                        mv['pic'])
                i += 1
            self.artist_mv_page += 1
            if self.artist_mv_page < self.artist_mv_total - 1:
                self.append_artist_mv()

        if init:
            self.artist_mv_liststore.clear()
            self.artist_mv_page = 0
        Net.async_call(Net.get_artist_mv, _append_artist_mv,
                self.curr_artist_id, self.artist_mv_page)

    def show_artist_similar(self):
        if self.artist_similar_inited:
            return
        self.artist_similar_inited = True
        self.artist_control_box.hide()
        self.append_artist_similar(init=True)

    def append_artist_similar(self, init=False):
        def _append_artist_similar(similar_args, error=None):
            print('_append_artist_similar:', similar_args, error)
            artists, self.artist_similar_total = similar_args
            if self.artist_similar_total == 0:
                return
            i = len(self.artist_similar_liststore)
            for artist in artists:
                self.artist_similar_liststore.append([
                    self.app.theme['anonymous'], artist['name'],
                    int(artist['id']), artist['songnum'] + '首歌曲', ])
                Net.update_artist_logo(self.artist_similar_liststore, i,
                        0, artist['pic'])
                i += 1
            self.artist_similar_page += 1
            if self.artist_similar_page < self.artist_similar_total - 1:
                self.append_artist_similar()

        if init:
            self.artist_similar_liststore.clear()
            self.artist_similar_page = 0
        Net.async_call(Net.get_artist_similar, _append_artist_similar,
                self.curr_artist_id, self.artist_similar_page)

    def show_artist_info(self):
        if self.artist_info_inited:
            return
        self.artist_info_inited = True
        self.artist_control_box.hide()
        self.append_artist_info()

    def append_artist_info(self):
        def _append_artist_info(info, error=None):
            if info is None:
                return
            # TODO, FIXME
            self.artist_info_textbuffer.set_text(info['info'])

        Net.async_call(Net.get_artist_info, _append_artist_info,
                self.curr_artist_id)


    def on_artist_albums_iconview_item_activated(self, iconview, path):
        model = iconview.get_model()
        album = model[path][1]
        albumid = model[path][2]
        artist = model[path][3]
        artistid = model[path][4]
        self.show_album(album, albumid, artist, artistid)

    def on_artist_mv_iconview_item_activated(self, iconview, path):
        model = iconview.get_model()
        song = Widgets.song_row_to_dict(model[path])
        self.app.popup_page(self.app.lrc.app_page)
        self.app.player.load_mv(song)

    def on_artist_similar_iconview_item_activated(self, iconview, path):
        model = iconview.get_model()
        artist = model[path][1]
        artistid = model[path][2]
        self.show_artist(artist, artistid)

    # open API
    def show_album(self, album, albumid, artist, artistid):
        self.curr_album_name = album
        self.curr_album_id = albumid
        self.curr_artist_name = artist
        self.curr_artist_id = artistid
        self.artist_button.set_label(artist)
        self.label.set_label(album)
        self.buttonbox.show_all()
        self.artist_control_box.hide()
        self.notebook.set_current_page(2)
        self.append_album_songs()
    
    def append_album_songs(self):
        def _append_album_songs(songs, error=None):
            if songs is None:
                return
            for song in songs:
                self.album_songs_liststore.append([True, song['name'],
                    song['artist'], self.curr_album_name,
                    int(song['id']), int(song['artistid']),
                    int(self.curr_album_id), ])
        self.album_songs_liststore.clear()
        Net.async_call(Net.get_album, _append_album_songs,
                self.curr_album_id)

    def on_artist_button_clicked(self, button):
        self.show_artist(self.curr_artist_name, self.curr_artist_id)
