"""
Created on 24 févr. 2015

@author: inso
"""
from cutecoin.core.net.node import Node

import logging
import statistics
import time
import asyncio
from ucoinpy.documents.peer import Peer
from ucoinpy.documents.block import Block

from ...tools.decorators import asyncify

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QTimer
from collections import Counter


class Network(QObject):
    """
    A network is managing nodes polling and crawling of a
    given community.
    """
    nodes_changed = pyqtSignal()
    new_block_mined = pyqtSignal(int)
    blockchain_rollback = pyqtSignal(int)

    def __init__(self, currency, nodes):
        """
        Constructor of a network

        :param str currency: The currency name of the community
        :param list nodes: The root nodes of the network
        """
        super().__init__()
        self._root_nodes = nodes
        self._nodes = []
        for n in nodes:
            self.add_node(n)
        self.currency = currency
        self._must_crawl = False
        self._refresh_block_found()
        self._timer = QTimer()

    @classmethod
    def create(cls, node):
        """
        Create a new network with one knew node
        Crawls the nodes from the first node to build the
        community network

        :param node: The first knew node of the network
        """
        nodes = [node]
        network = cls(node.currency, nodes)
        return network

    def merge_with_json(self, json_data):
        """
        We merge with knew nodes when we
        last stopped cutecoin

        :param dict json_data: Nodes in json format
        """
        for data in json_data:
            node = Node.from_json(self.currency, data)
            if node.pubkey not in [n.pubkey for n in self.nodes]:
                self.add_node(node)
                logging.debug("Loading : {:}".format(data['pubkey']))
            else:
                other_node = [n for n in self.nodes if n.pubkey == node.pubkey][0]
                other_node._uid = node.uid
                other_node._version = node.version
                other_node._software = node.software
                switch = False
                if other_node.block and node.block:
                    if other_node.block['hash'] != node.block['hash']:
                        switch = True
                else:
                    switch = True
                if switch:
                    other_node.set_block(node.block)
                    other_node.last_change = node.last_change
                    other_node.state = node.state

    @classmethod
    def from_json(cls, currency, json_data):
        """
        Load a network from a configured community

        :param str currency: The currency name of a community
        :param dict json_data: A json_data view of a network
        """
        nodes = []
        for data in json_data:
            node = Node.from_json(currency, data)
            nodes.append(node)
        network = cls(currency, nodes)
        # We block the signals until loading the nodes cache
        return network

    def jsonify(self):
        """
        Get the network in json format.

        :return: The network as a dict in json format.
        """
        data = []
        for node in self.nodes:
            data.append(node.jsonify())
        return data

    @property
    def quality(self):
        """
        Get a ratio of the synced nodes vs the rest
        """
        synced = len(self.synced_nodes)
        total = len(self.nodes)
        ratio_synced = synced / total
        return ratio_synced

    def start_coroutines(self):
        """
        Start network nodes crawling
        :return:
        """
        asyncio.async(self.discover_network())

    def stop_coroutines(self):
        """
        Stop network nodes crawling.
        """
        self._must_crawl = False

    def continue_crawling(self):
        return self._must_crawl

    @property
    def synced_nodes(self):
        """
        Get nodes which are in the ONLINE state.
        """
        return [n for n in self.nodes if n.state == Node.ONLINE]

    @property
    def online_nodes(self):
        """
        Get nodes which are in the ONLINE state.
        """
        return [n for n in self.nodes if n.state in (Node.ONLINE, Node.DESYNCED)]

    @property
    def nodes(self):
        """
        Get all knew nodes.
        """
        return self._nodes

    @property
    def root_nodes(self):
        """
        Get root nodes.
        """
        return self._root_nodes

    @property
    def latest_block_number(self):
        """
        Get the latest block considered valid
        It is the most frequent last block of every known nodes
        """
        blocks_numbers = [n.block['number'] for n in self.synced_nodes if n.block]
        if len(blocks_numbers) > 0:
            return blocks_numbers[0]
        else:
            return None

    @property
    def latest_block_hash(self):
        """
        Get the latest block considered valid
        It is the most frequent last block of every known nodes
        """
        blocks_hash = [n.block['hash'] for n in self.synced_nodes if n.block]
        if len(blocks_hash) > 0:
            return blocks_hash[0]
        else:
            return Block.Empty_Hash

    def _refresh_block_found(self):
        self._block_found = {'hash': self.latest_block_hash,
                             'number': self.latest_block_number}

    def check_nodes_sync(self):
        """
        Check nodes sync with the following rules :
        1 : The block of the majority
        2 : The more last different issuers
        3 : The more difficulty
        4 : The biggest number or timestamp
        """
        # rule number 1 : block of the majority
        blocks = [n.block['hash'] for n in self.online_nodes if n.block]
        blocks_occurences = Counter(blocks)
        blocks_by_occurences = {}
        for key, value in blocks_occurences.items():
            the_block = [n.block for n in self.online_nodes if n.block and n.block['hash'] == key][0]
            if value not in blocks_by_occurences:
                blocks_by_occurences[value] = [the_block]
            else:
                blocks_by_occurences[value].append(the_block)

        if len(blocks_by_occurences) == 0:
            for n in [n for n in self.online_nodes if n.state in (Node.ONLINE, Node.DESYNCED)]:
                n.state = Node.ONLINE
            return

        most_present = max(blocks_by_occurences.keys())

        if len(blocks_by_occurences[most_present]) > 1:
            # rule number 2 : more last different issuers
            # not possible atm
            blocks_by_issuers = blocks_by_occurences.copy()
            most_issuers = max(blocks_by_issuers.keys())
            if len(blocks_by_issuers[most_issuers]) > 1:
                # rule number 3 : biggest PowMin
                blocks_by_powmin = {}
                for block in blocks_by_issuers[most_issuers]:
                    if block['powMin'] in blocks_by_powmin:
                        blocks_by_powmin[block['powMin']].append(block)
                    else:
                        blocks_by_powmin[block['powMin']] = [block]
                bigger_powmin = max(blocks_by_powmin.keys())
                if len(blocks_by_powmin[bigger_powmin]) > 1:
                    # rule number 3 : latest timestamp
                    blocks_by_ts = {}
                    for block in blocks_by_powmin[bigger_powmin]:
                        blocks_by_ts[block['time']] = block
                    latest_ts = max(blocks_by_ts.keys())
                    synced_block_hash = blocks_by_ts[latest_ts]['hash']
                else:
                    synced_block_hash = blocks_by_powmin[bigger_powmin][0]['hash']
            else:
                synced_block_hash = blocks_by_issuers[most_issuers][0]['hash']
        else:
            synced_block_hash = blocks_by_occurences[most_present][0]['hash']

        for n in self.online_nodes:
            if n.block and n.block['hash'] == synced_block_hash:
                n.state = Node.ONLINE
            else:
                n.state = Node.DESYNCED

    def fork_window(self, members_pubkeys):
        """
        Get the medium of the fork window of the nodes members of a community
        :return: the medium fork window of knew network
        """
        fork_windows = [n.fork_window for n in self.online_nodes if n.software != ""
                                  and n.pubkey in members_pubkeys]
        if len(fork_windows) > 0:
            return int(statistics.median(fork_windows))
        else:
            return 0

    def add_node(self, node):
        """
        Add a nod to the network.
        """
        self._nodes.append(node)
        node.changed.connect(self.handle_change)
        node.neighbour_found.connect(self.handle_new_node)
        logging.debug("{:} connected".format(node.pubkey[:5]))

    def add_root_node(self, node):
        """
        Add a node to the root nodes list
        """
        self._root_nodes.append(node)

    def remove_root_node(self, index):
        """
        Remove a node from the root nodes list
        """
        self._root_nodes.pop(index)

    def is_root_node(self, node):
        """
        Check if this node is in the root nodes
        """
        return node in self._root_nodes

    def root_node_index(self, index):
        """
        Get the index of a root node from its index
        in all nodes list
        """
        node = self.nodes[index]
        return self._root_nodes.index(node)

    def refresh_once(self):
        for node in self._nodes:
            node.refresh()

    @asyncio.coroutine
    def discover_network(self):
        """
        Start crawling which never stops.
        To stop this crawling, call "stop_crawling" method.
        """
        self._must_crawl = True
        while self.continue_crawling():
            for node in self.nodes:
                if self.continue_crawling():
                    node.refresh()
                    yield from asyncio.sleep(15)
        logging.debug("End of network discovery")

    @pyqtSlot(Peer, str)
    def handle_new_node(self, peer, pubkey):
        pubkeys = [n.pubkey for n in self.nodes]
        if peer.pubkey not in pubkeys:
            logging.debug("New node found : {0}".format(peer.pubkey[:5]))
            node = Node.from_peer(self.currency, peer, pubkey)
            self.add_node(node)
            self.nodes_changed.emit()

    @pyqtSlot()
    def handle_change(self):
        node = self.sender()
        if node.state in (Node.ONLINE, Node.DESYNCED):
            self.check_nodes_sync()
        else:
            if node.last_change + 3600 < time.time():
                node.disconnect()
                self.nodes.remove(node)

        self.nodes_changed.emit()
        if node.state == Node.ONLINE:
            logging.debug("{0} -> {1}".format(self._block_found['hash'][:10], self.latest_block_hash[:10]))
            if self._block_found['hash'] != self.latest_block_hash:
                logging.debug("Latest block changed : {0}".format(self.latest_block_number))
                # If new latest block is lower than the previously found one
                # or if the previously found block is different locally
                # than in the main chain, we declare a rollback
                if self._block_found['number'] and \
                    self.latest_block_number <= self._block_found['number'] \
                    or node.main_chain_previous_block and \
                        node.main_chain_previous_block['hash'] != self._block_found['hash']:
                    self._refresh_block_found()
                    self.blockchain_rollback.emit(self.latest_block_number)
                else:
                    self._refresh_block_found()
                    self.new_block_mined.emit(self.latest_block_number)
