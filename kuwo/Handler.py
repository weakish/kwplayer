        i = 0
        double = 1
        prev = None
        for key in self.artists_list['cates']:
            button = Gtk.RadioButton()
            button.set_label(key)
            button.props.draw_indicator = False
            button.connect('toggled', self.on_button_artists_cate_toggled)
            if prev is not None:
                button.join_group(prev)
            prev = button
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

        self.ui('scrolledwindow_artists_songs').get_vadjustment().connect(
                'value-changed', 
                self.on_adjustment_artists_songs_value_changed)
        # use this flag to prevent downloading two pages of songs at a time.
        self.artists_append_songs_timestamp = 0

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
        if button.get_active():
            self.update_artist_list(self.artists_list[button.get_label()])

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
        '''
        A new artist is selected.
        '''
        self.artist = Cache.Artist(artist)

        # reset scrolledwindow to top.
        self.ui('scrolledwindow_artists_songs').get_vadjustment().set_value(0)

        self.append_songs_to_list(init=True)

        artist_info = self.artist.get_info()
        if artist_info is None:
            return
        self.update_artist_info(artist_info)

        logo = self.artist.get_logo(artist_info['pic'])
        print('logo: ', logo)
        if logo is None:
            self.update_artist_logo(Config.ARTIST_LOGO_DEFAULT)
        else:
            self.update_artist_logo(logo)

    def update_artist_info(self, artist_info):
        self.ui('label_artists_name').set_label(artist_info['name'])
        self.ui('image_artists_logo').set_tooltip_text(
                artist_info['info'].replace('<br>', '\n'))

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

    def on_treeviewcolumn_checkall_clicked(self, column):
        liststore = self.ui('liststore_artists_songs')
        checkbtn = self.ui('checkbutton_artists_checkall')
        status = checkbtn.get_active()
        print(checkbtn, status)
        checkbtn.set_active(not status)

    def on_cellrenderertoggle_artists_choose_toggled(self, cell, path):
       liststore = self.ui('liststore_artists_songs')
       print(liststore, path, liststore[path][0])
       liststore[path][0] = not liststore[path][0]
       print(liststore[path][0])

    def on_treeview_artists_songs_row_activated(self, tree, path, column):
        liststore = tree.get_model()
        index = tree.get_columns().index(column)
        song = liststore[path]

        if index in (1, 4):
            self.player.play_song(song)
        elif index == 2:
            print('will search album')
        elif index == 5:
            self.player.add_song(song)
        elif index == 6:
            self.player.cache_song(song)

    def on_adjustment_artists_songs_value_changed(self, adj):
        '''
        Automatically load more songs when reaches to bottom of the 
        scrolled-window.
        '''
        timestamp = time.time()
        if adj.get_upper() - adj.get_page_size() - adj.get_value() < 40 and\
                timestamp - self.artists_append_songs_timestamp > 1.5:
            self.artists_append_songs_timestamp = timestamp
            self.append_songs_to_list()

    def append_songs_to_list(self, init=False):
        liststore = self.ui('liststore_artists_songs')
        if init:
            liststore.clear()

        songs = self.artist.get_songs()
        if songs is None:
            return

        play_pix = GdkPixbuf.Pixbuf.new_from_file(Config.PLAY_ICON)
        add_pix = GdkPixbuf.Pixbuf.new_from_file(Config.ADD_ICON)
        download_pix = GdkPixbuf.Pixbuf.new_from_file(Config.DOWNLOAD_ICON)
        for song in songs:
            liststore.append((True, song['SONGNAME'], song['ALBUM'],
                int(song['SCORE100']), play_pix, add_pix, download_pix))

    def on_checkbutton_artists_songs_selectall_toggled(self, checkbtn):
        for song in self.ui('liststore_artists_songs'):
            song[0] = checkbtn.get_active()

    def on_button_artists_songs_play_clicked(self, btn):
        self.player.play_songs([song for song in self.ui(
            'liststore_artists_songs') if song[0] is True])

    def on_button_artists_songs_add_clicked(self, btn):
        self.player.add_songs([song for song in self.ui(
            'liststore_artists_songs') if song[0] is True])

    def on_button_artists_songs_cache_clicked(self, btn):
        self.player.cache_songs([song for song in self.ui(
            'liststore_artists_songs') if song[0] is True])


    # Search Tab
    def on_entry_search_activate(self, entry):
        combo_type = self.ui('combobox_search_type')
        model = combo_type.get_model()
        path = combo_type.get_active()
        _type = model[path][1]

        keyword = entry.get_text()

        print(Net.search(keyword, _type))
