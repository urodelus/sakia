from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QTimer
from cutecoin.core.net.api import bma as qtbma
from .identity import Identity

import asyncio


class IdentitiesRegistry:
    def __init__(self, instances={}):
        pass

    def load_json(self, json_data):
        pass

    def jsonify(self):
        return {'registry': []}

    def lookup(self, pubkey, community):
        identity = Identity.empty(pubkey)
        return identity

    @asyncio.coroutine
    def future_lookup(self, pubkey, community):
        identity = Identity.empty(pubkey)
        yield from asyncio.sleep(1)
        return identity

    def from_metadata(self, metadata):
        return Identity()