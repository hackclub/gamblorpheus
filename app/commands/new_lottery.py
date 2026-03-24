from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.web.async_client import AsyncWebClient

from app.tables import Lottery


async def new_lottery_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    channel: str,
    name: str,
):
    await ack()

    lottery = await Lottery.objects().where(Lottery.open == True)  # noqa: E712
    if lottery:
        return await respond("There's a lottery currently running!")

    lottery = Lottery(name=name)
    await Lottery.insert(lottery)

    return await respond("Lottery created!")
