
import copy
from gi.repository import GdkPixbuf
from gi.repository import GObject
import json
import os
import sqlite3
import threading
from urllib import parse
from urllib import request

from kuwo import Config
from kuwo import Utils

ARTIST_LOGO = 'http://img4.kwcdn.kuwo.cn/star/starheads/'
ARTIST = 'http://artistlistinfo.kuwo.cn/mb.slist?'
SEARCH = 'http://search.kuwo.cn/r.s?'
SONG = 'http://antiserver.kuwo.cn/anti.s?'
CHUNK = 16 * 1024
CHUNK_TO_PLAY = 1024 * 1024

conf = Config.load_conf()


# calls f on another thread
def async_call(func, func_done, *args):
    def do_call(*args):
        result = None
        error = None

        try:
            result = func(*args)
        except Exception as e:
            error = e

        GObject.idle_add(lambda: func_done(result, error))

    thread = threading.Thread(target=do_call, args=args)
    thread.start()

def get_nodes(nid):
    print('get_nodes:', nid, type(nid))
    url = ''.join([
        'http://qukudata.kuwo.cn/q.k?',
        'op=query&fmt=json&src=mbox&cont=ninfo&rn=200&node=',
        str(nid),
        '&pn=0',
        ])
    print('node url:', url)
    req = request.urlopen(url)
    if req.status != 200:
        return None
    try:
        nodes = json.loads(req.read().decode())
    except Exception as e:
        print(e)
        return None
    return nodes['child']

def get_image(url):
    # sync call
    # url should be the absolute path.
    def _parse_image(url): 
        print('url-image:', url)
        req = request.urlopen(url)
        if req.status != 200:
            return None
        return req.read()
    
    def _dump_image(image, filepath):
        with open(filepath, 'wb') as fh:
            fh.write(image)

    filename = os.path.split(url)[1]
    filepath = os.path.join(conf['img-dir'], filename)
    if os.path.exists(filepath):
        return filepath

    image = _parse_image(url)
    if image is not None:
        _dump_image(image, filepath)
        return filepath
    return None

def update_liststore_image(liststore, path, col, url):
    def _update_image(filepath, error):
        if filepath is None:
            return
        pix = GdkPixbuf.Pixbuf.new_from_file(filepath)
        liststore[path][col] = pix
    async_call(get_image, _update_image, url)

def get_toplist_songs(nid):
    # sync call
    url = ''.join([
        'http://kbangserver.kuwo.cn/ksong.s?',
        'from=pc&fmt=json&type=bang&data=content&rn=200&id=',
        str(nid),
        ])
    print('url-songs:', url)
    req = request.urlopen(url)
    if req.status != 200:
        return None
    try:
        songs = json.loads(req.read().decode())
    except Exception as e:
        print(e)
        return None
    return songs['musiclist']

def get_artists(catid, page, prefix):
    print('get artists()')
    url = ''.join([
        ARTIST,
        'stype=artistlist&order=hot&rn=50&category=',
        str(catid),
        '&pn=',
        str(page),
        ])
    if len(prefix) > 0:
        url = url + '&prefix=' + prefix
    print('get artists url:', url)
    req = request.urlopen(url)
    if req.status != 200:
        return None
    try:
        artists = Utils.json_loads_single(req.read().decode())
    except Exception as e:
        print(e)
        return None
    return artists

def update_toplist_node_logo(liststore, path, col, url):
    # TODO:
    update_liststore_image(liststore, path, col, url)

def update_artist_logo(liststore, path, col, logo_id):
    if logo_id[:3] in ('55/', '90/', '100'):
        logo_id = '120/' + logo_id[3:]
    url = ARTIST_LOGO + logo_id
    update_liststore_image(liststore, path, col, url)

