
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

def get_filepath_from_url(url):
    filename = os.path.split(url)[1]
    return os.path.join(conf['img-dir'], filename)

def get_image(url):
    '''
    Return local image path if exists,
    or retrieve from url and save it to filepath.
    If both fails, return None
    '''
    def _parse_image(url): 
        print('url-image:', url)
        req = request.urlopen(url)
        if req.status != 200:
            return None
        return req.read()
    
    def _dump_image(image, filepath):
        with open(filepath, 'wb') as fh:
            fh.write(image)

    filepath = get_filepath_from_url(url)
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
    filepath = get_filepath_from_url(url)
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
    txt = req.read().decode('gbk').replace("'", '"')
    return json.loads(txt)


class Artist:
    '''
    artist operations like get songs, artist info.
    '''
    def __init__(self, artist):
        self.artist = artist
        self.page = 0
        self.total_songs = 0

        self.init_tables()

    def init_tables(self):
        sql = '''
        CREATE TABLE IF NOT EXISTS `artistinfo` (
        artist CHAR,
        info TEXT,
        timestamp INT
        )
        '''
        self.cursor.execute(sql)

        sql = '''
        CREATE TABLE IF NOT EXISTS `artistmusic` (
        artist CHAR,
        pn INT,
        songs TEXT,
        timestamp INT
        )
        '''
        cursor.execute(sql)
        conn.commit()

    def get_info(self):
        info = self._read_info()
        if info is not None:
            return info

        info = self._parse_info()
        if info is not None:
            self._dump_info(info)
        return info

    def _read_info(self):
        sql = 'SELECT info FROM `artistinfo` WHERE artist=? LIMIT 1'
        req = cursor.execute(sql, (self.artist,))
        info = req.fetchone()
        if info is not None:
            return json.loads(info[0])
        return None

    def _parse_info(self):
        url = ''.join([
            SEARCH,
            'stype=artistinfo&artist=',
            parse.quote(self.artist),
            ])
        print('url-info:', url)
        req = request.urlopen(url)
        if req.status != 200:
            return None
        try:
            info = json.loads(req.read().decode().replace("'", '"'))
        except Error as e:
            print(e)
            return None
        return info

    def _dump_info(self, info):
        sql = 'INSERT INTO `artistinfo` VALUES(?, ?, ?)'
        cursor.execute(sql, (self.artist, json.dumps(info),
            int(time.time())))
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
            songs = json.loads(req.read().decode().replace("'", '"'))
        except Error as e:
            print(e)
            return None
        return songs

    def _dump_songs(self, songs):
        sql = 'INSERT INTO `artistmusic` VALUES(?, ?, ?, ?)'
        cursor.execute(sql, (self.artist, self.page, 
            json.dumps(songs), int(time.time())))
        conn.commit()

    def get_logo(self, logo_id):
        # set logo size to 120x120
        if logo_id[:3] in ('55/', '90/', '100'):
            logo_id = '120/' + logo_id[3:]
        url = ARTIST_LOGO + logo_id
        return get_image(url)


class Node:
    '''
    Get content of nodes from nid=2 to nid=15
    '''
    def __init__(self, nid):
        self.nid = nid

        self.init_tables()

    def init_tables(self):
        sql = '''
        CREATE TABLE IF NOT EXISTS `nodes` (
        nid INT,
        info TEXT,
        timestamp INT
        )
        '''
        cursor.execute(sql)
        conn.commit()

    def get_nodes(self):
        nodes = self._read_nodes()
        if nodes is None:
            nodes = self._parse_nodes()
            if nodes is not None:
                self._dump_nodes(nodes)
        return nodes['child']

    def _read_nodes(self):
        sql = 'SELECT info FROM `nodes` WHERE nid=? LIMIT 1'
        req = cursor.execute(sql, (self.nid,))
        nodes = req.fetchone()
        if nodes is not None:
            print('local cache HIT!')
            return json.loads(nodes[0])
        return None

    def _parse_nodes(self):
        '''
        Get 50 nodes of this nid
        '''
        url = ''.join([
            QUKU,
            'op=query&fmt=json&src=mbox&cont=ninfo&rn=200&node=',
            str(self.nid),
            '&pn=0',
            ])
        print('_parse_node url:', url)
        req = request.urlopen(url)
        if req.status != 200:
            return None
        try:
            nodes = json.loads(req.read().decode())
        except Error as e:
            print(e)
            return None
        return nodes

    def _dump_nodes(self, nodes):
        sql = 'INSERT INTO `nodes` VALUES(?, ?, ?)'
        cursor.execute(sql, (self.nid, json.dumps(nodes),
            int(time.time())))
        conn.commit()


