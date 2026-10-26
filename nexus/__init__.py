"""
Nexus: Record and replay Playwright navigation on blockchain (IPFS).

A tool for recording web navigation sequences via Playwright and storing
the waypoints immutably on IPFS via Pinata API.
"""

__version__ = '0.1.0'
__author__ = 'Hyperlog'
__author_email__ = 'nattimmis@gmail.com'
__license__ = 'Apache 2.0'

from nexus.waypoint import Waypoint, WaypointAction, WaypointAssertion
from nexus.recorder import NavigationRecorder
from nexus.blockchain import IPFSBlockchain
from nexus.playback import NavigationPlayback

__all__ = [
    'Waypoint',
    'WaypointAction',
    'WaypointAssertion',
    'NavigationRecorder',
    'IPFSBlockchain',
    'NavigationPlayback',
]
