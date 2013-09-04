
import json
import os
import sqlite3
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

    filename = os.path.split(url)[1]
    filepath = os.path.join(conf['img-dir'], filename)
    if os.path.exists(filepath):
        return filepath

    image = _parse_image(url)
    if image is not None:
        _dump_image(image, filepath)
        return filepath
    return None

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

    def get_info(self):
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

    def get_songs(self):
        '''
        Get 50 songs of this artist.
        '''
        #Rearch the max num
        if self.total_songs > 0 and self.page * 50 > self.total_songs:
            return None

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

        self.page += 1
        if self.total_songs == 0:
            self.total_songs = int(songs['TOTAL'])
        return songs['abslist']

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
        self.total_nodes = 0
        self.page = 0

    def get_nodes(self):
        '''
        Get 50 nodes of this nid
        '''
        if self.total_nodes > 0 and self.page * 50 > self.total_nodes:
            return None

        url = ''.join([
            QUKU,
            'op=query&fmt=json&src=mbox&cont=ninfo&rn=50&node=',
            str(self.nid),
            '&pn=',
            str(self.page),
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
        self.page += 1
        if self.total_nodes == 0:
            self.total_nodes = int(nodes['total'])
        return nodes['child']


class TopList:
    '''
    Get the info of Top List songs.
    '''
    def get_songs(self):
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
        return songs['musiclist']


#class Song(GObject.GObject):
#    '''
#    Use Gobject to emit signals:
#    register three signals: can-play and downloaded
#    if `can-play` emited, player will receive a filename which have
#    at least 1M to play.
#    `chunk-received` signal is used to display the progressbar of 
#    downloading process.
#    `downloaded` signal may be used to popup a message to notify 
#    user that a new song is downloaded.
#    '''
#    __gsignals__ = {
#            'can-play': (GObject.SIGNAL_RUN_LAST, 
#                GObject.TYPE_NONE, (GObject.TYPE_GSTRING, )),
#            'chunk-received': (GObject.SIGNAL_RUN_LAST,
#                GObject.TYPE_NONE, 
#                (GObject.TYPE_UINT, GObject.TYPE_UINT)),
#            'downloaded': (GObject.SIGNAL_RUN_LAST, 
#                GObject.TYPE_NONE, (GObject.TYPE_GSTRING, ))
#            }
#    def __init__(self):
#        super().__init__()
#        self.init_table()
#
#    def init_table(self):
#        sql = '''
#        CREATE TABLE IF NOT EXISTS `song` (
#        rid CHAR,
#        name CHAR,
#        artist CHAR,
#        song_ext CHAR
#        )
#        '''
#        cursor.execute(sql)
#
#    def get_song(self, rid):
#        '''
#        Get the actual link of music file.
#        If higher quality of that music unavailable, a lower one is used.
#        like this:
#        response=url&type=convert_url&format=ape|mp3&rid=MUSIC_3312608
#        '''
#        song_ext = self._read_song(rid)
#        song_ext = '.ape'
#        if song_ext is not None:
#            filename = os.path.join(conf['song-dir'], rid + song_ext)
#            #emit can-play and downloaded signals.
#        self.emit('can-play', filename)
#        self.emit('downloaded', filename)
#        return 
#
#        song_link = self._parse_song_link()
#        print('song link:', song_link)
#
#        if song_link is None:
#            return None
#        song_ext = os.path.splitext(song_link)[1]
#        filename = os.path.join(conf['song-dir'], rid + song_ext)
#        self._download_song(song_link, filename)
#        return filename
#
#    def _read_song(self, rid):
#        sql = 'SELECT song_ext FROM `song` WHERE rid=? LIMIT 1'
#        req = cursor.execute(sql, (rid, ))
#        song = req.fetchone()
#        if song is not None:
#            return song[0]
#        return None
#
#    def _parse_song_link(self):
#        if conf['use-ape']:
#            _format = 'ape|mp3'
#        else:
#            _format = 'mp3'
#        url = ''.join([
#            SONG,
#            'response=url&type=convert_url&format=',
#            ext_format,
#            '&rid=MUSIC_',
#            rid,
#            ])
#        print('url-song-link:', url)
#        req = request.urlopen(url)
#        if req.status != 200:
#            return None
#        return req.read().decode()
#
#    def _download_song(self, song_link, filename):
#        req = request.urlopen(song_link)
#        retrieved_size = 0
#        content_length = req.headers.get('Content-Length')
#        with open(filename, 'wb') as fh:
#            while True:
#                chunk = req.read(CHUNK)
#                retrieved_size += len(chunk)
#                # emit chunk-received signals
#                # contains content_length and retrieved_size
#
#                # check retrieved_size, and emit can-play signal.
#                if retrieved_size > CHUNK_TO_PLAY:
#                    print('song can be played noew')
#                if not chunk:
#                    break
#                fh.write(chunk)
#            #emit downloaded signal.
#            print('download finished')
## register Song to GObject
#GObject.type_register(Song)
