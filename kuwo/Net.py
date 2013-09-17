
import copy
from gi.repository import GdkPixbuf
from gi.repository import GObject
import hashlib
import json
import leveldb
import os
import threading
import urllib.error
from urllib import parse
from urllib import request

from kuwo import Config
from kuwo import Utils

ARTIST_LOGO = 'http://img4.kwcdn.kuwo.cn/star/starheads/'
ARTIST = 'http://artistlistinfo.kuwo.cn/mb.slist?'
QUKU = 'http://qukudata.kuwo.cn/q.k?'
QUKU_SONG = 'http://nplserver.kuwo.cn/pl.svc?'
SEARCH = 'http://search.kuwo.cn/r.s?'
SONG = 'http://antiserver.kuwo.cn/anti.s?'

CHUNK = 2 ** 14
CHUNK_TO_PLAY = 2 ** 21
MAXTIMES = 3
TIMEOUT = 30

# Using weak reference to cache song list in TopList and Radio.
class Dict(dict):
    pass
req_cache = Dict()

# Using leveldb to cache urlrequest
ldb = leveldb.LevelDB(Config.CACHE_DB)

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

def hash_key(_str):
    return hashlib.sha512(_str.encode()).digest()

def img_url(_str):
    return hashlib.sha1(_str.encode()).hexdigest()

def urlopen(_url, use_cache=True):
    # set host port from 81 to 80, to fix image problem
    url = _url.replace(':81', '')
    # hash the url to accelerate string compare speed in db.
    key = hash_key(url)
    if use_cache:
        try:
            req = ldb.Get(key)
            return req
        except KeyError:
            req = None
    retries = 0
    while retries < MAXTIMES:
        try:
            req = request.urlopen(url, timeout=TIMEOUT)
            req_content = req.read()
            if use_cache:
                ldb.Put(key, req_content)
            return req_content
        except Exception as e:
            print(e)
            print('with url:', url)
            retries += 1
    if retries == MAXTIMES:
        return None

def get_nodes(nid):
    print('get_nodes:', nid, type(nid))
    url = ''.join([
        QUKU,
        'op=query&fmt=json&src=mbox&cont=ninfo&rn=500&node=',
        str(nid),
        '&pn=0',
        ])
    print('node url:', url)
    req_content = urlopen(url)
    if req_content is None:
        return None
    try:
        nodes = json.loads(req_content.decode())
    except Exception as e:
        print(e)
        return None
    return nodes['child']

def get_image(url):
    # url should be the absolute path.
    def _parse_image(url): 
        req_content = urlopen(url, use_cache=False)
        if req_content is None:
            return None
        return req_content
    
    def _dump_image(image, filepath):
        with open(filepath, 'wb') as fh:
            fh.write(image)

    if len(url) == 0:
        return None
    filename = os.path.split(url)[1]
    filepath = os.path.join(Config.IMG_DIR, filename)
    if os.path.exists(filepath):
        return filepath

    image = _parse_image(url)
    if image is not None:
        _dump_image(image, filepath)
        return filepath
    return None

def get_album(albumid):
    print('get album()')
    url = ''.join([
        SEARCH,
        'stype=albuminfo&albumid=',
        str(albumid),
        ])
    print('album url:', url)
    req_content = urlopen(url)
    if req_content is None:
        return None
    try:
        songs_wrap = Utils.json_loads_single(req_content.decode())
    except Exception as e:
        print(e)
        return None
    return songs_wrap

def update_liststore_image(liststore, path, col, url):
    def _update_image(filepath, error):
        if filepath is None:
            return
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_size(filepath, 100, 100)
            liststore[path][col] = pix
        except Exception as e:
            print(e, 'filepath:', filepath)
    async_call(get_image, _update_image, url)

