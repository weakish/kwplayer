
from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Cache

class Node(Gtk.Box):
    def __init__(self, app, nid):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_border_width(5)

        self.app = app
        self.nid = nid

        self.parent = Gtk.Window()
        self.parent.add(self)

    def init_nav(self):
        pass

    def init_side(self):
        print('Node.init_side()--')
        # name, nid
        self.liststore_side = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str)

        self.treeview_side = Gtk.IconView(self.liststore_side)
        self.treeview_side.set_pixbuf_column(0)
        self.treeview_side.set_text_column(1)

        self.scrolledwindow_side = Gtk.ScrolledWindow()
        self.scrolledwindow_side.add(self.treeview_side)
        self.scrolledwindow_side.props.hscrollbar_policy = Gtk.PolicyType.NEVER
        self.pack_start(self.scrolledwindow_side, False, False, 0)

    def get_side_nodes(self):
        nodes = Cache.Node(self.nid).get_nodes()
        print(nodes)

        self.liststore_side.clear()
        for node in nodes:
            self.liststore_side.append([self.app.theme['anonymous'], 
                node['disname'], node['sourceid']])

    def init_nodes(self):
        print('Node.init_nodes()--')
        # pixbuf, name, id
        self.liststore_nodes = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, str)
        self.treeview_nodes = Gtk.IconView(self.liststore_nodes)
        self.treeview_nodes.set_pixbuf_column(0)
        self.treeview_nodes.set_text_column(1)

        self.scrolledwindow_nodes = Gtk.ScrolledWindow()
        self.scrolledwindow_nodes.add(self.treeview_nodes)
        #self.scrolledwindow_nodes.props.visible = False
        self.scrolledwindow_nodes.hide()
        #self.pack_start(self.scrolledwindow_nodes, True, True, 0)

    def init_song_list(self):
        # checked, songname, artist, album, play_pix, add_pix,
        # download_pix, music_id
        self.liststore_songs = Gtk.ListStore(bool, str, str, str,
                GdkPixbuf.Pixbuf, GdkPixbuf.Pixbuf, GdkPixbuf.Pixbuf, 
                str)
        self.treeview_songs = Gtk.TreeView(self.liststore_songs)
        self.scrolledwindow_nodes = Gtk.ScrolledWindow()
        self.scrolledwindow_nodes.add(self.treeview_songs)
        self.scrolledwindow_nodes.hide()
        #self.pack_start(self.scrolledwindow_nodes, True, True, 0)

    def load(self):
        return
        print('Node.load()--')
        viewport_main = self.app.ui('scrolledwindow_main')
        children = viewport_main.get_children()
        if len(children) == 1:
            children[0].reparent(children[0].parent)

        self.show_all()
        self.reparent(viewport_main)


class TopList(Node):
    '''
    Top list node class.
    '''
    def __init__(self, app, nid):
        super().__init__(app, nid)

        self.init_side()
        self.init_nodes()
        self.init_song_list()

        #self.get_side_nodes()


class Artist(Node):
    def __init__(self, app):
        #super().__init__(self, app)
        pass

    def init_nodes(self):
        pass
