
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gtk


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


def short_str(_str):
    if len(_str) > 10:
        return _str[:9] + '..'
    return _str
