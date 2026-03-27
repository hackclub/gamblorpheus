import random

from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.web.async_client import AsyncWebClient

from app.tables import Lottery
from app.tables import Ticket
from app.utils.logging import send_heartbeat


async def draw_lottery_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    channel: str,
):
    lotteries = await Lottery.select().where(Lottery.open == True)  # noqa: E712
    if len(lotteries) > 1:
        return await respond(
            "There are multiple open lotteries - please go into the database and fix this!"
        )
    if len(lotteries) == 0:
        return await respond(
            "There are no lotteries open, please start a lottery first :3"
        )

    lottery = lotteries[0]
    tickets = await Ticket.objects().where(Ticket.lottery == lottery["id"])

    winner: Ticket = random.choice(tickets)

    user = await winner.get_related(Ticket.user)

    await respond(
        f"<@{user.slack_id}> won! They earnt 🍪 {len(tickets) * 10}!\nhttps://flavortown.hackclub.com/admin/users/{user.ft_id}"
    )
    await send_heartbeat(
        f"<@{user.slack_id}> won! They earnt 🍪 {len(tickets) * 10}!\nhttps://flavortown.hackclub.com/admin/users/{user.ft_id}"
    )

    return await Lottery.update({Lottery.open: False, Lottery.winner: user.id}).where(
        Lottery.open == True  # noqa: E712
    )
