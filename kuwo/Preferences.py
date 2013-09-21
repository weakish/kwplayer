
from gi.repository import Gdk
from gi.repository import Gtk

from kuwo import Config

class NoteTab(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_border_width(10)


class BoldLabel(Gtk.Label):
    def __init__(self, label):
        super().__init__(label)
        self.set_use_markup(True)
        self.props.halign = Gtk.Align.START
        self.props.xalign = 0
        self.props.margin_bottom = 10

# TODO
class ChooseFolder(Gtk.FileChooserButton):
    def __init__(self):
        super().__init__()

class Preferences(Gtk.Dialog):
    def __init__(self, app):
        super().__init__('Preferences', app.window, 0,
                (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE,))
        self.app = app
        self.set_default_size(600, 320)
        self.set_border_width(5)
        box = self.get_content_area()
        #box.props.margin_left = 15

        notebook = Gtk.Notebook()
        box.pack_start(notebook, True, True, 0)

        # format tab
        format_box = NoteTab()
        notebook.append_page(format_box, Gtk.Label('Format'))

        audio_label = BoldLabel('<b>Prefered Audio Format</b>')
        format_box.pack_start(audio_label, False, False, 0)
        radio_mp3 = Gtk.RadioButton('MP3 (faster)')
        radio_mp3.props.margin_left = 15
        radio_mp3.connect('toggled', self.on_audio_toggled)
        format_box.pack_start(radio_mp3, False, False, 0)
        radio_ape = Gtk.RadioButton('APE (better)')
        radio_ape.join_group(radio_mp3)
        radio_ape.props.margin_left = 15
        radio_ape.set_active(app.conf['use-ape'])
        radio_ape.connect('toggled', self.on_audio_toggled)
        format_box.pack_start(radio_ape, False, False, 0)

        video_label = BoldLabel('<b>Prefered Video Format</b>')
        video_label.props.margin_top = 20
        format_box.pack_start(video_label, False, False, 0)
        radio_mp4 = Gtk.RadioButton('MP4 (faster)')
        radio_mp4.props.margin_left = 15
        radio_mp4.connect('toggled', self.on_video_toggled)
        format_box.pack_start(radio_mp4, False, False, 0)
        radio_mkv = Gtk.RadioButton('MKV (better)')
        radio_mkv.props.margin_left = 15
        radio_mkv.join_group(radio_mp4)
        radio_mkv.set_active(app.conf['use-mkv'])
        radio_mkv.connect('toggled', self.on_video_toggled)
        format_box.pack_start(radio_mkv, False, False, 0)

        # lyrics tab
        lrc_box = NoteTab()
        notebook.append_page(lrc_box, Gtk.Label('Lyrics'))

        lrc_back_box = Gtk.Box()
        lrc_box.pack_start(lrc_back_box, False, False, 0)

        lrc_back_label = Gtk.Label('<b>Background color</b>')
        lrc_back_label.set_use_markup(True)
        lrc_back_box.pack_start(lrc_back_label, False, False, 0)

        lrc_back_color = Gtk.ColorButton()
        lrc_back_color.set_use_alpha(True)
        lrc_back_rgba = Gdk.RGBA()
        lrc_back_rgba.parse(app.conf['lrc-back-color'])
        lrc_back_color.set_rgba(lrc_back_rgba)
        lrc_back_color.connect('color-set', self.on_lrc_back_color_set)
        lrc_back_color.set_title('Choose color for Lyrics background')
        lrc_back_box.pack_start(lrc_back_color, False, False, 20)
        
        # folders tab
        folder_box = NoteTab()
        notebook.append_page(folder_box, Gtk.Label('Folders'))

        song_folder_label = NoteTab('<b>Place to store sogns</b>')
        folder_box.pack_start(song_folder_label, False, False, 0)

        song_folder_button = ChooseFolder()

        mv_folder_label = NoteTab('<b>Place to store MVs</b>')
        folder_box.pack_start(mv_folder_label, False, False, 0)

    def run(self):
        self.get_content_area().show_all()
        super().run()

    def on_destroy(self):
        print('dialog.on_destroy()')
        Config.dump_conf(self.app.conf)

    def on_audio_toggled(self, radiobtn):
        self.app.conf['use-ape'] = radiobtn.get_group()[0].get_active()

    def on_video_toggled(self, radiobtn):
        # radio_group[0] is MKV
        self.app.conf['use-mkv'] = radiobtn.get_group()[0].get_active()

    def on_lrc_back_color_set(self, colorbutton):
        back_rgba = colorbutton.get_rgba()
        # Fixed: if alpha == 1, to_string() will remove alpha value
        #        and we got a RGB instead of RGBA.
        if back_rgba.alpha == 1:
            back_rgba.alpha = 0.999
        back_rgba.to_string()
        self.app.conf['lrc-back-color'] = back_rgba.to_string()
