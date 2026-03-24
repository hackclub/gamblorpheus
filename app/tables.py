# An example of how to create a table. Read the docs for more info: https://piccolo-orm.readthedocs.io/
from piccolo.columns import Boolean
from piccolo.columns import ForeignKey
from piccolo.columns import Integer
from piccolo.columns import Timestamptz
from piccolo.columns import Varchar
from piccolo.table import Table


class Lottery(Table):
    name = Varchar(unique=True)
    cookies = Integer()
    open = Boolean(default=True)
    winner = ForeignKey("User", null=True)
    created_at = Timestamptz()


class User(Table):
    ft_id = Integer(index=True, unique=True)
    slack_id = Varchar(unique=True)
    created_at = Timestamptz()


class Ticket(Table):
    lottery = ForeignKey(Lottery)
    order_id = Integer()
    user = ForeignKey(User)
    created_at = Timestamptz()