class TopList:
    '''
    Get the info of Top List songs.
    '''
    def __init__(self, nid):
        self.nid = nid

        self.init_tables()

    def init_tables(self):
        sql = '''
        CREATE TABLE IF NOT EXISTS `toplist` (
        nid INT,
        songs TEXT,
        timestamp INT
        )
        '''
        cursor.execute(sql)
        conn.commit()

    def get_songs(self):

        songs = self._read_songs()
        if songs is None:
            songs = self._parse_songs()
            if songs is not None:
                self._dump_songs(songs)
        return songs['musiclist']

    def _read_songs(self):
        sql = 'SELECT songs FROM `toplist` WHERE nid=? LIMIT 1'
        req = cursor.execute(sql, (self.nid, ))
        songs = req.fetchone()
        if songs is not None:
            print('local cache HIT!')
            return json.loads(songs[0])
        return None

    def _parse_songs(self):
        '''
        Get 50 songs of this top list.
        '''
        url = ''.join([
            TOPLIST,
            'from=pc&fmt=json&type=bang&data=content&rn=200&id=',
            str(self.nid),
            ])
        print('url-songs:', url)
        req = request.urlopen(url)
        if req.status != 200:
            return None
        try:
            songs = json.loads(req.read().decode())
        except Error as e:
            print(e)
            return None
        return songs

    def _dump_songs(self, songs):
        sql = 'INSERT INTO `toplist` VALUES(?, ?, ?)'
        cursor.execute(sql, (self.nid, json.dumps(songs), 
            int(time.time())))
        conn.commit()


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
                GObject.TYPE_NONE, (GObject.TYPE_GSTRING, )),
            'chunk-received': (GObject.SIGNAL_RUN_LAST,
                GObject.TYPE_NONE, 
                (GObject.TYPE_UINT, GObject.TYPE_UINT)),
            'downloaded': (GObject.SIGNAL_RUN_LAST, 
                GObject.TYPE_NONE, (GObject.TYPE_GSTRING, ))
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
        sql = '''
        CREATE TABLE IF NOT EXISTS `song` (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name CHAR,
        artist CHAR,
        album CHAR,
        rid CHAR,
        artistid CHAR,
        albumid CHAR,
        filename CHAR
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
            filepath = os.path.join(conf['song-dir'], song_info['filename'])
            #emit can-play and downloaded signals.
            self.emit('can-play', filepath)
            self.emit('downloaded', filepath)
            return 

        song_link = self._parse_song_link(song['rid'])
        print('song link:', song_link)

        if song_link is None:
            return None
        filename = os.path.split(song_link)[1]
        filepath = os.path.join(conf['song-dir'], filename)
        self._download_song(song_link, filepath)
        self._write_song_info(filename, song)
        return

    def append_playlist(self, song_info):
        print('append playlist')
        return

    def cache_song(self, song_info):
        print('cache song')
        return

    def _read_song_info(self, rid):
        sql = 'SELECT * FROM `song` WHERE rid=? LIMIT 1'
        req = self.cursor.execute(sql, (rid, ))
        song_info = req.fetchone()
        if song_info is not None:
            print('local song cache HIT!')
            print(song_info)
            if os.path.exists(os.path.join(conf['song-dir'], song_info[6])):
                return song_info
            else:
                self._delte_song_info(song_info)
                return None
        return None

    def _write_song_info(self, filename, song):
        sql = '''INSERT INTO `song` (
                name, artist, album, rid, artistid, albumid, filename
                ) VALUES(? , ?, ?, ?, ?, ?, ?)'''
        self.cursor.execute(sql, [song['name'], song['artist'], 
            song['album'], song['rid'], song['artistid'], song['albumid'], 
            filename, ])
        self.conn.commit()

    def _delete_song_info(self, song_info):
        sql = 'DELETE FROM `song` WHERE id=? LIMIT 1'
        self.cursor.execute(sql, (song_info[0], ))
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

    def _download_song(self, song_link, filepath):
        if os.path.exists(filepath): 
            print('local song cache HIT!')
            self.emit('can-play', filepath)
            self.emit('downloaded', filepath)
            return
        req = request.urlopen(song_link)
        retrieved_size = 0
        can_play_emited = False
        content_length = req.headers.get('Content-Length')
        with open(filepath, 'wb') as fh:
            while True:
                chunk = req.read(CHUNK)
                retrieved_size += len(chunk)
                # emit chunk-received signals
                # contains content_length and retrieved_size

                # check retrieved_size, and emit can-play signal.
                # this signal only emit once.
                if retrieved_size > CHUNK_TO_PLAY and not can_play_emited:
                    can_play_emited = True
                    self.emit('can-play', filepath)
                    print('song can be played now')
                if not chunk:
                    break
                fh.write(chunk)
            #emit downloaded signal.
            self.emit('downloaded', filepath)
            print('download finished')

# register Song to GObject
GObject.type_register(Song)
