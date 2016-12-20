from PyQt5.QtCore import QObject
from .table_model import HistoryTableModel, TxFilterProxyModel
from PyQt5.QtCore import Qt, QDateTime, QTime, pyqtSignal, QModelIndex
from sakia.errors import NoPeerAvailable
from duniterpy.api import errors

import logging


class TxHistoryModel(QObject):
    """
    The model of Navigation component
    """
    def __init__(self, parent, app, connection, blockchain_service, identities_service,
                 transactions_service, sources_service):
        """

        :param sakia.gui.txhistory.TxHistoryParent parent: the parent controller
        :param sakia.app.Application app: the app
        :param sakia.data.entities.Connection connection: the connection
        :param sakia.services.BlockchainService blockchain_service: the blockchain service
        :param sakia.services.IdentitiesService identities_service: the identities service
        :param sakia.services.TransactionsService transactions_service: the identities service
        :param sakia.services.SourcesService sources_service: the sources service
        """
        super().__init__(parent)
        self.app = app
        self.connection = connection
        self.blockchain_service = blockchain_service
        self.identities_service = identities_service
        self.transactions_service = transactions_service
        self.sources_service = sources_service
        self._model = None
        self._proxy = None

    def init_history_table_model(self, ts_from, ts_to):
        """
        Generates a history table model
        :param int ts_from: date from where to filter tx
        :param int ts_to: date to where to filter tx
        :return:
        """
        self._model = HistoryTableModel(self, self.app, self.connection,
                                        self.identities_service, self.transactions_service)
        self._proxy = TxFilterProxyModel(self, ts_from, ts_to, self.blockchain_service)
        self._proxy.setSourceModel(self._model)
        self._proxy.setDynamicSortFilter(True)
        self._proxy.setSortRole(Qt.DisplayRole)
        self._model.refresh_transfers()

        return self._proxy

    async def table_data(self, index):
        """
        Gets available table data at given index
        :param index:
        :return: tuple containing (Identity, Transfer)
        """
        if index.isValid() and index.row() < self.table_model.rowCount(QModelIndex()):
            source_index = self.table_model.mapToSource(index)

            pubkey_col = self.table_model.sourceModel().columns_types.index('pubkey')
            pubkey_index = self.table_model.sourceModel().index(source_index.row(), pubkey_col)
            pubkey = self.table_model.sourceModel().data(pubkey_index, Qt.DisplayRole)

            identity = await self.app.identities_registry.future_find(pubkey, self.community)

            transfer = self.table_model.sourceModel().transfers()[source_index.row()]
            return True, identity, transfer
        return False, None, None

    def minimum_maximum_datetime(self):
        """
        Get minimum and maximum datetime
        :rtype: Tuple[PyQt5.QtCore.QDateTime, PyQt5.QtCore.QDateTime]
        :return: minimum and maximum datetime
        """
        minimum_datetime = QDateTime()
        minimum_datetime.setTime_t(0)
        tomorrow_datetime = QDateTime().currentDateTime().addDays(1)
        return minimum_datetime, tomorrow_datetime

    async def received_amount(self, received_list):
        """
        Converts a list of transactions to an amount
        :param list received_list:
        :return: the amount, localized
        """
        amount = 0
        for r in received_list:
            amount += r.metadata['amount']
        localized_amount = await self.app.current_ref.instance(amount, self.connection.currency, self.app) \
            .localized(units=True, international_system=self.app.parameters.international_system_of_units)
        return localized_amount

    def localized_balance(self):
        """
        Get the localized amount of the given tx history
        :return: the localized amount of given account in given community
        :rtype: int
        """
        try:
            amount = self.sources_service.amount(self.connection.pubkey)
            localized_amount = self.app.current_ref.instance(amount, self.connection.currency, self.app)\
                .localized(units=True, international_system=self.app.parameters.international_system_of_units)
            return localized_amount
        except NoPeerAvailable as e:
            logging.debug(str(e))
        except errors.DuniterError as e:
            logging.debug(str(e))
        return self.tr("Loading...")

    @property
    def table_model(self):
        return self._proxy

    def notifications(self):
        return self.app.parameters.notifications