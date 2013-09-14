

from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Net
from kuwo import Widgets

class RadioItem(Gtk.EventBox):
    def __init__(self, radio_info):
        super().__init__()
        self.connect('button-press-event', self.on_button_pressed)
        # radio_info contains:
        # pic, name, radio_id, offset
        self.radio_info = radio_info
        self.expanded = False

        self.box = Gtk.Box()
        self.box.props.margin_top = 5
        self.box.props.margin_bottom = 5
        self.add(self.box)

        self.img = Gtk.Image()
        self.img_path = Net.get_image(radio_info['pic'])
        self.small_pix = GdkPixbuf.Pixbuf.new_from_file_at_size(
                self.img_path, 50, 50)
        self.big_pix = GdkPixbuf.Pixbuf.new_from_file_at_size(
                self.img_path, 75, 75)
        self.img.set_from_pixbuf(self.small_pix)
        self.box.pack_start(self.img, False, False, 0)

        box_right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.pack_start(box_right, True, True, 0)

        radio_name = Gtk.Label(radio_info['name'])
        box_right.pack_start(radio_name, True, True, 0)

        #self.song_name = Gtk.Label(radio_info['curr_song_name'])
        self.song_name = Gtk.Label('song name')
        box_right.pack_start(self.song_name, False, False, 0)

        self.toolbar = Gtk.Toolbar()
        self.toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        self.toolbar.set_show_arrow(False)
        self.toolbar.set_icon_size(1)
        box_right.pack_start(self.toolbar, False, False, 0)

        button_play = Gtk.ToolButton()
        button_play.set_label('Play')
        button_play.set_icon_name('media-playback-start-symbolic')
        button_play.connect('clicked', self.on_button_play_clicked)
        self.toolbar.insert(button_play, 0)

        button_next = Gtk.ToolButton()
        button_next.set_label('Next')
        button_next.set_icon_name('media-skip-forward-symbolic')
        button_next.connect('clicked', self.on_button_next_clicked)
        self.toolbar.insert(button_next, 1)

        button_favorite = Gtk.ToolButton()
        button_favorite.set_label('Favorite')
        button_favorite.set_icon_name('emblem-favorite-symbolic')
        button_favorite.connect('clicked', self.on_button_favorite_clicked)
        self.toolbar.insert(button_favorite, 2)

        button_delete = Gtk.ToolButton()
        button_delete.set_label('Delete')
        #button_delete.set_icon_name('edit-delete-symbolic')
        button_delete.set_icon_name('user-trash-symbolic')
        button_delete.connect('clicked', self.on_button_delete_clicked)
        self.toolbar.insert(button_delete, 3)

        self.show_all()
        self.song_name.hide()
        self.toolbar.hide()

    def expand(self):
        print('expand()')
        if self.expanded:
            return
        self.expanded = True
        self.img.set_from_pixbuf(self.big_pix)
        self.song_name.show_all()
        self.toolbar.show_all()

    def collapse(self):
        print('collapse()')
        if not self.expanded:
            return
        self.expanded = False
        self.img.set_from_pixbuf(self.small_pix)
        self.song_name.hide()
        self.toolbar.hide()

    def on_button_pressed(self, widget, event):
        print('on button pressed')
        parent = self.get_parent()
        print('parent:', parent)
        children = parent.get_children()
        print('children:', children)
        for child in children:
            print('child:', child)
            child.collapse()
        self.expand()

    # toolbar
    def on_button_play_clicked(self, btn):
        print('play clicked')

    def on_button_next_clicked(self, btn):
        print('next clicked')

    def on_button_favorite_clicked(self, btn):
        print('favorite clicked')

    def on_button_delete_clicked(self, btn):
        print('delete clicked')




class Radio(Gtk.Box):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.first_show = False

        # left side panel
        # radios selected by user.
        self.box_myradio = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box_myradio.props.margin_left = 10
        self.pack_start(self.box_myradio, False, False, 0)

        self.scrolled_radios = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_radios, True, True, 0)

        # pic, name, id, num of listeners, pic_url
        self.liststore_radios = Gtk.ListStore(GdkPixbuf.Pixbuf, str, int, 
                str, str)
        iconview_radios = Widgets.IconView(self.liststore_radios)
        iconview_radios.connect('item_activated',
                self.on_iconview_radios_item_activated)
        self.scrolled_radios.add(iconview_radios)


    def after_init(self):
        pass

    def first(self):
        if self.first_show:
            return
        self.first_show = True
        radios = Net.get_radios_nodes()
        print('radios:', radios)
        if radios is None:
            return
        i = 0
        for radio in radios:
            self.liststore_radios.append([self.app.theme['anonymous'],
                Widgets.short_str(radio['disname']), 
                int(radio['sourceid'].split(',')[0]),
                radio['info'], radio['pic']])
            Net.update_liststore_image(self.liststore_radios, i, 0,
                    radio['pic']),
            i += 1

    def on_iconview_radios_item_activated(self, iconview, path):
        print('item activated')
        model = iconview.get_model()
        radio_info = {
                'name': model[path][1],
                'radio_id': model[path][3],
                'pic': model[path][4],
                # TODO: set default offset.
                'offset': 10,
                }
        print('radio info:', radio_info)
        radio_item = RadioItem(radio_info)
        self.box_myradio.pack_start(radio_item, False, False, 0)