def get_toplist_songs(nid):
    # sync call
    url = ''.join([
        'http://kbangserver.kuwo.cn/ksong.s?',
        'from=pc&fmt=json&type=bang&data=content&rn=200&id=',
        str(nid),
        ])
    print('url-songs:', url)
    if url not in req_cache:
        req_content = urlopen(url, use_cache=False)
        if req_content is None:
            return None
        req_cache[url] = req_content
    try:
        songs = json.loads(req_cache[url].decode())
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
    req_content = urlopen(url)
    if req_content is None:
        return None
    try:
        artists = Utils.json_loads_single(req_content.decode())
    except Exception as e:
        print(e)
        return None
    return artists

def update_toplist_node_logo(liststore, path, col, url):
    update_liststore_image(liststore, path, col, url)

def update_artist_logo(liststore, path, col, logo_id):
    if logo_id[:2] in ('55', '90',):
        logo_id = '100/' + logo_id[2:]
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
        req_content = urlopen(url)
        if req_content is None:
            return None
        try:
            info = Utils.json_loads_single(req_content.decode())
        except Exception as e:
            print(e)
            return None

        # set logo size to 100x100
        logo_id = info['pic']
        if logo_id[:2] in ('55', '90',):
            logo_id = '100/' + logo_id[2:]
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
    req_content = urlopen(url)
    if req_content is None:
        return None
    try:
        songs = Utils.json_loads_single(req_content.decode())
    except Error as e:
        print(e)
        return None
    return songs

def get_lrc(_rid):
    def _parse_lrc():
        url = ('http://newlyric.kuwo.cn/newlyric.lrc?' + 
                Utils.encode_lrc_url(rid))
        print('lrc url:', url)
        req_content = urlopen(url, use_cache=False)
        if req_content is None:
            return None
        try:
            lrc = Utils.decode_lrc_content(req_content)
        except Exception as e:
            print(e)
            return None
        return lrc

    rid = str(_rid)
    filepath = os.path.join(Config.LRC_DIR, rid + '.lrc')
    if os.path.exists(filepath):
        with open(filepath) as fh:
            return fh.read()

    lrc = _parse_lrc()
    if lrc is not None:
        with open(filepath, 'w') as fh:
            fh.write(lrc)
        return lrc
    return None

def get_recommend_lists(artist):
    url = ''.join([
        'http://artistpicserver.kuwo.cn/pic.web?',
        'type=big_artist_pic&pictype=url&content=list&&id=0&from=pc',
        '&name=',
        Utils.encode_uri(artist),
        ])
    print('recommend lists url:', url)
    req_content = urlopen(url)
    print('req_content:', req_content)
    if req_content is None:
        return None
    return req_content.decode()

def get_recommend_image(url):
    def _parse_image(url): 
        req_content = urlopen(url, use_cache=False)
        if req_content is None:
            return None
        return req_content

    if len(url) == 0:
        return None
    ext = os.path.splitext(url)[1]
    filename = img_url(url) + ext
    filepath = os.path.join(Config.IMG_LARGE_DIR, filename)
    if os.path.exists(filepath):
        return filepath

    image = _parse_image(url)
    if image is None:
        return None
    with open(filepath, 'wb') as fh:
        fh.write(image)
    return filepath

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
    if url not in req_cache:
        req_content = urlopen(url, use_cache=False)
        if req_content is None:
            return None
        req_cache[url] = req_content
    try:
        result = Utils.json_loads_single(req_cache[url].decode('gbk'))
    except Exception as e:
        print(e)
        return None
    return result

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
    print('get index nodes:', url)
    req_content = urlopen(url)
    if req_content is None:
        return None
    try:
        nodes_wrap = json.loads(req_content.decode())
    except Error as e:
        print(e)
        return None
    return nodes_wrap

