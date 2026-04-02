from slack_bolt.async_app import AsyncAck
from slack_bolt.async_app import AsyncRespond
from slack_sdk.web.async_client import AsyncWebClient

from app.tables import Lottery
from app.tables import Ticket
from app.tables import User
from app.utils.logging import send_heartbeat


async def add_ticket_handler(
    ack: AsyncAck,
    client: AsyncWebClient,
    respond: AsyncRespond,
    performer: str,
    channel: str,
    order: str,
):
    from app.config import config
    from app.env import env

    await ack()
    lottery = await Lottery.objects().where(Lottery.open == True).first()  # noqa: E712
    if not lottery:
        return await respond("No currently running lottery!")
    headers = {"Authorization": f"Bearer {config.flavortown_api_key}"}
    async with env.http.get(
        f"https://flavortown.hackclub.com/api/v1/admin/shop_orders/order?order_id={order}",
        headers=headers,
    ) as res:
        data = await res.json()
        quantity = data.get("quantity", 1)
        user_id = data.get("user_id")
        item_id = data.get("shop_item_id")
        aasm_state = data.get("aasm_state")
        if item_id != 200:
            return await respond("That's not a lottery order!")
        if aasm_state != "awaiting_periodical_fulfillment":
            return await respond(
                f"Woah there, you can't fulfill that, it's {aasm_state}!"
            )

    user = await User.objects().where(User.ft_id == user_id).first()
    slack_id = ""
    if not user:
        async with env.http.get(
            f"https://flavortown.hackclub.com/api/v1/users/{user_id}", headers=headers
        ) as res:
            user_data = await res.json()
            slack_id = user_data.get("slack_id")
        user = User(ft_id=user_id, slack_id=slack_id)
        await user.save()

    tickets = [
        Ticket(lottery=lottery, order_id=int(order), user=user) for _ in range(quantity)
    ]
    tkts = await Ticket.insert(*tickets)
    ids = [str(tkt["id"]) for tkt in tkts]

    cookies = lottery.cookies + (9 * quantity)
    await Lottery.update({Lottery.cookies: cookies}).where(Lottery.open == True)  # noqa: E712

    ref = "Ticket #:" + ",".join(ids)
    async with env.http.post(
        f"https://flavortown.hackclub.com/api/v1/admin/shop_orders/fulfill?order_id={order}",
        headers=headers,
        data={"external_ref": ref, "fulfillment_cost": 0},
    ) as fulfill_res:
        if fulfill_res.status != 200:
            json = await fulfill_res.json()
            await send_heartbeat(
                f"Something went wrong processing #{order} - status {fulfill_res.status}",
                messages=[f"```{json}```"],
            )
            return await respond("Something went wrong!")

    await send_heartbeat(f"Issued {quantity} tickets to <@{slack_id}>.", messages=[ref])
    return await respond(f"Issued {quantity} tickets to <@{slack_id}>.")
