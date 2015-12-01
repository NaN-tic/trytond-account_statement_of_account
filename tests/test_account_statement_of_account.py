# This file is part of the account_statement_of_account module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase


class AccountStatementOfAccountTestCase(ModuleTestCase):
    'Test Account Statement Of Account module'
    module = 'account_statement_of_account'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AccountStatementOfAccountTestCase))
    return suite