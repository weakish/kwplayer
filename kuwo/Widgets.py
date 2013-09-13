
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gtk


def song_row_to_dict(song_row):
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

def short_str(_str):
    if len(_str) > 10:
        return _str[:9] + '..'
    return _str



class IconView(Gtk.IconView):
    def __init__(self, liststore):
        super().__init__(model=liststore)

        self.set_pixbuf_column(0)
        cell_name = Gtk.CellRendererText()
        cell_name.set_alignment(0.5, 0.5)
        #cell_name.props.max_width_chars = 20
        self.pack_start(cell_name, True)
        self.add_attribute(cell_name, 'text', 1)

        cell_nums = Gtk.CellRendererText()
        fore_color = Gdk.RGBA(red=136/256, green=139/256, blue=132/256)
        cell_nums.props.foreground_rgba = fore_color
        cell_nums.props.size_points = 10
        cell_nums.set_alignment(0.5, 0.5)
        self.pack_start(cell_nums, True)
        self.add_attribute(cell_nums, 'text', 3)


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
        self.liststore[path][0] = not self.liststore_songs[path][0]

    def on_row_activated(self, treeview, path, column):
        print('on row activated')
        liststore = treeview.get_model()
        index = treeview.get_columns().index(column)
        song = song_row_to_dict(liststore[path])
        print('song:', song)

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