def get_artist_info(callback, artistid):
    '''
    Get artist info, if cached, just return it.
    At least one of these parameters is specified, and artistid is prefered.

    This function uses async_call(), and the callback function is called 
    when the artist info is retrieved.

    Artist logo is also retrieved and saved to info['logo']
    '''
    def _parse_info():
        print('_parse info()')
        url = ''.join([
            SEARCH, 
            'stype=artistinfo&artistid=', 
            str(artistid),
            ])

        print('artist-info:', url)
        req = request.urlopen(url)
        if req.status != 200:
            return None
        try:
            info = Utils.json_loads_single(req.read().decode())
        except Exception as e:
            print(e)
            return None

        # set logo size to 120x120
        logo_id = info['pic']
        if logo_id[:3] in ('55/', '90/', '100'):
            logo_id = '120/' + logo_id[3:]
        url = ARTIST_LOGO + logo_id
        info['logo'] = get_image(url)
        return info
    async_call(_parse_info, callback)

def get_artist_songs(artist, page):
    '''
    Get 200 songs of this artist.
    '''
    url = ''.join([
        SEARCH,
        'ft=music&rn=200&itemset=newkw&newsearch=1&cluster=0',
        '&primitive=0&rformat=json&encoding=UTF8&artist=',
        parse.quote(artist, encoding='GBK'),
        '&pn=',
        str(page),
        ])
    print('url-songs:', url)
    req = request.urlopen(url)
    if req.status != 200:
        return None
    try:
        songs = Utils.json_loads_single(req.read().decode())
    except Error as e:
        print(e)
        return None
    return songs



def get_lrc(_rid):
    def _parse_lrc():
        url = ('http://newlyric.kuwo.cn/newlyric.lrc?' + 
                Utils.encode_lrc_url(rid))
        print('lrc url:', url)
        req = request.urlopen(url)
        if req.status != 200:
            return None
        data = req.read()
        try:
            lrc = Utils.decode_lrc_content(data)
        except Exception as e:
            print(e)
            return None
        return lrc

    rid = str(_rid)
    filepath = os.path.join(conf['lrc-dir'], rid + '.lrc')
    if os.path.exists(filepath):
        with open(filepath) as fh:
            return fh.read()

    lrc = _parse_lrc()
    if lrc is not None:
        with open(filepath, 'w') as fh:
            fh.write(lrc)
        return lrc
    return None


def search(keyword, _type, page=0):
    '''
    Search songs, albums, MV.
    No local cache.
    '''
    url = ''
    if _type == 'all':
        url = ''.join([
            SEARCH,
            'all=',
            parse.quote(keyword),
            '&rformat=json&encoding=UTF8&rn=50',
            '&pn=',
            str(page),
            ])
    print('url-search:', url)
    req = request.urlopen(url)
    if req.status != 200:
        return None
    txt = req.read().decode('gbk').replace("'", '"')
    return json.loads(txt)


def get_index_nodes(nid):
    '''
    Get content of nodes from nid=2 to nid=15
    '''
    url = ''.join([
        QUKU,
        'op=query&fmt=json&src=mbox&cont=ninfo&rn=500&node=',
        str(nid),
        '&pn=0',
        ])
    print('_parse_node url:', url)
    if url in _requests:
        return _requests[url]
    _requests[url] = None
    req = request.urlopen(url)
    if req.status != 200:
        return None
    try:
        nodes = json.loads(req.read().decode())
    except Error as e:
        print(e)
        return None
    _requests[url] = nodes['child']
    return _requests[url]


