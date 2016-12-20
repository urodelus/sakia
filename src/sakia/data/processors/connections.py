import attr
import sqlite3
import logging


@attr.s
class ConnectionsProcessor:
    _connections_repo = attr.ib()  # :type sakia.data.repositories.ConnectionsRepo
    _logger = attr.ib(default=attr.Factory(lambda: logging.getLogger('sakia')))

    @classmethod
    def instanciate(cls, app):
        """
        Instanciate a blockchain processor
        :param sakia.app.Application app: the app
        """
        return cls(app.db.connections_repo)

    def commit_connection(self, connection):
        """
        Saves a connection state in the db
        :param sakia.data.entities.Connection connection: the connection updated
        """
        try:
            self._connections_repo.insert(connection)
        except sqlite3.IntegrityError:
            self._connections_repo.update(connection)

    def pubkeys(self):
        return self._connections_repo.get_pubkeys()

    def connections(self, currency):
        return self._connections_repo.get_all(currency=currency)

    def currencies(self):
        return self._connections_repo.get_currencies()