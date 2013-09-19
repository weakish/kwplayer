

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gtk
import html

from kuwo import Widgets
from kuwo import Net

class Search(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.app = app
        self.first_show = False

        self.songs_tab_inited = False
        self.artists_tab_inited = False
        self.albums_tab_inited = False

        box_top = Gtk.Box(spacing=5)
        self.pack_start(box_top, False, False, 0)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text('Search Songs, Artists..')
        #self.search_entry.props.margin_right = 20
        self.search_entry.props.width_chars = 30
        self.search_entry.connect('activate', self.on_search_entry_activate)
        box_top.pack_start(self.search_entry, False, False, 20)

        self.songs_button = Widgets.ListRadioButton('Songs')
        self.songs_button.connect('toggled', self.switch_notebook_page, 0)
        box_top.pack_start(self.songs_button, False, False, 0)

        self.artists_button = Widgets.ListRadioButton('Artists', 
                self.songs_button)
        self.artists_button.connect('toggled', self.switch_notebook_page, 1)
        box_top.pack_start(self.artists_button, False, False, 0)

        self.albums_button = Widgets.ListRadioButton('Albums', 
                self.songs_button)
        self.albums_button.connect('toggled', self.switch_notebook_page, 2)
        box_top.pack_start(self.albums_button, False, False, 0)

        # TODO: add MV and lyrics search.

        # checked, name, artist, album, rid, artistid, albumid
        self.liststore_songs = Gtk.ListStore(bool, str, str, str, int, int,
                int)
        self.control_box = Widgets.ControlBox(self.liststore_songs, app)
        #control_box.props.halign = Gtk.Align.END
        box_top.pack_end(self.control_box, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.set_show_tabs(False)
        self.pack_start(self.notebook, True, True, 0)

        songs_tab = Gtk.ScrolledWindow()
        self.notebook.append_page(songs_tab, Gtk.Label('Songs'))
        treeview_songs = Widgets.TreeViewSongs(self.liststore_songs, app)
        songs_tab.add(treeview_songs)

        artists_tab = Gtk.ScrolledWindow()
        self.notebook.append_page(artists_tab, Gtk.Label('Artists'))

        # pic, artist, artistid
        self.liststore_artists = Gtk.ListStore(GdkPixbuf.Pixbuf,
                str, int)
        iconview_artists = Widgets.IconView(self.liststore_artists)
        artists_tab.add(iconview_artists)

        albums_tab = Gtk.ScrolledWindow()
        self.notebook.append_page(albums_tab, Gtk.Label('Albums'))

        # logo, album, albumid, artist, artistid, info
        self.liststore_albums = Gtk.ListStore(GdkPixbuf.Pixbuf, str, int,
                str, int, str)
        iconview_albums = Widgets.IconView(self.liststore_albums)
        iconview_albums.set_tooltip_column(5)
        albums_tab.add(iconview_albums)

    def after_init(self):
        pass

    def first(self):
        if self.first_show:
            return
        self.first_show = True

    def switch_notebook_page(self, radiobtn, page):
        self.notebook.set_current_page(page)
        if page == 0 and not self.songs_tab_inited:
            self.control_box.show_all()
            self.on_search_entry_activate()
        elif page == 1 and not self.artists_tab_inited:
            self.control_box.hide()
            self.on_search_entry_activate()
        elif page == 2 and not self.albums_tab_inited:
            self.control_box.hide()
            self.on_search_entry_activate()

    def on_search_entry_activate(self, search_entry=None):
        print('on search entry activate()')
        keyword = self.search_entry.get_text()
        if len(keyword) == 0:
            return
        page = self.notebook.get_current_page()
        if page == 0:
            songs_wrap = Net.search_songs(keyword)
            self.liststore_songs.clear()
            if not songs_wrap:
                print('songs wrap is empty')
                return
            self.songs_button.set_label('Songs ({0})'.format(
                songs_wrap['HIT']))
            songs = songs_wrap['abslist']
            for song in songs:
                self.liststore_songs.append([self.app.theme['anonymous'],
                    song['SONGNAME'], song['ARTIST'], song['ALBUM'],
                    int(song['MUSICRID'][6:]), int(song['ARTISTID']),
                    int(song['ALBUMID']), ])
        elif page == 1:
            artists_wrap = Net.search_artists(keyword)
            self.liststore_artists.clear()
            if not artists_wrap:
                return
            self.artists_button.set_label('Artists ({0})'.format(
                artists_wrap['HIT']))
            artists = artists_wrap['abslist']
            i = 0
            for artist in artists:
                self.liststore_artists.append([self.app.theme['anonymous'],
                    artist['ARTIST'], int(artist['ARTISTID']), ])
                if len(artist['PICPATH']) > 0:
                    Net.update_artist_logo(self.liststore_artists, i, 0,
                            artist['PICPATH'])
                i += 1
        elif page == 2:
            albums_wrap = Net.search_albums(keyword)
            self.liststore_albums.clear()
            if not albums_wrap:
                print('albums is None, return')
                return
            self.albums_button.set_label('Albums ({0})'.format(
                albums_wrap['total']))
            albums = albums_wrap['albumlist']
            i = 0
            for album in albums:
                self.liststore_albums.append([self.app.theme['anonymous'],
                    Widgets.short_str(album['name'], 20), 
                    int(album['albumid']), 
                    Widgets.short_str(album['artist'], 20),
                    int(album['artistid']),
                    Widgets.tooltip(album['info']), ])
                Net.update_album_covers(self.liststore_albums, i, 0,
                        album['pic'])
                i += 1
