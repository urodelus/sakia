import attr
from duniterpy.documents import block_uid
from duniterpy.documents.transaction import reduce_base
import math


def parse_transaction_doc(tx_doc, pubkey, block_number, mediantime, txid):
    """
    Parse a transaction
    :param duniterpy.documents.Transaction tx_doc: The tx json data
    :param str pubkey: The pubkey of the transaction to parse, to know if its a receiver or issuer
    :param int block_number: The block number where we found the tx
    :param int mediantime: Median time on the network
    :param int txid: The latest txid
    :return: the found transaction
    """
    receivers = [o.conditions.left.pubkey for o in tx_doc.outputs
                 if o.conditions.left.pubkey != tx_doc.issuers[0]]

    if len(receivers) == 0:
        receivers = [tx_doc.issuers[0]]

    in_issuers = len([i for i in tx_doc.issuers
                      if i == pubkey]) > 0
    in_outputs = len([o for o in tx_doc.outputs
                      if o.conditions.left.pubkey == pubkey]) > 0

    if in_issuers or in_outputs:
        # If the wallet pubkey is in the issuers we sent this transaction
        if in_issuers:
            outputs = [o for o in tx_doc.outputs
                       if o.conditions.left.pubkey != pubkey]
            amount = 0
            for o in outputs:
                amount += o.amount * math.pow(10, o.base)
        # If we are not in the issuers,
        # maybe we are in the recipients of this transaction
        else:
            outputs = [o for o in tx_doc.outputs
                       if o.conditions.left.pubkey == pubkey]
        amount = 0
        for o in outputs:
            amount += o.amount * math.pow(10, o.base)
        amount, amount_base = reduce_base(amount, 0)

        transaction = Transaction(currency=tx_doc.currency,
                                  sha_hash=tx_doc.sha_hash,
                                  written_block=block_number,
                                  blockstamp=tx_doc.blockstamp,
                                  timestamp=mediantime,
                                  signature=tx_doc.signatures[0],
                                  issuer=tx_doc.issuers[0],
                                  receiver=receivers[0],
                                  amount=amount,
                                  amount_base=amount_base,
                                  comment=tx_doc.comment,
                                  txid=txid,
                                  state=Transaction.VALIDATED)
        return transaction
    return None

@attr.s()
class Transaction:

    TO_SEND = 0
    AWAITING = 1
    VALIDATING = 2
    VALIDATED = 4
    REFUSED = 8
    DROPPED = 16
    LOCAL = 128

    currency = attr.ib(convert=str, cmp=False)
    sha_hash = attr.ib(convert=str)
    written_block = attr.ib(convert=int, cmp=False)
    blockstamp = attr.ib(convert=block_uid, cmp=False)
    timestamp = attr.ib(convert=int, cmp=False)
    signature = attr.ib(convert=str, cmp=False)
    issuer = attr.ib(convert=str, cmp=False)
    receiver = attr.ib(convert=str, cmp=False)
    amount = attr.ib(convert=int, cmp=False)
    amount_base = attr.ib(convert=int, cmp=False)
    comment = attr.ib(convert=str, cmp=False)
    txid = attr.ib(convert=int, cmp=False)
    state = attr.ib(convert=int, cmp=False)

    @property
    def local(self):
        return self.state & Transaction.LOCAL == Transaction.LOCAL