
import json
import os

from gi.repository import GdkPixbuf


if __file__.startswith('/usr/'):
    PREF = '/usr/share/kuwo'
else:
    PREF = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'share', 'kuwo')

_ui_files = ('main.ui', 'menus.ui', 'toplist.ui')
UI_FILES = [os.path.join(PREF, 'ui', ui) for ui in _ui_files]


HOME_DIR = os.path.expanduser('~')
CACHE_DIR = os.path.join(HOME_DIR, '.cache', 'kuwo')
CONF_DIR = os.path.join(HOME_DIR, '.config', 'kuwo')
_conf_file = os.path.join(CONF_DIR, 'kuwo', 'conf.json')

NODES = (
       ('Top List', 2), # 排行榜
       ('MV', 3),
       ('Artists', 4), # 歌手
       ('Hot Categories', 5), # 热门分类
       ('Broadcasting', 8), # 电台
       ('Language', 10), # 语言
       ('People', 11), # 人群
       ('Festival', 12), # 节日
       ('Temper', 13), # 心情
       ('Scene', 14), # 场景
       ('Genre', 15), # 曲风流派
       ('Playlist', 0),
       ('Search', 0),
       ('Download', 0),
        )

_default_conf = {
        'window-size': (800, 480),
        'use-ape': False,
        'use-mkv': False,
        'song-dir': os.path.join(CACHE_DIR, 'song'),
        'lrc-dir': os.path.join(CACHE_DIR, 'lrc'),
        'img-dir': os.path.join(CACHE_DIR, 'images'),
        'mv-dir': os.path.join(CACHE_DIR, 'mv'),
        'cache-dir': os.path.join(CACHE_DIR, 'cache'),
        'cache-db': os.path.join(CACHE_DIR, 'cache.sqlite'),
        'song-db': os.path.join(CACHE_DIR, 'music.sqlite'),
        'mv-db': os.path.join(CACHE_DIR, 'music.sqlite'),
        'theme': os.path.join(PREF, 'themes', 'default', 'images.json')
        }

def load_conf():
    return _default_conf
    # TODO: For test
    if os.path.exists(_conf_file):
        with open(_conf_file) as fh:
            return json.loads(fh.read())

    try:
        os.makedirs(os.path.dirname(_conf_file))
    except Exception as e:
        print('Error', e)
    dump_conf(_default_conf)
    return _default_conf

def dump_conf(conf):
    with open(_conf_file, 'w') as fh:
        fh.write(json.dumps(conf))

# TODO: use theme
def load_theme(conf):
    theme_dir = os.path.split(conf['theme'])[0]
    try:
        with open(conf['theme']) as fh:
            theme = json.loads(fh.read())
    except Exception as e:
        print(e)
        return None

    theme_pix = {}
    for key in theme:
        filename = os.path.join(theme_dir, theme[key])
        if os.path.exists(filename):
            theme_pix[key] = GdkPixbuf.Pixbuf.new_from_file(filename)
        else:
            print('Failed to open theme icon', filename)
            return None
    return theme_pix
