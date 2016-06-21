"""
    requests-respectful

    A simple but powerful addon to the beloved requests library.
    Seamlessly respect service rate limits. Be a good Netizen.
    Keeps track of any amount of realms simultaneously. Split-second precision.

    :copyright: (c) 2016 by Nicholas Brochu.
    :license: Apache 2, see LICENSE for more details.
"""

__author__ = "Nicholas Brochu"
__version__ = "0.1.2"

from .respectful_requester import RespectfulRequester
from .exceptions import *
