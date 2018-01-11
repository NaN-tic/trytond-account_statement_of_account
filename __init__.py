# This file is part account_statement_of_account module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import account


def register():
    Pool.register(
        account.Line,
        account.StatementOfAccountStart,
        module='account_statement_of_account', type_='model')
    Pool.register(
        account.StatementOfAccount,
        account.ReceivableStatementOfAccount,
        account.PayableStatementOfAccount,
        module='account_statement_of_account', type_='wizard')
