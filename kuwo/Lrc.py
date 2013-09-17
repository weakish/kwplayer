

import cairo
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gtk
import os
import re
import time


def list_to_time(time_tags):
    mm, ss, ml = time_tags
    if ml is None:
        curr_time = int(mm) * 60 + int(ss)
    else:
        curr_time = int(mm) * 60 + int(ss) + float(ml)
    return int(curr_time * 10**9)


def lrc_parser(lrc_txt):
    if lrc_txt is None:
        return None
    lines = lrc_txt.split('\n')
    lrc_obj = []
    reg_time = re.compile('\[([0-9]{2}):([0-9]{2})(\.[0-9]{1,3})?\]')
    for line in lines:
        offset = 0
        match = reg_time.match(line)
        tags = []
        while match:
            time = list_to_time(match.groups())
            tags.append(time)
            offset = match.end()
            match = reg_time.match(line, offset)
        content = line[offset:]
        for tag in tags:
            lrc_obj.append((tag, content))
    return sorted(lrc_obj)

class Lrc(Gtk.ScrolledWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.lrc_obj = None
        self.tv_background = os.path.join(app.conf['theme'],
                'lrc-background.jpg')

        self.buf = Gtk.TextBuffer()
        self.buf.set_text('Lrc loading...')
        self.tag_centered = self.buf.create_tag('blue_fg', 
                foreground='blue')
        self.tv= Gtk.TextView(buffer=self.buf)
        self.tv.props.editable = False
        self.tv.props.cursor_visible = False
        self.tv.props.justification = Gtk.Justification.CENTER
        self.tv.props.pixels_above_lines = 10
        self.tv.connect('draw', self.on_tv_draw)
        self.add(self.tv)

    def after_init(self):
        pass

    def first(self):
        pass

    def set_lrc(self, lrc_txt):
        self.old_line = -1
        self.old_line_iter = None
        print('lrc_txt:', lrc_txt)
        if lrc_txt is None:
            print('failed to get lrc')
            self.buf.set_text('No lrc available')
            self.lrc_obj = None
            return
        self.lrc_obj = lrc_parser(lrc_txt)
        print('lrc obj:', self.lrc_obj)
        self.get_vadjustment().set_value(0)
        self.lrc_content = [l[1] for l in self.lrc_obj]
        self.buf.set_text('\n'.join(self.lrc_content))
        self.sync_lrc(0)

    def sync_lrc(self, timestamp):
        if self.lrc_obj is None:
            return
        line_num = self.old_line + 1
        if len(self.lrc_obj) > line_num and \
                timestamp < self.lrc_obj[line_num][0]:
            return
        if self.old_line >= 0 and self.old_line_iter and \
                len(self.old_line_iter) == 2:
            self.buf.remove_tag(self.tag_centered, *self.old_line_iter)
        while len(self.lrc_obj) > line_num and \
                timestamp > self.lrc_obj[line_num][0]:
            line_num += 1
        line_num -= 1
        iter_start = self.buf.get_iter_at_line(line_num)
        iter_end = self.buf.get_iter_at_line(line_num+1)
        self.buf.apply_tag(self.tag_centered, iter_start, iter_end)
        self.tv.scroll_to_iter(iter_start, 0, True, 0, 0.5)
        self.old_line_iter = (iter_start, iter_end)
        self.old_line = line_num

    def update_background(self, filepath, error=None):
        if filepath and os.path.exists(filepath):
            self.tv_background = filepath

    def on_tv_draw(self, textview, cr):
        tv_width = self.tv.get_allocated_width()
        tv_height = self.tv.get_allocated_height()

        # TODO, use a better linear gradient
        lg3 = cairo.LinearGradient(20.0, 260.0, 20.0, 360.0)
        lg3.add_color_stop_rgba(0.9, 0.9, 0.9, 0.9, 10) 
        lg3.add_color_stop_rgba(0.7, 0.7, 0.7, 0.7, 10) 

        cr.rectangle(0, 0, tv_width, tv_height)
        cr.set_source(lg3)
        cr.fill()

        if self.tv_background:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_size(self.tv_background,
                    tv_width, tv_height)
            pix_width = pix.get_width()
            pix_height = pix.get_height()
            d_width = (tv_width - pix_width) / 2
            d_height = (tv_height - pix_height) / 2
            Gdk.cairo_set_source_pixbuf(cr, pix, d_width, d_height)
            cr.paint()

            cr.set_source_rgba(0.83, 0.84, 0.83, 0.45)
            cr.set_line_width(14)
            cr.rectangle(d_width + 30, d_height+30, pix_width-65, 
                    pix_height-65)
            cr.fill()
        else:
            cr.set_source_rgba(0.83, 0.84, 0.83, 0.65)
            cr.set_line_width(14)
            cr.rectangle(0, 0, tv_width, tv_height)
            cr.fill()
