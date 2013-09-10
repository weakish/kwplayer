

from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import Gst
from gi.repository import Gtk
import html
import time

from kuwo import Net


def delta(sec_float):
    _seconds = sec_float // 10**9
    mm, ss = divmod(_seconds, 60)
    hh, mm = divmod(mm, 60)
    if hh == 0:
        s = '%d:%02d' % (mm, ss)
    else:
        s = '%d:%02d:%02d' % (hh, mm, ss)
    return s

class Player(Gtk.Box):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self._player = None

        self.logo = Gtk.Image.new_from_pixbuf(app.theme['anonymous'])

        self.pack_start(self.logo, False, False, 0)

        toolbar = Gtk.Toolbar()
        toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        toolbar.set_show_arrow(False)
        toolbar.set_icon_size(5)

        prev_btn = Gtk.ToolButton()
        prev_btn.set_label('Previous')
        prev_btn.set_icon_name('media-skip-backward-symbolic')
        prev_btn.connect('clicked', self.play_previous)
        toolbar.insert(prev_btn, 0)

        self.play_btn = Gtk.ToolButton()
        self.play_btn.set_label('Play')
        self.play_btn.set_icon_name('media-playback-start-symbolic')
        self.play_btn.connect('clicked', self.play_start)
        toolbar.insert(self.play_btn, 1)

        self.pause_btn = Gtk.ToolButton()
        self.pause_btn.set_label('Pause')
        self.pause_btn.set_icon_name('media-playback-pause-symbolic')
        self.pause_btn.connect('clicked', self.play_pause)
        toolbar.insert(self.pause_btn, 2)

        next_btn = Gtk.ToolButton()
        next_btn.set_label('Next')
        next_btn.set_icon_name('media-skip-forward-symbolic')
        next_btn.connect('clicked', self.play_next)
        toolbar.insert(next_btn, 3)

        sep = Gtk.SeparatorToolItem()
        toolbar.insert(sep, 4)

        shuffle_btn = Gtk.ToggleToolButton()
        shuffle_btn.set_label('Shuffle')
        shuffle_btn.set_icon_name('media-playlist-shuffle-symbolic')
        shuffle_btn.connect('clicked', self.play_shuffle)
        toolbar.insert(shuffle_btn, 5)

        repeat_btn = Gtk.ToggleToolButton()
        repeat_btn.set_label('Repeat')
        repeat_btn.set_icon_name('media-playlist-repeat-symbolic')
        repeat_btn.connect('clicked', self.play_repeat)
        toolbar.insert(repeat_btn, 6)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.pack_start(box, True, True, 0)

        box.pack_start(toolbar, False, False, 0)

        self.label = Gtk.Label('')
        self.label.props.use_markup = True
        self.label.props.xalign = 0
        box.pack_start(self.label, True, False, 0)

        box2 = Gtk.Box(spacing=5)
        box.pack_start(box2, True, False, 0)

        self.scale = Gtk.Scale()
        self.adjustment = Gtk.Adjustment()
        self.scale.set_adjustment(self.adjustment)
        self.scale.props.draw_value = False
        self.scale.connect('change-value', self.on_scale_change_value)
        box2.pack_start(self.scale, True, True, 0)

        self.label_time = Gtk.Label('0:00/0:00')
        box2.pack_start(self.label_time, False, False, 0)

        self.volume = Gtk.VolumeButton()
        self.volume.set_value(0.2)
        self.volume.connect('value-changed', self.on_volume_value_changed)
        box2.pack_start(self.volume, False, False, 0)

    def after_init(self):
        self.pause_btn.hide()

    def load(self, song):
        print('player will load this song:')
        print(song)
        if self._player is not None:
            self.play_pause(None)
            del self._player
        self._player = Gst.ElementFactory.make('playbin', 'player')
        local_song = self.app.playlist.play_song(song)
        print('local song is :', local_song)
        if local_song is not None:
            self._player.set_property('uri', 'file://'+ local_song['filepath'])
            GLib.timeout_add(500, self.init_adjustment)
            self.adj_timeout = 0
            self.play_start(None)
            self.update_player_info(song)
            return
        # download and load the song.
        parse_song = Net.Song()
        parse_song.connect('can-play', self.on_can_play)
        parse_song.get_song(song)



    def on_can_play(self, widget, song_info):
        # store this song_info to db.
        self.app.playlist.append_song(song_info)
        self.load(song_info)

    def init_adjustment(self):
        print('init adjustment()')
        self.adjustment.set_value(0.0)
        self.adjustment.set_lower(0.0)
        status, upper = self._player.query_duration(Gst.Format.TIME)
        if status and upper > 0:
            self.adjustment.set_upper(upper)
            return False
        return True
    
    def sync_adjustment(self):
        print('sync_adjustment()')
        status, curr = self._player.query_position(Gst.Format.TIME)
        if status:
            self.adjustment.set_value(curr)
            total_time = delta(self.adjustment.get_upper())
            curr_time = delta(curr)
            self.label_time.set_label('{0}/{1}'.format(curr_time, total_time))
            if total_time == curr_time:
                self.on_eos()
        return True

    def sync_label_by_adjustment(self):
        curr = delta(self.adjustment.get_value())
        total = delta(self.adjustment.get_upper())
        self.label_time.set_label('{0}/{1}'.format(curr, total))

    def play_previous(self, btn):
        pass

    def play_next(self, btn):
        pass

    def play_start(self, btn=None):
        if self._player is None:
            return
        self.adj_timeout = GLib.timeout_add(500, self.sync_adjustment)
        self._player.set_state(Gst.State.PLAYING)
        self.play_btn.hide()
        self.pause_btn.show()

    def play_pause(self, btn=None):
        if self._player is None:
            return 
        if self.adj_timeout > 0:
            GLib.source_remove(self.adj_timeout)
            self.adj_timeout = 0
        self._player.set_state(Gst.State.PAUSED)
        self.pause_btn.hide()
        self.play_btn.show()

    def play_shuffle(self, toggle):
        pass

    def play_repeat(self, toggle):
        pass

    def on_scale_change_value(self, scale, scroll_type, value):
        '''
        When user move the scale, pause play and seek audio position.
        '''
        if self._player is None:
            return
        status, state, pending = self._player.get_state(10**8)
        if state == Gst.State.PLAYING:
            self.play_pause()
        self._player.seek_simple(Gst.Format.TIME, 
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                self.adjustment.get_value())
        self.sync_label_by_adjustment()
        self.player_timestamp = time.time()
        GLib.timeout_add(450, self._delay_play, self.player_timestamp)

    def _delay_play(self, local_timestamp):
        if self.player_timestamp == local_timestamp:
            self.play_start()
        return False

    def on_volume_value_changed(self, volume, value):
        # Use a factor to reduce volume change
        if value < 0.3:
            self._player.set_property('volume', value*0.25)
        elif value < 0.6:
            self._player.set_property('volume', value*0.5)
        else:
            self._player.set_property('volume', value)

    def update_player_info(self, song):
        def _update_logo(info, error=None):
            print('update player logo:', info)
            if info is None:
                return
            self.logo.set_tooltip_text(info['info'].replace('<br>', '\n'))
            if info['logo'] is not None:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_size(info['logo'], 
                        120, 120)
                self.logo.set_from_pixbuf(pix)
            
        label = ''.join([
            '<b>', html.escape(song['name']), '</b> ',
            '<i><small>by ', html.escape(song['artist']), ' from ',
            html.escape(song['album']), '</small></i>'])
        print('label text:', label)
        self.label.set_label(label)
        self.logo.set_from_pixbuf(self.app.theme['anonymous'])

        Net.get_artist_info(_update_logo, song['artistid'])

    def on_eos(self):
        '''
        When EOS is reached, do something.
        '''
        print('End of Source')
        self.play_pause()
