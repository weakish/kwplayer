
from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Net
from kuwo import Widgets

NID = 2

class TopList(Gtk.Box):
    def __init__(self, app):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.app = app
        self.first_show = False

        self.buttonbox = Gtk.Box(spacing=8)
        self.pack_start(self.buttonbox, False, False, 0)

        button_home = Gtk.Button('TopList')
        button_home.connect('clicked', self.on_button_home_clicked)
        #button_home.props.relief = Gtk.ReliefStyle.NONE
        self.buttonbox.pack_start(button_home, False, False, 0)

        self.label = Gtk.Label('')
        self.buttonbox.pack_start(self.label, False, False, 20)

        #TODO: reset these button to local variable.
        button_cache = Gtk.Button('Cache')
        button_cache.connect('clicked', self.on_button_cache_clicked)
        self.buttonbox.pack_end(button_cache, False, False, 0)

        self.button_add = Gtk.Button('Add to playlist')
        self.buttonbox.pack_end(self.button_add, False, False, 0)

        self.button_play = Gtk.Button('Play')
        self.buttonbox.pack_end(self.button_play, False, False, 0)

        self.button_selectall = Gtk.ToggleButton('Select All')
        self.button_selectall.set_active(True)
        self.button_selectall.connect('toggled', self.on_button_selectall_toggled)
        self.buttonbox.pack_end(self.button_selectall, False, False, 0)


        self.scrolled_nodes = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_nodes, True, True, 0)

        # logo, name, nid
        # TODO: use Widgets.IconView
        self.liststore_nodes = Gtk.ListStore(GdkPixbuf.Pixbuf, str, int)
        iconview_nodes = Gtk.IconView(model=self.liststore_nodes)
        iconview_nodes.set_pixbuf_column(0)
        iconview_nodes.set_text_column(1)
        iconview_nodes.set_item_width(95)
        iconview_nodes.connect('item_activated', 
                self.on_iconview_nodes_item_activated)
        self.scrolled_nodes.add(iconview_nodes)

        self.scrolled_songs = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_songs, True, True, 0)

        # checked, name, artist, album, rid, artistid, albumid
        self.liststore_songs = Gtk.ListStore(bool, str, str, str, int, int,
                int, GdkPixbuf.Pixbuf, GdkPixbuf.Pixbuf, GdkPixbuf.Pixbuf)
        treeview_songs = Widgets.TreeViewSongs(self.liststore_songs, app)

    def after_init(self):
        self.buttonbox.hide()
        self.scrolled_songs.hide()

    def first(self):
        if self.first_show:
            return
        self.first_show = True

        nodes = Net.get_nodes(NID)

        i = 0
        for node in nodes:
            self.liststore_nodes.append([self.app.theme['anonymous'],
                node['name'], int(node['sourceid']), ])
            Net.update_toplist_node_logo(self.liststore_nodes, i, 0, 
                    node['pic'])
            i += 1

    def on_button_home_clicked(self, btn):
        self.scrolled_nodes.show_all()
        self.scrolled_songs.hide()
        self.buttonbox.hide()

    def on_button_selectall_toggled(self, btn):
        toggled = btn.get_active()
        for song in self.liststore_songs:
            song[0] = toggled

    def on_iconview_nodes_item_activated(self, iconview, path):
        model = iconview.get_model()
        self.buttonbox.show_all()
        self.label.set_label(model[path][1])
        self.show_toplist_songs(model[path][2])

    def on_song_checked(self, widget, path):
        self.liststore_songs[path][0] = not self.liststore_songs[path][0]

    def show_toplist_songs(self, nid):
        self.scrolled_nodes.hide()
        self.scrolled_songs.show_all()

        songs = Net.get_toplist_songs(nid)
        self.liststore_songs.clear()
        for song in songs:
            self.liststore_songs.append([True, song['name'], 
                song['artist'], song['album'], int(song['id']), 
                int(song['artistid']), int(song['albumid']), 
                self.app.theme['play'], self.app.theme['add'],
                self.app.theme['cache'], ])

    def on_treeview_songs_row_activated(self, treeview, path, column):
        liststore = treeview.get_model()
        index = treeview.get_columns().index(column)
        song = self.song_modelrow_to_dict(liststore[path])

        if index in (1, 4):
            # level 1
            self.app.player.load(song)
        elif index == 2:
            print('will search artist')
        elif index == 3:
            print('will search album')
        elif index == 5:
            # level 2
            print('will append song')
            self.app.playlist.append_song(song)
        elif index == 6:
            # level 3
            self.app.playlist.cache_song(song)


    def on_button_cache_clicked(self, btn):
        print('on button cache clicked')
        songs = [self.song_modelrow_to_dict(song) for song in self.liststore_songs if song[0]]
        self.app.playlist.cache_songs(songs)

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
