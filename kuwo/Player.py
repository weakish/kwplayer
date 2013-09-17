

from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import Gst
from gi.repository import Gtk
import html
import time

from kuwo import Net
from kuwo import Widgets

# Gdk.EventType.2BUTTON_PRESS is an invalid variable
GDK_2BUTTON_PRESS = 5


def delta(nanosec_float):
    _seconds = nanosec_float // 10**9
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
        self.adj_timeout = 0
        self.is_radio = False

        event_logo = Gtk.EventBox()
        self.pack_start(event_logo, False, False, 0)
        event_logo.connect('button-press-event', self.on_logo_pressed)

        self.logo = Gtk.Image.new_from_pixbuf(app.theme['anonymous'])
        event_logo.add(self.logo)

        toolbar = Gtk.Toolbar()
        toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)
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

        self.shuffle_btn = Gtk.ToggleToolButton()
        self.shuffle_btn.set_label('Shuffle')
        self.shuffle_btn.set_icon_name('media-playlist-shuffle-symbolic')
        toolbar.insert(self.shuffle_btn, 5)

        self.repeat_btn = Gtk.ToggleToolButton()
        self.repeat_btn.set_label('Repeat')
        self.repeat_btn.set_icon_name('media-playlist-repeat-symbolic')
        toolbar.insert(self.repeat_btn, 6)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.pack_start(box, True, True, 0)

        box.pack_start(toolbar, False, False, 0)

        self.label = Gtk.Label('<b>Unknown</b> <i>by unknown</i>')
        self.label.props.use_markup = True
        self.label.props.xalign = 0
        box.pack_start(self.label, True, False, 0)

        box2 = Gtk.Box(spacing=5)
        box.pack_start(box2, True, False, 0)

        self.scale = Gtk.Scale()
        self.adjustment = Gtk.Adjustment(0, 0, 100, 1, 10, 0)
        self.scale.set_adjustment(self.adjustment)
        self.scale.props.draw_value = False
        self.scale.connect('change-value', self.on_scale_change_value)
        box2.pack_start(self.scale, True, True, 0)

        self.label_time = Gtk.Label('0:00/0:00')
        box2.pack_start(self.label_time, False, False, 0)

        self.volume = Gtk.VolumeButton()
        #self.volume.props.use_symbolic = True
        self.volume.set_value(app.conf['volume'])
        self.volume.connect('value-changed', self.on_volume_value_changed)
        box2.pack_start(self.volume, False, False, 0)

    def after_init(self):
        self.pause_btn.hide()

    def load(self, song):
        self.is_radio = False
        if self._player is not None:
            self.play_pause(None)
            del self._player
        self._player = Gst.ElementFactory.make('playbin', 'player')

        if len(song['filepath']) != 0: 
            print('player will load:', song)
            self._player.set_property('uri', 'file://'+ song['filepath'])
            GLib.timeout_add(1000, self.init_adjustment)
            self.adj_timeout = 0
            self.play_start(None)
            self.curr_song = song
            self._player.set_property('volume', self.volume.get_value())
            self.update_player_info(song)
            self.get_lrc()
            self.get_recommend_lists()
            return
        # download and load the song.
        parse_song = Net.AsyncSong(self.app)
        parse_song.connect('can-play', self.on_can_play)
        parse_song.get_song(song, self.on_song_downloaded)

    def on_can_play(self, widget, song):
        # Maybe we should ignore this signal
        GLib.idle_add(self.load, song)

    def on_song_downloaded(self, song, error=None):
        # use this to temporarily solve the problem above.
        GLib.idle_add(self.init_adjustment)
        if song:
            self.app.playlist.on_song_downloaded(song)

    def init_adjustment(self):
        self.adjustment.set_value(0.0)
        self.adjustment.set_lower(0.0)
        # when song is not totally downloaded but can play, query_duration
        # might give incorrect/inaccurate result.
        status, upper = self._player.query_duration(Gst.Format.TIME)
        if status and upper > 0:
            self.adjustment.set_upper(upper)
            return False
        return True
    
    def sync_adjustment(self):
        status, curr = self._player.query_position(Gst.Format.TIME)
        if status:
            status, total = self._player.query_duration(Gst.Format.TIME)
            self.adjustment.set_value(curr)
            curr_time = delta(curr)
            total_time = delta(total)
            self.label_time.set_label('{0}/{1}'.format(curr_time, total_time))
            if total_time == curr_time:
                self.on_eos()
            self.app.lrc.sync_lrc(curr)
            if self.recommend_imgs:
                div, mod = divmod(int(curr / 10**9), 20)
                if mod == 0:
                    div, mod = divmod(div, len(self.recommend_imgs))
                    url = self.recommend_imgs[mod]
                    self.update_lrc_background(url)
        return True

    def sync_label_by_adjustment(self):
        curr = delta(self.adjustment.get_value())
        total = delta(self.adjustment.get_upper())
        self.label_time.set_label('{0}/{1}'.format(curr, total))


    # top widgets
    def on_logo_pressed(self, eventbox, event):
        if event.type == GDK_2BUTTON_PRESS:
            self.app.playlist.locate_curr_song()

    def play_previous(self, btn):
        if self.is_radio:
            return
        _repeat = self.repeat_btn.get_active()
        _shuffle = self.shuffle_btn.get_active()
        prev_song = self.app.playlist.get_prev_song(repeat=_repeat, 
                shuffle=_shuffle)
        print('prev song:', prev_song)
        if prev_song is not None:
            self.load(prev_song)

    def play_next(self, btn):
        # use EOS to force load next song.
        self.on_eos()

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
        self.app.conf['volume'] = value
        # Use a factor to reduce volume change
        if self._player is None:
            return
        self._player.set_property('volume', value)
