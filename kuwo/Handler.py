
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gtk

from kuwo import Net
from kuwo import Config


class Handler:
    def __init__(self, builder):
        self.ui = builder.get_object

        self.window = self.ui('main_window')
        self.initUI()

    def initUI(self):
        # init artists tab
        liststore_artists = self.ui('liststore_artists')
        self.artists_list = Config.load_artists_list()
        grid_artists = self.ui('grid_artists')

        i = 0
        double = 1
        for key in self.artists_list['cates']:
            button = Gtk.ToggleButton(key)
            button.connect('toggled', self.on_button_artists_cate_toggled)
            if len(key) == 1:
                double = (double + 1) % 2
                grid_artists.attach(button, double, i, 1, 1)
                i += double
            else:
                grid_artists.attach(button, 0, i, 2, 1)
                i += 1
        self.button_artists_old = None
        self.toggle_artists_signal_hanlder(True)
        self.update_artist_logo(Config.ARTIST_LOGO_DEFAULT)

    def run(self):
        self.window.show_all()
        Gtk.main()

    def on_app_exit(self, widget, event=None):
        Gtk.main_quit()


    # Notebooks
    def on_notebook_main_switch_page(self, notebook, child, page_num):
        print(notebook)
        print(page_num)


    # Artists Tab
    def on_entry_artists_search_changed(self, entry):
        '''
        Search artists from artist list.
        '''
        keyword = entry.get_text()
        if len(keyword) == 0:
            return
        artists = self.search_artist_from_list(keyword)
        self.update_artist_list(artists)

    def search_artist_from_list(self, keyword):
        artists = []
        for cate in range(65, 91):
            for artist in self.artists_list[chr(cate)]:
                if artist.lower().find(keyword) > -1:
                    artists.append(artist)
                if len(artists) > 50:
                    return artists
        return artists


    def on_button_artists_cate_toggled(self, button):
        '''
        Update artist list when artist category changed
        '''
        if self.button_artists_old is not None:
            self.button_artists_old.props.active = False
        self.update_artist_list(self.artists_list[button.get_label()])
        self.button_artists_old = button

#    def cache_artist_liststore_gen(self):
#        for key in self.artists_list['cates']:
#            self.artists_liststores[key] = Gtk.ListStore(str)
#            for artist in self.artists_list[key]:
#                self.artists_liststores[key].append((artist,))
#            yield True

    def update_artist_list(self, artists):
        def gen():
            # block clicked signal.
            self.toggle_artists_signal_hanlder(False)

            liststore_artists = self.ui('liststore_artists')
            liststore_artists.clear()
            # reset scrolledwindow to top.
            self.ui('scrolledwindow_artists').get_vadjustment().set_value(0)

            i = 0
            for artist in artists:
                liststore_artists.append((artist,))
                i += 1
                if i % 200 == 0:
                    yield True
            # reconnect signal handler
            self.toggle_artists_signal_hanlder(True)
        g = gen()
        next(g)
        GObject.idle_add(g.__next__)

    def on_treeview_selection_artists_changed(self, treeselection):
        liststore, path = treeselection.get_selected()
        if path is None:
            return
        artist = liststore[path][0]
        self.update_artists_artist(artist)

    def toggle_artists_signal_hanlder(self, on, handler_id=[0]):
        tree_sel = self.ui('treeview_selection_artists')
        if on is True and handler_id[0] == 0:
            handler_id[0] = tree_sel.connect('changed', 
                    self.on_treeview_selection_artists_changed)
        elif on is False and handler_id[0] > 0:
            tree_sel.disconnect(handler_id[0])
            handler_id[0] = 0

    def update_artists_artist(self, artist):
        print('update artists artist: ', artist)
        songs = Net.get_songs_by_artist(artist)
        if songs is None:
            return

        artist_info = Net.get_artist_info(artist)
        if artist_info is None:
            return
        self.update_artist_info(artist_info)

        logo = Net.get_artist_logo(artist_info['pic'])
        print('logo: ', logo)
        if logo is None:
            self.update_artist_logo(Config.ARTIST_LOGO_DEFAULT)
        else:
            self.update_artist_logo(logo)

    def update_artist_info(self, artist_info):
        self.ui('label_artists_name').set_label(artist_info['name'])
        self.ui('image_artists_logo').set_tooltip_text(artist_info['info'])

        box = self.ui('box_artists_similar')
        # remove old buttons and add some new buttons
        for button in box.get_children()[1:]:
            box.remove(button)

        for artist in artist_info['similar'].split(';')[:3]:
            btn = Gtk.Button(label=artist)
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.connect('clicked', 
                    lambda btn, artist: self.update_artists_artist(artist),
                    artist)
            box.pack_start(btn, True, True, 0)
            btn.show()

    def update_artist_logo(self, image):
        pix = GdkPixbuf.Pixbuf.new_from_file_at_size(image, 120, 120)
        self.ui('image_artists_logo').set_from_pixbuf(pix)


    # Search Tab
    def on_entry_search_activate(self, entry):
        combo_type = self.ui('combobox_search_type')
        model = combo_type.get_model()
        path = combo_type.get_active()
        _type = model[path][1]

        keyword = entry.get_text()

        print(Net.search(keyword, _type))
