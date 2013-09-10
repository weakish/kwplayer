
import copy
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
import json
import os
import sqlite3
import threading
import time
from urllib import parse
from urllib import request

from kuwo import Config
from kuwo import Utils

SEARCH = 'http://search.kuwo.cn/r.s?'
QUKU = 'http://qukudata.kuwo.cn/q.k?'
TOPLIST = 'http://kbangserver.kuwo.cn/ksong.s?'
LRC = 'http://newlyric.kuwo.cn/newlyric.lrc?'
ARTIST_LOGO = 'http://img4.kwcdn.kuwo.cn/star/starheads/'
SONG = 'http://antiserver.kuwo.cn/anti.s?'
ARTISTLIST = 'http://artistlistinfo.kuwo.cn/mb.slist?'
CHUNK = 16 * 1024
CHUNK_TO_PLAY = 1024 * 1024

conf = Config.load_conf()
conn = sqlite3.connect(conf['cache-db'])
cursor = conn.cursor()
def close():
    conn.commit()
    conn.close()
    print('db closed')

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

def get_image(url):
    '''
    Return local image path if exists,
    or retrieve from url and save it to filepath.
    If both fails, return None
    '''
    def _parse_image(url): 
        print('url-image:', url)
        if not url.startswith('http:'):
            url = ARTIST_LOGO + url
        req = request.urlopen(url)
        if req.status != 200:
            return None
        return req.read()
    
    def _dump_image(image, filepath):
        with open(filepath, 'wb') as fh:
            fh.write(image)

    filename = os.path.split(url)[1]
    filepath = os.path.join(conf['img-dir'], filename)
    image = _parse_image(url)
    if image is not None:
        _dump_image(image, filepath)
        return filepath
    return None

def update_liststore_image(liststore, path, col, url):
    '''
    Update images in IconView(liststore).
    '''
    def _update_image(filepath, error):
        if filepath is None:
            return
        #Gdk.threads_enter()
        pix = GdkPixbuf.Pixbuf.new_from_file(filepath)
        liststore[path][col] = pix
        #Gdk.threads_leave()
    
    # image image is cached locally, just load them.
    filename = os.path.split(url)[1]
    filepath = os.path.join(conf['img-dir'], filename)
    if os.path.exists(filepath):
        _update_image(filepath, None)
        return

    print('update_liststore_image:', url)
    async_call(get_image, _update_image, url)

def get_lrc(rid):
    '''
    Get lrc content of specific song with UTF-8
    rid like this: '928003'
    '''
    def _parse_lrc():
        url = LRC + Utils.encode_lrc_url(rid)
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
    return Utils.json_loads_single(req.read().decode('gbk'))


class ArtistSong:
    '''
    artist operations like get songs
    Create this class because we need to store some private information to
    simplify the design of program.
    '''
    def __init__(self, artist):
        self.artist = artist
        self.page = 0
        self.total_songs = 0

        self.init_tables()

    def init_tables(self):
        sql = '''
        CREATE TABLE IF NOT EXISTS `artistmusic` (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artist CHAR,
        pn INT,
        songs TEXT
        )
        '''
        cursor.execute(sql)
        conn.commit()

    def get_songs(self):
        #Rearch the max num
        if self.total_songs > 0 and self.page * 50 > self.total_songs:
            return None

        songs = self._read_songs()
        if songs is None:
            songs = self._parse_songs()
            if songs is not None:
                self._dump_songs(songs)
        self.page += 1
        if self.total_songs == 0:
            self.total_songs = int(songs['TOTAL'])
        return songs['abslist']

    def _read_songs(self):
        sql = 'SELECT songs FROM `artistmusic` WHERE artist=? AND pn=? LIMIT 1'
        req = cursor.execute(sql, (self.artist, self.page))
        songs = req.fetchone()
        if songs is not None:
            print('local song cache HIT!')
            return json.loads(songs[0])
        return None

    def _parse_songs(self):
        '''
        Get 50 songs of this artist.
        '''
        url = ''.join([
            SEARCH,
            'ft=music&rn=50&itemset=newkw&newsearch=1&cluster=0',
            '&primitive=0&rformat=json&encoding=UTF8&artist=',
            parse.quote(self.artist, encoding='GBK'),
            '&pn=',
            str(self.page),
            ])
        print('url-songs:', url)
        req = request.urlopen(url)
        if req.status != 200:
            return None
        try:
            songs = Utils.json_loads_single(req.read().decode())
        except Exception as e:
            print(e)
            return None
        return songs

    def _dump_songs(self, songs):
        sql = 'INSERT INTO `artistmusic`(artist, pn, songs) VALUES(?, ?, ?)'
        cursor.execute(sql, (self.artist, self.page, json.dumps(songs))) 
        conn.commit()







