# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
try:
    from trytond.modules.account_statement_of_account.tests.test_account_statement_of_account import suite
except ImportError:
    from .test_account_statement_of_account import suite

__all__ = ['suite']
