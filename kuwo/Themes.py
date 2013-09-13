
from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Net
from kuwo import Widgets


class Themes(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.first_show = False

        self.buttonbox = Gtk.Box()
        self.pack_start(self.buttonbox, False, False, 0)

        self.button_main = Gtk.Button('心情主题')
        self.button_main.connect('clicked', self.on_button_main_clicked)
        self.buttonbox.pack_start(self.button_main, False, False, 0)

        self.button_sub = Gtk.Button('')
        self.button_sub.connect('clicked', self.on_button_sub_clicked)
        self.buttonbox.pack_start(self.button_sub, False, False, 0)

        self.label = Gtk.Label('')
        self.buttonbox.pack_start(self.label, False, False, 0)

        self.scrolled_main = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_main, True, True, 0)
        
        # pic, name, id, num of lists
        self.liststore_main = Gtk.ListStore(GdkPixbuf.Pixbuf, str, int, str)
        iconview_main = Widgets.IconView(self.liststore_main)
        iconview_main.connect('item_activated', 
                self.on_iconview_main_item_activated)
        self.scrolled_main.add(iconview_main)

        self.scrolled_sub = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_sub, True, True, 0)

        # pic, name, sourceid, num of lists
        self.liststore_sub = Gtk.ListStore(GdkPixbuf.Pixbuf, str, int, str)
        iconview_sub = Widgets.IconView(self.liststore_sub)
        iconview_sub.connect('item_activated', 
                self.on_iconview_sub_item_activated)
        self.scrolled_sub.add(iconview_sub)

        self.box_songs = Gtk.Box()
        self.pack_start(self.box_songs, True, True, 0)

        self.scrolled_songs = Gtk.ScrolledWindow()
        self.box_songs.pack_start(self.scrolled_songs, True, True, 0)

        # checked, name, artist, album, rid, artistid, albumid
        self.liststore_songs = Gtk.ListStore(bool, str, str, str, 
                int, int, int)
        treeview_songs = Widgets.TreeViewSongs(self.liststore_songs,
                self.app)
        self.scrolled_songs.add(treeview_songs)

    def after_init(self):
        self.buttonbox.hide()
        self.scrolled_sub.hide()
        self.box_songs.hide()

    def first(self):
        if self.first_show:
            return
        self.first_show = True

        nodes = Net.get_themes_main()
        if nodes is None:
            print('Failed to get nodes, do something!')
            return
        i = 0
        for node in nodes:
            self.liststore_main.append([self.app.theme['anonymous'],
                    Widgets.short_str(node['name']), node['nid'], 
                    node['info'], ])
            Net.update_liststore_image(self.liststore_main, i, 0, 
                    node['pic'])
            i += 1

    def on_iconview_main_item_activated(self, iconview, path):
        model = iconview.get_model()
        self.curr_sub_name = model[path][1]
        self.curr_sub_id = model[path][2]
        self.label.set_label(self.curr_sub_name)
        #self.curr_sub_page = 0
        self.show_sub()

    def show_sub(self):
        self.scrolled_main.hide()
        self.box_songs.hide()
        self.buttonbox.show_all()
        self.button_sub.hide()
        self.scrolled_sub.get_vadjustment().set_value(0)
        self.scrolled_sub.show_all()
        nodes  = Net.get_themes_sub(self.curr_sub_id)
        if nodes is None:
            return
        self.liststore_sub.clear()
        i = 0
        for node in nodes:
            print('node:', node)
            self.liststore_sub.append([self.app.theme['anonymous'],
                Widgets.short_str(node['name']), int(node['sourceid']), 
                node['info'], ])
            Net.update_liststore_image(self.liststore_sub, i, 0, 
                    node['pic'])
            i += 1

    def on_iconview_sub_item_activated(self, iconview, path):
        model = iconview.get_model()
        self.curr_list_name = model[path][1]
        self.curr_list_id = model[path][2]
        self.label.set_label(self.curr_list_name)
        self.button_sub.set_label(self.curr_sub_name)
        self.curr_list_page = 0
        self.show_songs()
    
    def show_songs(self):
        print('show songs')
        self.scrolled_sub.hide()
        self.button_sub.show_all()
        self.scrolled_songs.get_vadjustment().set_value(0.0)
        self.box_songs.show_all()
        songs_wrap = Net.get_themes_songs(self.curr_list_id, 
                self.curr_list_page)
        if songs_wrap is None:
            return
        self.total_songs = songs_wrap['total']
        songs = songs_wrap['musiclist']
        for song in songs:
            self.liststore_songs.append([
                True, song['name'], song['artist'], song['album'],
                int(song['id']), int(song['artistid']), 
                int(song['albumid']), ])
    
    # buttonbox buttons
    def on_button_main_clicked(self, btn):
        self.buttonbox.hide()
        self.scrolled_sub.hide()
        self.box_songs.hide()
        self.scrolled_main.show_all()

    def on_button_sub_clicked(self, btn):
        self.box_songs.hide()
        self.label.set_label(self.curr_sub_name)
        self.buttonbox.show_all()
        self.button_sub.hide()
        self.scrolled_sub.show_all()
