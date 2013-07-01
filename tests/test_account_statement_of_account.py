#!/usr/bin/env python
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

import sys
import os
DIR = os.path.abspath(os.path.normpath(os.path.join(__file__,
    '..', '..', '..', '..', '..', 'trytond')))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))

import unittest
import doctest
import datetime
from decimal import Decimal
import trytond.tests.test_tryton
from trytond.tests.test_tryton import test_view, test_depends
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.backend.sqlite.database import Database as SQLiteDatabase
from trytond.transaction import Transaction


class AccountStatementOfAccountTestCase(unittest.TestCase):
    '''
    Test AccountStatementOfAccount module.
    '''

    def setUp(self):
        trytond.tests.test_tryton.install_module(
            'account_statement_of_account')
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

    def test0005views(self):
        '''
        Test views.
        '''
        test_view('account_statement_of_account')

    def test0006depends(self):
        '''
        Test depends.
        '''
        test_depends()

    def test0030account_debit_credit(self):
        '''
        Test account debit/credit.
        '''
        with Transaction().start(DB_NAME, USER,
                context=CONTEXT) as transaction:

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
            self.assertEqual(lines[0].balance, Decimal(10))
            self.assertEqual(lines[0].party, party1)
            self.assertEqual(lines[1].balance, Decimal(30))
            self.assertEqual(lines[1].party, party2)
            self.assertEqual(lines[2].balance, Decimal(60))
            self.assertEqual(lines[2].party, party1)

            # check_party == True
            with Transaction().set_context(statement_of_account=True,
                    statement_of_account_check_party=True,
                    statement_of_account_fiscalyear_id=fiscalyear.id):
                lines = self.move_line.search([
                        ('account', '=', receivable.id),
                        ])
            self.assertEqual(lines[0].balance, Decimal(10))
            self.assertEqual(lines[0].party, party1)
            self.assertEqual(lines[1].balance, Decimal(20))
            self.assertEqual(lines[1].party, party2)
            self.assertEqual(lines[2].balance, Decimal(40))
            self.assertEqual(lines[2].party, party1)

            transaction.cursor.rollback()

def doctest_dropdb(test):
    '''
    Remove sqlite memory database
    '''
    database = SQLiteDatabase().connect()
    cursor = database.cursor(autocommit=True)
    try:
        database.drop(cursor, ':memory:')
        cursor.commit()
    finally:
        cursor.close()


def suite():
    suite = trytond.tests.test_tryton.suite()
    from trytond.modules.company.tests import test_company
    for test in test_company.suite():
        if test not in suite:
            suite.addTest(test)
    from trytond.modules.account.tests import test_account
    for test in test_account.suite():
        if test not in suite and not isinstance(test, doctest.DocTestCase):
            suite.addTest(test)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AccountStatementOfAccountTestCase))
    suite.addTests(doctest.DocFileSuite(
            'scenario_statement_of_account.rst',
            setUp=doctest_dropdb, tearDown=doctest_dropdb, encoding='utf-8',
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
