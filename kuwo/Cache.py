
import json
import os
import sqlite3
from urllib import parse
from urllib import request

from kuwo import Config

SEARCH = 'http://search.kuwo.cn/r.s?'

conn = sqlite3.connect(Config.DB_CACHE)
cursor = conn.cursor()
def close():
    conn.commit()
    cursor.close()
    conn.close()


def quote_gbk(string):
    return parse.quote_from_bytes(string.encode('gbk'))

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
        info TEXT
        )
        '''
        cursor.execute(sql)

        sql = '''
        CREATE TABLE IF NOT EXISTS `artistmusic` (
        artist CHAR,
        pn INT,
        music TEXT
        )
        '''
        cursor.execute(sql)

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
        sql = 'INSERT INTO `artistinfo` VALUES(?, ?)'
        cursor.execute(sql, (self.artist, json.dumps(info)))
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
        print('page:', self.page, 'total songs:', self.total_songs)
        return songs['abslist']

    def _read_songs(self):
        sql = 'SELECT music FROM `artistmusic` WHERE artist=? AND pn=? LIMIT 1'
        req = cursor.execute(sql, (self.artist, self.page))
        songs = req.fetchone()
        if songs is not None:
            return json.loads(songs[0])
        return None

    def _parse_songs(self):
        '''
        Get 50 songs of this artist.
        '''
        url = ''.join([
            SEARCH,
            'ft=music&rn=50&itemset=newkw&newsearch=1',
            '&cluster=0&primitive=0&rformat=json&encoding=UTF8&artist=',
            quote_gbk(self.artist),
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
        sql = 'INSERT INTO `artistmusic` VALUES(?, ?, ?)'
        cursor.execute(sql, (self.artist, self.page, json.dumps(songs)))
        conn.commit()

    def get_logo(self, logo_id):
        # set logo size to 120x120
        if logo_id[:2] in ('55', '90'):
            logo_id = '120/' + logo_id[3:]

        filepath = os.path.join(Config.IMG_CACHE, logo_id)

        if os.path.exists(filepath):
            return filepath
        image = self._parse_logo(logo_id)
        if image is None:
            return None
        self._dump_logo(image, filepath)
        return filepath

    def _parse_logo(self, logo_id): 
        url = 'http://img4.kwcdn.kuwo.cn/star/starheads/' + logo_id
        print('url-logo:', url)
        req = request.urlopen(url)
        if req.status != 200:
            return None
        return req.read()
    
    def _dump_logo(self, image, filepath):
        path, filename = os.path.split(filepath)
        if not os.path.exists(path):
            os.makedirs(path)
        with open(filepath, 'wb') as fh:
            fh.write(image)


class Lyrics:
    pass