class Song(GObject.GObject):
    '''
    Use Gobject to emit signals:
    register three signals: can-play and downloaded
    if `can-play` emited, player will receive a filename which have
    at least 1M to play.
    `chunk-received` signal is used to display the progressbar of 
    downloading process.
    `downloaded` signal may be used to popup a message to notify 
    user that a new song is downloaded.
    '''
    __gsignals__ = {
            'can-play': (GObject.SIGNAL_RUN_LAST, 
                GObject.TYPE_NONE, (object, )),
            'chunk-received': (GObject.SIGNAL_RUN_LAST,
                GObject.TYPE_NONE, 
                (object, int)),
            'downloaded': (GObject.SIGNAL_RUN_LAST, 
                GObject.TYPE_NONE, (object, ))
            }
    def __init__(self):
        super().__init__()

    def get_song(self, song):
        '''
        Get the actual link of music file.
        If higher quality of that music unavailable, a lower one is used.
        like this:
        response=url&type=convert_url&format=ape|mp3&rid=MUSIC_3312608
        '''
        song_link = self._parse_song_link(song['rid'])
        print('song link:', song_link)
        if song_link is None:
            return None

        song_info = copy.copy(song)
        song_info['filepath'] = os.path.join(conf['song-dir'], 
                os.path.split(song_link)[1])
        self._download_song(song_link, song_info)

    def _parse_song_link(self, rid):
        if conf['use-ape']:
            _format = 'ape|mp3'
        else:
            _format = 'mp3'
        url = ''.join([
            SONG,
            'response=url&type=convert_url&format=',
            _format,
            '&rid=MUSIC_',
            str(rid),
            ])
        print('url-song-link:', url)
        req = request.urlopen(url)
        if req.status != 200:
            return None
        return req.read().decode()

    def _download_song(self, song_link, song_info):
        if os.path.exists(song_info['filepath']): 
            self.emit('can-play', song_info)
            self.emit('downloaded', song_info)
            return
        req = request.urlopen(song_link)
        retrieved_size = 0
        can_play_emited = False
        content_length = req.headers.get('Content-Length')
        with open(song_info['filepath'], 'wb') as fh:
            while True:
                chunk = req.read(CHUNK)
                retrieved_size += len(chunk)
                # emit chunk-received signals
                # contains content_length and retrieved_size

                # check retrieved_size, and emit can-play signal.
                # this signal only emit once.
                if retrieved_size > CHUNK_TO_PLAY and not can_play_emited:
                    can_play_emited = True
                    self.emit('can-play', song_info)
                    print('song can be played now')
                if not chunk:
                    break
                fh.write(chunk)
            #emit downloaded signal.
            print('download finished')
            self.emit('downloaded', song_info)
GObject.type_register(Song)

class AsyncSong(Song):
    def get_song(self, song):
        print('AsyncSong.get_song()')
        async_call(self._get_song, self.on_downloaded, song)

    def _get_song(self, song):
        song_link = self._parse_song_link(song['rid'])
        print('song link:', song_link)
        if song_link is None:
            return None

        song_info = copy.copy(song)
        song_info['filepath'] = os.path.join(conf['song-dir'], 
                os.path.split(song_link)[1])
        self._download_song(song_link, song_info)
        #async_call(self._download_song, self.on_downloaded, 
        #        song_link, song_info)

    def on_downloaded(self, *args):
        print('AsyncSong.on_downloaded()')
        print(args)

    def _download_song(self, song_link, song_info):
        if os.path.exists(song_info['filepath']): 
            self.emit('can-play', song_info)
            self.emit('downloaded', song_info)
            print('downloaded signal emited')
            return
        req = request.urlopen(song_link)
        received_size = 0
        can_play_emited = False
        content_length = int(req.headers.get('Content-Length'))
        with open(song_info['filepath'], 'wb') as fh:
            while True:
                chunk = req.read(CHUNK)
                received_size += len(chunk)
                # emit chunk-received signals
                percent = int(received_size/content_length * 100)
                self.emit('chunk-received', song_info, percent)
                print('new chunk received:', percent)

                # check retrieved_size, and emit can-play signal.
                # this signal only emit once.
                if received_size > CHUNK_TO_PLAY and not can_play_emited:
                    can_play_emited = True
                    self.emit('can-play', song_info)
                    print('song can be played now')
                if not chunk:
                    break
                fh.write(chunk)
            #emit downloaded signal.
            print('download finished')
            self.emit('downloaded', song_info)
            print('downloaded signal emited')

GObject.type_register(AsyncSong)
