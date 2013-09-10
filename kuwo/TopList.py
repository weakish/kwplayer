
from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Net

NID = 2

class TopList(Gtk.Box):
    def __init__(self, app):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.app = app

        self.buttonbox = Gtk.Box()
        self.pack_start(self.buttonbox, False, False, 0)

        home_btn = Gtk.Button('热播榜')
        home_btn.connect('clicked', self.on_home_btn_clicked)
        home_btn.props.relief = Gtk.ReliefStyle.NONE
        self.buttonbox.pack_start(home_btn, False, False, 0)

        self.label = Gtk.Label('')
        self.buttonbox.pack_start(self.label, False, False, 20)

        self.scrolled_nodes = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_nodes, True, True, 0)

        iconview_nodes = Gtk.IconView()
        # logo, name, nid
        self.liststore_nodes = Gtk.ListStore(GdkPixbuf.Pixbuf, str, int)
        iconview_nodes.set_model(self.liststore_nodes)
        iconview_nodes.set_pixbuf_column(0)
        iconview_nodes.set_text_column(1)
        iconview_nodes.set_item_width(95)
        iconview_nodes.connect('item_activated', 
                self.on_iconview_nodes_item_activated)
        self.scrolled_nodes.add(iconview_nodes)

        self.scrolled_songs = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_songs, True, True, 0)

        treeview_songs = Gtk.TreeView()
        # checked, name, artist, album, rid, artistid, albumid
        self.liststore_songs = Gtk.ListStore(bool, str, str, str, int, int,
                int)
        treeview_songs.set_model(self.liststore_songs)
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
        #col_name.props.min_width = 100
        #col_name.props.max_width = 520
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

        play = Gtk.CellRendererPixbuf(pixbuf=self.app.theme['play'])
        col_play = Gtk.TreeViewColumn('Play', play)
        col_play.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        col_play.props.fixed_width = 20
        treeview_songs.append_column(col_play)

        add = Gtk.CellRendererPixbuf(pixbuf=self.app.theme['add'])
        col_add = Gtk.TreeViewColumn('Add', add)
        col_add.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        col_add.props.fixed_width = 20
        treeview_songs.append_column(col_add)

        cache = Gtk.CellRendererPixbuf(pixbuf=self.app.theme['cache'])
        col_cache = Gtk.TreeViewColumn('Cache', cache)
        col_cache.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        col_cache.props.fixed_width = 20
        treeview_songs.append_column(col_cache)

        self.first_show = False

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

    def on_home_btn_clicked(self, btn):
        self.scrolled_nodes.show_all()
        self.scrolled_songs.hide()
        self.buttonbox.hide()

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
                int(song['artistid']), int(song['albumid']), ])

    def on_treeview_songs_row_activated(self, treeview, path, column):
        liststore = treeview.get_model()
        index = treeview.get_columns().index(column)
        song = {
                'name': liststore[path][1],
                'artist': liststore[path][2],
                'album': liststore[path][3],
                'rid': liststore[path][4],
                'artistid': liststore[path][5],
                'albumid': liststore[path][6],
                }

        if index in (1, 7):
            # level 1
            self.app.player.load(song)
        elif index == 2:
            print('will search artist')
        elif index == 3:
            print('will search album')
        elif index == 8:
            # level 2
            self.app.playlist.append(song)
        elif index == 9:
            # level 3
            self.app.playlist.cache(song)
