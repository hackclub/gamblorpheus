import logging

from app.config import config
from app.env import env
from app.tables import Lottery
from app.tables import Ticket
from app.tables import User
from app.utils.logging import send_heartbeat

logger = logging.getLogger(__name__)


async def auto_fulfill():
    logger.info("Starting auto-fulfillment task")

    # Only fulfill if there's an open lottery
    lottery = await Lottery.objects().where(Lottery.open == True).first()  # noqa: E712
    if not lottery:
        logger.info("No open lottery found, skipping auto-fulfillment")
        return

    headers = {"Authorization": f"Bearer {config.flavortown_api_key}"}

    try:
        # Polling orders awaiting periodical fulfillment for item 200
        url = "https://flavortown.hackclub.com/api/v1/admin/shop_orders?shop_item_id=200&aasm_state=awaiting_periodical_fulfillment"
        async with env.http.get(url, headers=headers) as res:
            if res.status != 200:
                logger.error(f"Failed to fetch orders: {res.status}")
                return

            orders = await res.json()
            if not orders:
                logger.debug("No orders found to fulfill")
                return

            for order in orders:
                order_id = order.get("id")
                if not order_id:
                    continue

                # Double check state and item_id just in case, though the URL filters them
                if (
                    order.get("shop_item_id") != 200
                    or order.get("aasm_state") != "awaiting_periodical_fulfillment"
                ):
                    continue

                # Check if already processed to avoid duplicates
                existing_ticket = (
                    await Ticket.objects()
                    .where(Ticket.order_id == int(order_id))
                    .first()
                )
                if existing_ticket:
                    logger.debug(f"Order {order_id} already has tickets, skipping")
                    continue

                quantity = order.get("quantity", 1)
                user_id = order.get("user_id")

                try:
                    user = await User.objects().where(User.ft_id == user_id).first()
                    slack_id = ""
                    if not user:
                        async with env.http.get(
                            f"https://flavortown.hackclub.com/api/v1/users/{user_id}",
                            headers=headers,
                        ) as user_res:
                            if user_res.status == 200:
                                user_data = await user_res.json()
                                slack_id = user_data.get("slack_id")
                                user = User(ft_id=user_id, slack_id=slack_id)
                                await user.save()
                            else:
                                logger.error(
                                    f"Failed to fetch user {user_id}: {user_res.status}"
                                )
                                continue
                    else:
                        slack_id = user.slack_id

                    # Create tickets
                    tickets = [
                        Ticket(lottery=lottery, order_id=int(order_id), user=user)
                        for _ in range(quantity)
                    ]
                    tkts = await Ticket.insert(*tickets)
                    ids = [str(tkt["id"]) for tkt in tkts]

                    # Update lottery cookies (matching add_ticket.py logic: 9 cookies per quantity)
                    new_cookies = lottery.cookies + (9 * quantity)
                    await Lottery.update({Lottery.cookies: new_cookies}).where(
                        Lottery.id == lottery.id
                    )
                    # Update local object so subsequent orders in this loop see the updated count
                    lottery.cookies = new_cookies

                    ref = "Ticket #:" + ",".join(ids)
                    # Fulfill on Flavortown
                    fulfill_url = f"https://flavortown.hackclub.com/api/v1/admin/shop_orders/fulfill?order_id={order_id}"
                    async with env.http.post(
                        fulfill_url,
                        headers=headers,
                        data={"external_ref": ref, "fulfillment_cost": 0},
                    ) as fulfill_res:
                        if fulfill_res.status != 200:
                            json_err = await fulfill_res.json()
                            await send_heartbeat(
                                f"Something went wrong auto-fulfilling #{order_id} - status {fulfill_res.status}",
                                messages=[f"```{json_err}```"],
                            )
                            continue

                    await send_heartbeat(
                        f"Auto-fulfilled {quantity} tickets for <@{slack_id}>.",
                        messages=[ref],
                    )
                    logger.info(f"Auto-fulfilled order {order_id} for user {user_id}")
                except Exception as e:
                    logger.error(f"Error processing order {order_id}: {e}")
                    continue

    except Exception as e:
        logger.exception(f"Error in auto_fulfill task: {e}")
