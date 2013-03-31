Account Statement of Account Module
###################################

This module adds a new menu entry that allows showing all move lines of a given
account (optionally filtered by party). Most important thing is that it adds the
*Balance* field which shows the accumulated account balance for that move line.

If user chooses to filter by party, the accumulated account balance only takes
into account move lines with the given party and account. If no party is given,
the balance takes into account all move lines of the given account.
