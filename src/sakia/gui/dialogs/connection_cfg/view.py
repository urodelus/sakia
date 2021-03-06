from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import pyqtSignal, Qt
from .connection_cfg_uic import Ui_ConnectionConfigurationDialog
from duniterpy.key import SigningKey, ScryptParams
from math import ceil, log
from ...widgets import toast
from ...widgets.dialogs import QAsyncMessageBox


class ConnectionConfigView(QDialog, Ui_ConnectionConfigurationDialog):
    """
    Connection config view
    """
    values_changed = pyqtSignal()

    def __init__(self, parent):
        """
        Constructor
        """
        super().__init__(parent)
        self.setupUi(self)
        self.edit_uid.textChanged.connect(self.values_changed)
        self.edit_password.textChanged.connect(self.values_changed)
        self.edit_password_repeat.textChanged.connect(self.values_changed)
        self.edit_salt.textChanged.connect(self.values_changed)
        self.button_generate.clicked.connect(self.action_show_pubkey)

        self.combo_scrypt_params.currentIndexChanged.connect(self.handle_combo_change)
        self.scrypt_params = ScryptParams(4096, 16, 1)
        self.spin_n.setMaximum(2 ** 20)
        self.spin_n.setValue(self.scrypt_params.N)
        self.spin_n.valueChanged.connect(self.handle_n_change)
        self.spin_r.setMaximum(128)
        self.spin_r.setValue(self.scrypt_params.r)
        self.spin_r.valueChanged.connect(self.handle_r_change)
        self.spin_p.setMaximum(128)
        self.spin_p.setValue(self.scrypt_params.p)
        self.spin_p.valueChanged.connect(self.handle_p_change)
        self.label_info.setTextFormat(Qt.RichText)

    def handle_combo_change(self, index):
        strengths = [
            (2 ** 12, 16, 1),
            (2 ** 14, 32, 2),
            (2 ** 16, 32, 4),
            (2 ** 18, 64, 8),
        ]
        self.spin_n.setValue(strengths[index][0])
        self.spin_r.setValue(strengths[index][1])
        self.spin_p.setValue(strengths[index][2])

    def handle_n_change(self, value):
        spinbox = self.sender()
        self.scrypt_params.N = ConnectionConfigView.compute_power_of_2(spinbox, value, self.scrypt_params.N)

    def handle_r_change(self, value):
        spinbox = self.sender()
        self.scrypt_params.r = ConnectionConfigView.compute_power_of_2(spinbox, value, self.scrypt_params.r)

    def handle_p_change(self, value):
        spinbox = self.sender()
        self.scrypt_params.p = ConnectionConfigView.compute_power_of_2(spinbox, value, self.scrypt_params.p)

    @staticmethod
    def compute_power_of_2(spinbox, value, param):
        if value > 1:
            if value > param:
                value = pow(2, ceil(log(value) / log(2)))
            else:
                value -= 1
                value = 2 ** int(log(value, 2))
        else:
            value = 1

        spinbox.blockSignals(True)
        spinbox.setValue(value)
        spinbox.blockSignals(False)

        return value

    def display_info(self, info):
        self.label_info.setText(info)

    def set_currency(self, currency):
        self.label_currency.setText(currency)

    def add_node_parameters(self):
        server = self.lineedit_add_address.text()
        port = self.spinbox_add_port.value()
        return server, port

    async def show_success(self, notification):
        if notification:
            toast.display(self.tr("UID broadcast"), self.tr("Identity broadcasted to the network"))
        else:
            await QAsyncMessageBox.information(self, self.tr("UID broadcast"),
                                               self.tr("Identity broadcasted to the network"))

    def show_error(self, notification, error_txt):
        if notification:
            toast.display(self.tr("UID broadcast"), error_txt)
        self.label_info.setText(self.tr("Error") + " " + error_txt)

    def set_nodes_model(self, model):
        self.tree_peers.setModel(model)

    def set_creation_layout(self, currency):
        """
        Hide unecessary buttons and display correct title
        """
        self.setWindowTitle(self.tr("New connection to {0} network").format(currency))

    def action_show_pubkey(self):
        salt = self.edit_salt.text()
        password = self.edit_password.text()
        pubkey = SigningKey(salt, password, self.scrypt_params).pubkey
        self.label_info.setText(pubkey)

    def account_name(self):
        return self.edit_account_name.text()

    def set_communities_list_model(self, model):
        """
        Set communities list model
        :param sakia.models.communities.CommunitiesListModel model:
        """
        self.list_communities.setModel(model)

    def stream_log(self, log):
        """
        Add log to
        :param str log:
        """
        self.plain_text_edit.insertPlainText("\n" + log)