#        if value < 0.3:
#            self._player.set_property('volume', value*0.25)
#        elif value < 0.6:
#            self._player.set_property('volume', value*0.5)
#        else:
#            self._player.set_property('volume', value)

    def update_player_info(self, song):
        def _update_logo(info, error=None):
            if info is None:
                return
            self.logo.set_tooltip_text(info['info'].replace('<br>', '\n'))
            if info['logo'] is not None:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_size(info['logo'], 
                        100, 100)
                self.logo.set_from_pixbuf(pix)
            
        label = ''.join([
            '<b>', Widgets.short_str(html.escape(song['name']), length=45),
            '</b> ', '<i><small>by ', 
            Widgets.short_str(html.escape(song['artist']), length=15), 
            ' from ', Widgets.short_str(html.escape(song['album']), 
                length=30), '</small></i>'])
        self.label.set_label(label)
        self.logo.set_from_pixbuf(self.app.theme['anonymous'])
        Net.get_artist_info(_update_logo, song['artistid'])

    def get_lrc(self):
        def _update_lrc(lrc_text, error=None):
            print('_update_lrc()')
            self.app.lrc.set_lrc(lrc_text)
        Net.async_call(Net.get_lrc, _update_lrc, self.curr_song['rid'])

    def get_recommend_lists(self):
        self.recommend_imgs = None
        def _on_list_received(imgs, error=None):
            if imgs is None or len(imgs) == 0:
                return
            self.recommend_imgs = imgs.splitlines()
        Net.async_call(Net.get_recommend_lists, _on_list_received, 
                self.curr_song['artist'])

    def update_lrc_background(self, url):
        def _update_background(filepath, error=None):
            if filepath:
                self.app.lrc.update_background(filepath)
        Net.async_call(Net.get_recommend_image, _update_background, url)

    def on_eos(self):
        '''
        When EOS is reached, try to fetch next song.
        '''
        print('End of Source')
        self.play_pause()
        _repeat = self.repeat_btn.get_active()
        _shuffle = self.shuffle_btn.get_active()
        if self.is_radio:
            self.curr_radio_item.play_next_song()
        else:
            next_song = self.app.playlist.get_next_song(repeat=_repeat, 
                    shuffle=_shuffle)
            print('next song:', next_song)
            if next_song is not None:
                self.load(next_song)

    # Radio part
    def play_radio(self, song, radio_item):
        def _on_radio_can_play(widget, song):
            GLib.idle_add(self.on_radio_can_play(song))

        def _on_radio_downloaded(*args):
            pass

        self.is_radio = True
        self.curr_radio_item = radio_item
        if self._player is not None:
            self.play_pause(None)
            del self._player
        self._player = Gst.ElementFactory.make('playbin', 'player')
        parse_song = Net.AsyncSong(self.app)
        parse_song.connect('can-play', _on_radio_can_play)
        parse_song.get_song(song, _on_radio_downloaded)

    def on_radio_can_play(self, song):
        self._player.set_property('uri', 'file://'+ song['filepath'])
        GLib.timeout_add(1000, self.init_adjustment)
        self.adj_timeout = 0
        self.play_start(None)
        self.curr_song = song
        self._player.set_property('volume', self.volume.get_value())
        self.update_player_info(song)
        self.get_lrc()
        self.get_recommend_lists()
