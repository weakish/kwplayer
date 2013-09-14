
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gtk


def song_row_to_dict(song_row, start=1, withpath=True):
    song = {
            'name': song_row[start],
            'artist': song_row[start+1],
            'album': song_row[start+2],
            'rid': song_row[start+3],
            'artistid': song_row[start+4],
            'albumid': song_row[start+5],
            }
    if withpath:
        song['filepath'] = song_row[start+6]
    return song

def song_dict_to_row(song):
    # with filepath
    song_row = [song['name'], song['artist'], song['album'], song['rid'], 
            song['artistid'], song['albumid'], song['filepath']]
    return song_row

def short_str(_str):
    if len(_str) > 10:
        return _str[:9] + '..'
    return _str


class BoxControl(Gtk.Box):
    def __init__(self, liststore, app):
        super().__init__(spacing=5)
        self.liststore = liststore
        self.app = app

        button_selectall = Gtk.ToggleButton('Select All')
        button_selectall.set_active(True)
        button_selectall.connect('toggled', 
                self.on_button_selectall_toggled)
        self.pack_start(button_selectall, False, False, 0)

        button_play = Gtk.Button('Play')
        button_play.connect('clicked', self.on_button_play_clicked)
        self.pack_start(button_play, False, False, 0)

        button_add = Gtk.Button('Add to Playlist')
        button_add.connect('clicked', self.on_button_add_clicked)
        self.pack_start(button_add, False, False, 0)

        button_cache = Gtk.Button('Cache')
        button_cache.connect('clicked', self.on_button_cache_clicked)
        self.pack_start(button_cache, False, False, 0)

    def on_button_selectall_toggled(self, btn):
        toggled = btn.get_active()
        for song in self.liststore:
            song[0] = toggled

    def on_button_play_clicked(self, btn):
        songs = [song_row_to_dict(s, withpath=False) for s in self.liststore if s[0]]
        self.app.playlist.play_songs(songs)

    def on_button_add_clicked(self, btn):
        songs = [song_row_to_dict(s, withpath=False) for s in self.liststore if s[0]]
        self.app.playlist.add_songs_to_playlist(songs)

    def on_button_cache_clicked(self, btn):
        songs = [song_row_to_dict(s, withpath=False) for s in self.liststore if s[0]]
        self.app.playlist.cache_songs(songs)


class IconView(Gtk.IconView):
    def __init__(self, liststore):
        super().__init__(model=liststore)

        self.set_pixbuf_column(0)
        cell_name = Gtk.CellRendererText()
        cell_name.set_alignment(0.5, 0.5)
        #cell_name.props.max_width_chars = 20
        self.pack_start(cell_name, True)
        self.add_attribute(cell_name, 'text', 1)

        cell_info = Gtk.CellRendererText()
        fore_color = Gdk.RGBA(red=136/256, green=139/256, blue=132/256)
        cell_info.props.foreground_rgba = fore_color
        cell_info.props.size_points = 9
        cell_info.set_alignment(0.5, 0.5)
        self.pack_start(cell_info, True)
        self.add_attribute(cell_info, 'text', 3)


class TreeViewSongs(Gtk.TreeView):
    def __init__(self, liststore, app):
        super().__init__(model=liststore)
        self.set_headers_visible(False)
        self.liststore = liststore
        self.app = app

        checked = Gtk.CellRendererToggle()
        checked.connect('toggled', self.on_song_checked)
        column_check = Gtk.TreeViewColumn('Checked', checked, active=0)
        self.append_column(column_check)

        name = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn('Name', name, text=1)
        col_name.props.sizing = Gtk.TreeViewColumnSizing.AUTOSIZE
        col_name.props.expand = True
        self.append_column(col_name)

        artist = Gtk.CellRendererText()
        col_artist = Gtk.TreeViewColumn('Artist', artist, text=2)
        col_artist.props.sizing = Gtk.TreeViewColumnSizing.AUTOSIZE
        col_artist.props.expand = True
        self.append_column(col_artist)

        album = Gtk.CellRendererText()
        col_album = Gtk.TreeViewColumn('Album', album, text=3)
        col_album.props.sizing = Gtk.TreeViewColumnSizing.AUTOSIZE
        col_album.props.expand = True
        self.append_column(col_album)

        play = Gtk.CellRendererPixbuf(pixbuf=app.theme['play'])
        col_play = Gtk.TreeViewColumn('Play', play)
        col_play.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        col_play.props.fixed_width = 20
        self.append_column(col_play)

        add = Gtk.CellRendererPixbuf(pixbuf=app.theme['add'])
        col_add = Gtk.TreeViewColumn('Add', add)
        col_add.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        col_add.props.fixed_width = 20
        self.append_column(col_add)

        cache = Gtk.CellRendererPixbuf(pixbuf=app.theme['cache'])
        col_cache = Gtk.TreeViewColumn('Cache', cache)
        col_cache.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        col_cache.props.fixed_width = 20
        self.append_column(col_cache)

        self.connect('row_activated', self.on_row_activated)

    def on_song_checked(self, widget, path):
        self.liststore[path][0] = not self.liststore[path][0]

    def on_row_activated(self, treeview, path, column):
        print('on row activated')
        model = treeview.get_model()
        index = treeview.get_columns().index(column)
        song = song_row_to_dict(model[path], withpath=False)
        print('song:', song)
        print('index:', index)
        print('mode[path]:', model[path])

        if index in (1, 4):
            # level 1
            print('will play song')
            self.app.playlist.play_song(song)
        elif index == 2:
            print('will search artist')
        elif index == 3:
            print('will search album')
        elif index == 5:
            print('will append song')
            self.app.playlist.add_song_to_playlist(song)
        elif index == 6:
            print('will cache song')
            self.app.playlist.cache_song(song)