def get_themes_main():
    def append_to_nodes(nid, use_child=True):
        node_wrap = get_index_nodes(nid)
        if node_wrap is None:
            return None
        if use_child:
            # node is limited to 10, no more are needed.
            for node in node_wrap['child'][:10]:
                nodes.append({
                    'name': node['disname'],
                    'nid': int(node['id']),
                    'info': node['info'],
                    'pic': node['pic'],
                    })
        else:
            # Because of different image style, we use child picture instaed
            node = node_wrap['ninfo']
            pic = node_wrap['child'][0]['pic']
            nodes.append({
                'name': node['disname'],
                'nid': int(node['id']),
                'info': node['info'],
                'pic': pic,
                })

    nodes = []
    # 语言 10(+)
    append_to_nodes(10)
    # Test:
    # 人群 11
    append_to_nodes(11, False)
    # 节日 12
    append_to_nodes(12, False)
    # 心情 13(+)
    append_to_nodes(13)
    # 场景 14
    append_to_nodes(14, False)
    # 曲风流派 15(+)
    append_to_nodes(15)
    # 时间 72325
    append_to_nodes(72325, False)
    # 环境 72326
    append_to_nodes(72326, False)
    # 精选集 22997 这个格式不正确, 不要了.
    #append_to_nodes(22997, False)
    if len(nodes) > 0:
        return nodes
    else:
        return None

def get_themes_sub(nid):
    return get_nodes(nid)

def get_themes_songs(nid, page):
    url = ''.join([
        QUKU_SONG,
        'op=getlistinfo&rn=200&encode=utf-8&identity=kuwo&keyset=pl2012',
        '&pn=',
        str(page),
        '&pid=',
        str(nid),
        ])
    print('get themes songs:', url)
    if url not in req_cache:
        req_content = urlopen(url, use_cache=False)
        if req_content is None:
            return None
        req_cache[url] = req_content
    try:
        songs_wrap = json.loads(req_cache[url].decode())
    except Exception as e:
        print(e)
        return None
    return songs_wrap

def get_radios_nodes():
    nid = 8
    return get_nodes(nid)

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
    def __init__(self, app):
        super().__init__()
        self.app = app

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
        song_info['filepath'] = os.path.join(self.app.conf['song-dir'], 
                os.path.split(song_link)[1])
        return self._download_song(song_link, song_info)

    def _parse_song_link(self, rid):
        if self.app.conf['use-ape']:
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
        req_content = urlopen(url, use_cache=False)
        if req_content is None:
            return None
        return req_content.decode()

    def _download_song(self, song_link, song_info):
        def _wrap(req):
            received_size = 0
            can_play_emited = False
            content_length = int(req.headers.get('Content-Length'))
            print('size of file: ', round(content_length / 2**20, 2), 'M')
            with open(song_info['filepath'], 'wb') as fh:
                while True:
                    chunk = req.read(CHUNK)
                    received_size += len(chunk)
                    # emit chunk-received signals
                    # contains content_length and retrieved_size
                    percent = int(received_size/content_length * 100)
                    #print('percent:', percent)
                    # emit every 10% received, to reduce GUI queue draw. 
                    #if percent % 10 == 0:
                    #    self.emit('chunk-received', song_info, percent)

                    # check retrieved_size, and emit can-play signal.
                    # this signal only emit once.
                    if (received_size > CHUNK_TO_PLAY or percent > 40) \
                            and not can_play_emited:
                        print('song can be played now')
                        can_play_emited = True
                        self.emit('can-play', song_info)
                    if not chunk:
                        break
                    fh.write(chunk)
                #emit downloaded signal.
                print('download finished')
                self.emit('downloaded', song_info)

        if os.path.exists(song_info['filepath']): 
            self.emit('can-play', song_info)
            self.emit('downloaded', song_info)
            return song_info
        retried = 0
        while retried < MAXTIMES:
            try:
                req = request.urlopen(song_link)
                _wrap(req)
                return song_info
            except Exception as e:
                print(e)
                retried += 1
        # remember to check song_info when `downloaded` signal received.
        if retried == MAXTIMES:
            self.emit('downloaded', None)
            return None
GObject.type_register(Song)

class AsyncSong(Song):
    def get_song(self, song, callback):
        print('AsyncSong.get_song()')
        async_call(self._get_song, callback, song)

    def _get_song(self, song):
        song_link = self._parse_song_link(song['rid'])
        print('song link:', song_link)
        if song_link is None:
            return None

        song_info = copy.copy(song)
        song_info['filepath'] = os.path.join(self.app.conf['song-dir'], 
                os.path.split(song_link)[1])
        return self._download_song(song_link, song_info)
GObject.type_register(AsyncSong)