class Artists:
    def __init__(self):
        pass

    def get_artists(self, category, page):
        #TODO: memorize page number
        artists = self._parse_list(category, page)
        return artists['artistlist']

    def _parse_list(self, category, page):
        url = ''.join([
            ARTISTLIST,
            'stype=artistlist&order=hot&rn=50&category=',
            str(category),
            '&pn=',
            str(page)
            ])
        print('artist url:', url)
        
        req = request.urlopen(url)
        if req.status != 200:
            return None
        artists = Utils.json_loads_single(req.read().decode())
        return artists



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

    Remember to call Song.close() method when exit the process.
    '''
    __gsignals__ = {
            'can-play': (GObject.SIGNAL_RUN_LAST, 
                GObject.TYPE_NONE, (object, )),
            'chunk-received': (GObject.SIGNAL_RUN_LAST,
                GObject.TYPE_NONE, 
                (GObject.TYPE_UINT, GObject.TYPE_UINT)),
            'downloaded': (GObject.SIGNAL_RUN_LAST, 
                GObject.TYPE_NONE, (object, ))
            }
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.conn = sqlite3.connect(conf['song-db'])
        self.cursor = self.conn.cursor()
        self.init_table()

    def close(self):
        self.conn.commit()
        self.conn.close()

    def init_table(self):
        self.cols = ['id', 'name', 'artist', 'album', 'rid', 'artistid',
                'albumid', 'filepath']
        sql = '''
        CREATE TABLE IF NOT EXISTS `song` (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name CHAR,
        artist CHAR,
        album CHAR,
        rid INTEGER,
        artistid INTEGER,
        albumid INTEGER,
        filepath CHAR
        )
        '''
        self.cursor.execute(sql)
        self.conn.commit()

    def play_song(self, song):
        '''
        Get the actual link of music file.
        If higher quality of that music unavailable, a lower one is used.
        like this:
        response=url&type=convert_url&format=ape|mp3&rid=MUSIC_3312608
        '''
        song_info = self._read_song_info(song['rid'])
        if song_info is not None:
            #emit can-play and downloaded signals.
            self.emit('can-play', song_info)
            self.emit('downloaded', song_info)
            return 

        # TODO: use async call:
        song_link = self._parse_song_link(song['rid'])
        print('song link:', song_link)

        if song_link is None:
            return None

        song_info = copy.copy(song)
        song_info['filepath'] = os.path.join(conf['song-dir'], 
                os.path.split(song_link)[1])
        self._write_song_info(song_info)
        self._download_song(song_link, song_info)
        return

    def append_playlist(self, song_info):
        return

    def cache_song(self, song_info):
        return

    def _read_song_info(self, rid):
        sql = 'SELECT * FROM `song` WHERE rid=? LIMIT 1'
        req = self.cursor.execute(sql, (rid, ))
        song = req.fetchone()
        if song is not None:
            song_info = dict(zip(self.cols , song))
            if os.path.exists(song_info['filepath']):
                return song_info
            else:
                self._delete_song_info(song_info)
                return None
        return None

    def _write_song_info(self, song_info):
        sql = '''INSERT INTO `song` (
                name, artist, album, rid, artistid, albumid, filepath
                ) VALUES(? , ?, ?, ?, ?, ?, ?)'''
        self.cursor.execute(sql, [song_info['name'], song_info['artist'], 
            song_info['album'], song_info['rid'], song_info['artistid'], 
            song_info['albumid'], song_info['filepath']])
        self.conn.commit()

    def _delete_song_info(self, song_info):
        sql = 'DELETE FROM `song` WHERE id=? LIMIT 1'
        self.cursor.execute(sql, (song_info['id'], ))
        self.conn.commit()

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
            rid,
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
            self.emit('downloaded', song_info)
            print('download finished')

# register Song to GObject
GObject.type_register(Song)
