# This file is part of the account_statement_of_account module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import doctest
from decimal import Decimal
from trytond.pool import Pool
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.tests.test_tryton import doctest_teardown
from trytond.tests.test_tryton import doctest_checker
from trytond.transaction import Transaction

from trytond.modules.company.tests import create_company, set_company
from trytond.modules.account.tests import create_chart, get_fiscalyear


class AccountStatementOfAccountTestCase(ModuleTestCase):
    'Test Account Statement Of Account module'
    module = 'account_statement_of_account'

    @with_transaction()
    def test_account_debit_credit(self):
        'Test account debit/credit'
        pool = Pool()
        Party = pool.get('party.party')
        FiscalYear = pool.get('account.fiscalyear')
        Journal = pool.get('account.journal')
        Account = pool.get('account.account')
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        company = create_company()
        with set_company(company):
            create_chart(company)
            fiscalyear = get_fiscalyear(company)
            fiscalyear.save()
            FiscalYear.create_period([fiscalyear])
            period = fiscalyear.periods[0]
            party1, party2 = Party.create([{
                        'name': 'Customer 1',
                        }, {
                        'name': 'Customer 2',
                        }])
            journal_revenue, = Journal.search([
                    ('code', '=', 'REV'),
                    ])
            revenue, = Account.search([
                    ('kind', '=', 'revenue'),
                    ])
            receivable, = Account.search([
                    ('kind', '=', 'receivable'),
                    ])
            # Create some moves
            vlist = [
                {
                    'period': period.id,
                    'journal': journal_revenue.id,
                    'date': period.start_date,
                    'lines': [
                        ('create', [{
                                    'account': receivable.id,
                                    'debit': Decimal(10),
                                    'party': party1.id,
                                    }, {
                                    'account': revenue.id,
                                    'credit': Decimal(10),
                                    }]),
                        ],
                    },
                {
                    'period': period.id,
                    'journal': journal_revenue.id,
                    'date': period.start_date,
                    'lines': [
                        ('create', [{
                                    'account': receivable.id,
                                    'debit': Decimal(20),
                                    'party': party2.id,
                                    }, {
                                    'account': revenue.id,
                                    'credit': Decimal(20),
                                    }]),
                        ],
                    },
                {
                    'period': period.id,
                    'journal': journal_revenue.id,
                    'date': period.start_date,
                    'lines': [
                        ('create', [{
                                    'account': receivable.id,
                                    'debit': Decimal(30),
                                    'party': party1.id,
                                    }, {
                                    'account': revenue.id,
                                    'credit': Decimal(30),
                                    }]),
                        ],
                    },
                ]
            Move.create(vlist)

            # Default value for check_party
            with Transaction().set_context(statement_of_account=True,
                    statement_of_account_fiscalyear_id=fiscalyear.id):
                lines = MoveLine.search([
                        ('account', '=', receivable.id),
                        ])
            self.assertEqual(lines[0].balance, Decimal(40))
            self.assertEqual(lines[0].party, party1)
            self.assertEqual(lines[1].balance, Decimal(20))
            self.assertEqual(lines[1].party, party2)
            self.assertEqual(lines[2].balance, Decimal(10))
            self.assertEqual(lines[2].party, party1)

            # Override order
            with Transaction().set_context(statement_of_account=True,
                    statement_of_account_fiscalyear_id=fiscalyear.id):
                lines = MoveLine.search([
                        ('account', '=', receivable.id),
                        ],
                    order=[('date', 'ASC')])
            self.assertEqual(lines[0].balance, Decimal(10))
            self.assertEqual(lines[0].party, party1)
            self.assertEqual(lines[1].balance, Decimal(20))
            self.assertEqual(lines[1].party, party2)
            self.assertEqual(lines[2].balance, Decimal(40))
            self.assertEqual(lines[2].party, party1)

            # check_party == False
            with Transaction().set_context(statement_of_account=True,
                    statement_of_account_check_party=False,
                    statement_of_account_fiscalyear_id=fiscalyear.id):
                lines = MoveLine.search([
                        ('account', '=', receivable.id),
                        ])
            self.assertEqual(lines[0].balance, Decimal(60))
            self.assertEqual(lines[0].party, party1)
            self.assertEqual(lines[1].balance, Decimal(30))
            self.assertEqual(lines[1].party, party2)
            self.assertEqual(lines[2].balance, Decimal(10))
            self.assertEqual(lines[2].party, party1)

            # check_party == True
            with Transaction().set_context(statement_of_account=True,
                    statement_of_account_check_party=True,
                    statement_of_account_fiscalyear_id=fiscalyear.id):
                lines = MoveLine.search([
                        ('account', '=', receivable.id),
                        ])
            self.assertEqual(lines[0].balance, Decimal(40))
            self.assertEqual(lines[0].party, party1)
            self.assertEqual(lines[1].balance, Decimal(20))
            self.assertEqual(lines[1].party, party2)
            self.assertEqual(lines[2].balance, Decimal(10))
            self.assertEqual(lines[2].party, party1)


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AccountStatementOfAccountTestCase))
    suite.addTests(doctest.DocFileSuite(
            'scenario_statement_of_account.rst',
            tearDown=doctest_teardown, encoding='utf-8',
            checker=doctest_checker,
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite
