# This file is part of the account_statement_of_account module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import doctest
from decimal import Decimal
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase
from trytond.tests.test_tryton import doctest_setup, doctest_teardown
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction


class AccountStatementOfAccountTestCase(ModuleTestCase):
    'Test Account Statement Of Account module'
    module = 'account_statement_of_account'

    def setUp(self):
        super(AccountStatementOfAccountTestCase, self).setUp()
        self.account_template = POOL.get('account.account.template')
        self.account = POOL.get('account.account')
        self.account_create_chart = POOL.get(
            'account.create_chart', type='wizard')
        self.company = POOL.get('company.company')
        self.user = POOL.get('res.user')
        self.fiscalyear = POOL.get('account.fiscalyear')
        self.sequence = POOL.get('ir.sequence')
        self.move = POOL.get('account.move')
        self.move_line = POOL.get('account.move.line')
        self.journal = POOL.get('account.journal')
        self.account_type = POOL.get('account.account.type')
        self.party = POOL.get('party.party')

    def test0030account_debit_credit(self):
        'Test account debit/credit'
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            party1, party2 = self.party.create([{
                        'name': 'Customer 1',
                        }, {
                        'name': 'Customer 2',
                        }])
            fiscalyear, = self.fiscalyear.search([])
            period = fiscalyear.periods[0]
            journal_revenue, = self.journal.search([
                    ('code', '=', 'REV'),
                    ])
            revenue, = self.account.search([
                    ('kind', '=', 'revenue'),
                    ])
            receivable, = self.account.search([
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
            self.move.create(vlist)

            # Default value for check_party
            with Transaction().set_context(statement_of_account=True,
                    statement_of_account_fiscalyear_id=fiscalyear.id):
                lines = self.move_line.search([
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
                lines = self.move_line.search([
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
                lines = self.move_line.search([
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
                lines = self.move_line.search([
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
            setUp=doctest_setup, tearDown=doctest_teardown, encoding='utf-8',
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite
