"""Lightweight and dynamic MPlayer wrapper with a Pythonic API

Classes:

Player -- provides a clean, Pythonic interface to MPlayer
CmdPrefix -- contains the prefixes that can be used with MPlayer commands
Step -- use with property access to implement the 'step_property' command

AsyncPlayer -- Player subclass with asyncore integration (POSIX only)
GeventPlayer -- Player subclass with gevent integration


Constants:

PIPE -- subprocess.PIPE, provided here for convenience
STDOUT -- subprocess.STDOUT, provided here for convenience
"""

__version__ = '0.1.0'
__author__ = 'LiuLang <gsushzhsosgsu@gmail.com>'
__old_author__ = 'Darwin M. Bautista <djclue917@gmail.com>'
__all__ = [
    'PIPE',
    'STDOUT',
    'Player',
    'CmdPrefix',
    'Step'
    ]

# Import here for convenience.
from subprocess import PIPE, STDOUT
from mplayer.core import Player, Step
from mplayer.misc import CmdPrefix
