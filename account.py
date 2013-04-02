#This file is part account_statement_of_account module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.
from decimal import Decimal
from trytond.tools import reduce_ids
from trytond.model import ModelView, ModelSQL, fields
from trytond.transaction import Transaction
from trytond.pool import Pool
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.pyson import PYSONEncoder

__all__ = ['Line', 'StatementOfAccountStart', 'StatementOfAccount']


class Line(ModelSQL, ModelView):
    __name__ = 'account.move.line'
    balance = fields.Function(fields.Numeric('Balance'), 'get_balance')

    @classmethod
    def _check_party_account_kind(cls, account_kind):
        return account_kind in ('payable', 'receivable')

    @classmethod
    def get_balance(cls, lines, name):
        if not lines:
            return {}
        ids = [x.id for x in lines]
        res = {}.fromkeys(ids, Decimal('0.0'))
        fiscalyear_id = Transaction().context.get(
            'statement_of_account_fiscalyear_id')
        default_check_party = Transaction().context.get(
            'statement_of_account_check_party')

        from_fiscalyear = ''
        where_fiscalyear = ''
        if fiscalyear_id:
            from_fiscalyear = '''
                LEFT JOIN account_period ap ON (ap.id=am.period)
                LEFT JOIN account_fiscalyear af ON (af.id=ap.fiscalyear)
                '''
            where_fiscalyear = '''
                ap.fiscalyear = %d AND
                ''' % fiscalyear_id

        cursor = Transaction().cursor
        for line in lines:
            id = line.id
            account_id = line.account.id
            party_id = line.party and line.party.id
            date = line.move.date
            number = line.move.number
            debit = line.debit or Decimal('0.0')
            credit = line.credit or Decimal('0.0')
            if default_check_party is None:
                check_party = cls._check_party_account_kind(line.account.kind)
            else:
                check_party = default_check_party

            # Order is a bit complex. In theory move lines should be sorted by
            # move.number but in some cases move will be in draft state and
            # thus move.number will be '/' It can also happen that users made
            # some mistakes and move.number may be recalculated at the end of
            # the current period or year. So here we consider users want this
            # sorted by date. In the same date, then then move.number is
            # considered and finally if they have the same value, they're sorted
            # by account_move_line.id just to ensure balance is not overlapped.

            # Of course, this filtering criteria must be the one used by the
            # 'search()' function below, so remember to modify that if you want
            # to change this calulation.

            cursor.execute("""
                SELECT
                    SUM(debit-credit)
                FROM
                    account_move am""" + from_fiscalyear + """,
                    account_move_line aml
                WHERE """ + where_fiscalyear + """
                    aml.move = am.id
                    AND aml.account = %s
                    AND (NOT %s OR aml.party = %s)
                    AND (
                        am.date < %s
                        OR (am.date = %s AND am.number < %s)
                        OR (am.date = %s AND am.number = %s
                            AND aml.id < %s)
                    )
                """, (account_id, check_party, party_id, date, date, number,
                    date, number, id))
            balance = cursor.fetchone()[0] or Decimal('0.0')
            # SQLite uses float for SUM
            if not isinstance(balance, Decimal):
                balance = Decimal(balance)
            # Add/substract current debit and credit
            balance += debit - credit
            res[id] = balance
        return res

    @classmethod
    def search(cls, args, offset=0, limit=None, order=None, count=False,
            query_string=False):
        """
        Override default search function so that if it's being called from the
        statement of accounts tree view, the given order is ignored and a
        special one is used so it ensures consistency between balance field
        value and account.move.line order.
        """
        lines = super(Line, cls).search(args, offset, limit, order,
            count, query_string)

        cursor = Transaction().cursor

        if Transaction().context.get('statement_of_account') and lines:
            # If it's a statement_of_account, ignore order given
            red_sql, red_ids = reduce_ids('aml.id', [x.id for x in lines])

            # This sorting criteria must be the one used by the 'balance'
            # functional field above, so remember to modify that if you
            # want to change the order.
            cursor.execute("""
                SELECT
                    aml.id
                FROM
                    account_move_line aml,
                    account_move am
                WHERE
                    aml.move = am.id AND
                """ + red_sql + """
                ORDER BY
                    am.date,
                    am.number,
                    aml.id
                """, red_ids)
            result = cursor.fetchall()
            ids = [x[0] for x in result]
            lines = cls.browse(ids)
        return lines


class StatementOfAccountStart(ModelView):
    'Statement of Account'
    __name__ = 'account.statement.of.account.start'
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
        required=True)
    account = fields.Many2One('account.account', 'Account',
        domain=[('type', '!=', 'view')], required=True)
    party = fields.Many2One('party.party', 'Party')

    @staticmethod
    def default_fiscalyear():
        FiscalYear = Pool().get('account.fiscalyear')
        return FiscalYear.find(Transaction().context.get('company'),
            exception=False)


class StatementOfAccount(Wizard):
    'Statement of Account'
    __name__ = 'account.statement.of.account'
    start = StateView('account.statement.of.account.start',
        'account_statement_of_account.account_statement_of_account_start_form',
        [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Open', 'open_', 'tryton-ok'),
            ])
    open_ = StateAction(
        'account_statement_of_account.act_statement_of_account_tree')

    def do_open_(self, action):
        name = (self.start.party and self.start.party.name
            or self.start.account.name)
        title = ''
        if self.start.account.code:
            title += '%s: ' % self.start.account.code
        title += name[:10]
        if len(name) > 10:
            title += '...'
        action['name'] = title

        domain = [('account', '=', self.start.account.id)]
        domain += [('period.fiscalyear', '=', self.start.fiscalyear.id)]
        if self.start.party:
            domain += [('party', '=', self.start.party.id)]
        action['pyson_domain'] = PYSONEncoder().encode(domain)

        action['pyson_context'] = PYSONEncoder().encode({
                'statement_of_account': True,
                'statement_of_account_check_party': bool(self.start.party),
                'statement_of_account_fiscalyear_id': self.start.fiscalyear.id,
                })
        return action, {}
