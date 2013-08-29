
import json
import os


PREF = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'share',
        'kuwo')

UI_FILE = os.path.join(PREF, 'window.ui')
ARTIST_LOGO_DEFAULT = os.path.join(PREF, 'logo-128.png')
PLAY_ICON = os.path.join(PREF, 'play.svg')
ADD_ICON = os.path.join(PREF, 'add.svg')
DOWNLOAD_ICON = os.path.join(PREF, 'download.svg')

HOME_DIR = os.path.expanduser('~')
CACHE_DIR = os.path.join(HOME_DIR, '.cache', 'kuwo')
CONF_DIR = os.path.join(HOME_DIR, '.config', 'kuwo')

_ARTISTS_JSON = os.path.join(PREF, 'artists.json')

IMG_CACHE = os.path.join(CACHE_DIR, 'images')
DB_CACHE = os.path.join(CACHE_DIR, 'db.sqlite')

def load_artists_list():
    with open(_ARTISTS_JSON) as fh:
        return json.loads(fh.read())
