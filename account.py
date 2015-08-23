#This file is part account_statement_of_account module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from sql.aggregate import Sum
from sql import Column
from decimal import Decimal
from trytond.model import ModelView, ModelSQL, fields
from trytond.transaction import Transaction
from trytond.pool import Pool
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.pyson import If, Bool, Eval, PYSONEncoder

__all__ = ['Line', 'StatementOfAccountStart', 'StatementOfAccount',
    'ReceivableStatementOfAccount', 'PayableStatementOfAccount']


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
        pool = Pool()
        Move = pool.get('account.move')
        Line = pool.get('account.move.line')

        ids = [x.id for x in lines]
        res = {}.fromkeys(ids, Decimal('0.0'))
        fiscalyear_id = Transaction().context.get(
            'statement_of_account_fiscalyear_id')
        default_check_party = Transaction().context.get(
            'statement_of_account_check_party')

        cursor = Transaction().cursor
        for line in lines:
            id = line.id
            account_id = line.account.id
            party = line.party.id if line.party else None
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
            # sorted by date. In the same date, then move.number is
            # considered and finally if they have the same value, they're sorted
            # by account_move_line.id just to ensure balance is not overlapped.

            # Of course, this filtering criteria must be the one used by the
            # 'order_move()' function below, so remember to modify that if you
            # want to change this calulation.

            move = Move.__table__()
            line = Line.__table__()
            columns = [Sum(line.debit - line.credit)]
            table = move
            where = line.account == account_id

            table = table.join(line, condition=move.id == line.move)

            if check_party:
                where &= line.party == party

            where &= ((move.date < date)
                | ((move.date == date) & (move.number < number))
                | ((move.date == date) & (move.number == number)
                    & (move.id < id)))

            # remove current line from query
            where &= line.id != id
            cursor.execute(*table.select(*columns, where=where))
            record = cursor.fetchone()
            balance = Decimal('0.0')
            if record and record[0]:
                balance = record[0]
            # SQLite uses float for SUM
            if not isinstance(balance, Decimal):
                balance = Decimal(balance)
            # Add/substract current debit and credit
            balance += debit - credit
            res[id] = balance
        return res

    @staticmethod
    def order_move(tables):
        pool = Pool()
        Move = pool.get('account.move')
        Line = pool.get('account.move.line')

        if not Transaction().context.get('statement_of_account'):
            # TODO: This code is almost copy & pasted from
            # fields.Many2One.convert_order function because
            # if that function is called we get an infinite recursion
            # error, due to the check at the very beginning of that
            # function which will call this one again. We should
            # probably split that core function in two.
            field = Line._fields['move']
            Target = field.get_target()
            oname = 'id'
            if Target._rec_name in Target._fields:
                oname = Target._rec_name
            if Target._order_name in Target._fields:
                oname = Target._order_name

            ofield = Target._fields[oname]
            table, _ = tables[None]
            target_tables = tables.get('move')
            if target_tables is None:
                target = Target.__table__()
                target_tables = {
                    None: (target, target.id == Column(table, 'move')),
                    }
                tables['move'] = target_tables
            return ofield.convert_order(oname, target_tables, Target)

        table, _ = tables[None]
        date = Move._fields['date']
        number = Move._fields['number']
        move = Move.__table__()
        move_tables = {
            None: (move, move.id == table.move),
            }
        tables['move'] = move_tables
        return (date.convert_order('date', move_tables, Move) +
            number.convert_order('number', move_tables, Move) + [table.id])

    @classmethod
    def search(cls, args, offset=0, limit=None, order=None, count=False,
            query=False):
        """
        Override default search function so that if it's being called from the
        statement of accounts tree view, the given order is ignored and a
        special one is used so it ensures consistency between balance field
        value and account.move.line order.
        """
        if order is None:
            order = []
        order = list(order)
        if Transaction().context.get('statement_of_account'):
            descending = True
            for x in order:
                if x[0] == 'date' and x[1].upper() == 'ASC':
                    descending = False
            # If it's a statement_of_account, ignore order given
            order = [('move', 'DESC' if descending else 'ASC')]
        return super(Line, cls).search(args, offset, limit, order, count,
            query)


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

    @staticmethod
    def default_account():
        model = Transaction().context.get('active_model')
        if model == 'account.account':
            return Transaction().context.get('active_id')
        return None

    @staticmethod
    def default_party():
        model = Transaction().context.get('active_model')
        if model == 'party.party':
            return Transaction().context.get('active_id')
        return None


class StatementOfAccount(Wizard):
    'Statement of Account'
    __name__ = 'account.statement.of.account'
    start = StateView('account.statement.of.account.start',
        'account_statement_of_account.account_statement_of_account_start_form',
        [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Open', 'open_', 'tryton-ok', default=True),
            ])
    open_ = StateAction(
        'account_statement_of_account.act_statement_of_account_tree')

    def do_open_(self, action):
        name = (self.start.party and self.start.party.name
            or self.start.account.name)
        title = ''
        if self.start.account.code:
            title += '%s: ' % self.start.account.code
        title += name
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


class ReceivableStatementOfAccount(StatementOfAccount):
    'Receivable Statement Of Account'
    __name__ = 'account.statement.of.account.receivable'

    def default_start(self, fields):
        Party = Pool().get('party.party')
        party = Party(Transaction().context.get('active_id'))
        return {
            'account': (party.account_receivable.id if party.account_receivable
                else None),
            }


class PayableStatementOfAccount(StatementOfAccount):
    'Payable Statement Of Account'
    __name__ = 'account.statement.of.account.payable'

    def default_start(self, fields):
        Party = Pool().get('party.party')
        party = Party(Transaction().context.get('active_id'))
        return {
            'account': (party.account_payable.id if party.account_payable
                else None),
            }
