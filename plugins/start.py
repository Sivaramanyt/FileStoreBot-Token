import asyncio
import random
import string
import time

from pyrogram import filters, Client
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import Bot
from config import (
    VERIFY_EXPIRE,
    SHORTLINK_URL,
    SHORTLINK_API,
    CUSTOM_CAPTION,
    DISABLE_CHANNEL_BUTTON,
    PROTECT_CONTENT,
    START_MSG,
)
from helper_func import (
    decode,
    get_messages,
    get_shortlink,
    get_verify_status,
    update_verify_status,
    subscribed,
)
from database.database import (
    add_user,
    present_user,
    get_view_count,
    increment_view_count,
)

@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message):
    user_id = message.from_user.id

    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except Exception as e:
            print(f"Error adding user: {e}")

    verify_status = await get_verify_status(user_id)

    if verify_status['is_verified'] and VERIFY_EXPIRE < (time.time() - verify_status['verified_time']):
        await update_verify_status(user_id, is_verified=False)

    text = message.text

    if "verify_" in text:
        _, token = text.split("_", 1)
        if verify_status['verify_token'] != token:
            await message.reply("Your token is invalid or expired. Try again by clicking /start")
            return
        await update_verify_status(user_id, is_verified=True, verified_time=time.time())
        await message.reply("Your token is successfully verified and valid for 6 hours.")
        return

    if len(text) > 7:
        try:
            base64_str = text.split(" ", 1)[1]
        except Exception:
            return

        decoded_str = await decode(base64_str)
        argument = decoded_str.split("-")
        msg_ids = []

        try:
            if len(argument) == 3:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end = int(int(argument) / abs(client.db_channel.id))
                msg_ids = list(range(start, end + 1)) if start <= end else list(range(start, end - 1, -1))
            elif len(argument) == 2:
                msg_ids = [int(int(argument[1]) / abs(client.db_channel.id))]
        except Exception:
            return

        try:
            messages = await get_messages(client, msg_ids)
        except Exception:
            await message.reply("Something went wrong fetching the messages.")
            return

        view_count = await get_view_count(user_id)

        if view_count < 3:
            for msg in messages:
                caption = ""
                if bool(CUSTOM_CAPTION) and bool(msg.document):
                    caption = CUSTOM_CAPTION.format(
                        previouscaption="" if not msg.caption else msg.caption.html,
                        filename=msg.document.file_name,
                    )
                elif msg.caption:
                    caption = msg.caption.html

                reply_markup = None if DISABLE_CHANNEL_BUTTON else msg.reply_markup

                try:
                    await msg.copy(
                        chat_id=user_id,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup,
                        protect_content=PROTECT_CONTENT,
                    )
                    await asyncio.sleep(0.5)
                except Exception:
                    pass

            await increment_view_count(user_id)

        else:
            if verify_status['is_verified']:
                for msg in messages:
                    caption = ""
                    if bool(CUSTOM_CAPTION) and bool(msg.document):
                        caption = CUSTOM_CAPTION.format(
                            previouscaption="" if not msg.caption else msg.caption.html,
                            filename=msg.document.file_name,
                        )
                    elif msg.caption:
                        caption = msg.caption.html

                    reply_markup = None if DISABLE_CHANNEL_BUTTON else msg.reply_markup

                    try:
                        await msg.copy(
                            chat_id=user_id,
                            caption=caption,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup,
                            protect_content=PROTECT_CONTENT,
                        )
                        await asyncio.sleep(0.5)
                    except Exception:
                        pass

                await increment_view_count(user_id)

            else:
                token = "".join(random.choices(string.ascii_letters + string.digits, k=10))
                await update_verify_status(user_id, verify_token=token, is_verified=False, verified_time=0, link="")
                shortlink = await get_shortlink(
                    SHORTLINK_URL,
                    SHORTLINK_API,
                    f"https://telegram.dog/{client.username}?start=verify_{token}",
                )

                verification_text = (
                    "Hello my dear friend 👋\n\n"
                    "You have watched your free videos Today🥲. So you want watch more videos 💦 for Next 6 Hours 🤩\n\n"
                    "😎Please complete a quick ad verification💥\n\n"
                    "\"👇 Click the button below to verify, and check the tutorial if needed🤪!\""
                )

                btn = [
                    [InlineKeyboardButton("Click here to Verify", url=shortlink)],
                    [InlineKeyboardButton("How to Complete Verification", url="https://t.me/Sr_Movie_Links/52")]
                ]

                await message.reply(
                    verification_text,
                    reply_markup=InlineKeyboardMarkup(btn),
                    protect_content=False,
                )
        return

    if verify_status['is_verified']:
        reply_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("About Me", callback_data="about"),
                 InlineKeyboardButton("Close", callback_data="close")]
            ]
        )
        await message.reply_text(
            START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else "@" + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id,
            ),
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            quote=True,
        )
    else:
        token = "".join(random.choices(string.ascii_letters + string.digits, k=10))
        await update_verify_status(user_id, verify_token=token, is_verified=False, verified_time=0, link="")
        shortlink = await get_shortlink(
            SHORTLINK_URL,
            SHORTLINK_API,
            f"https://telegram.dog/{client.username}?start=verify_{token}",
        )
        btn = [[InlineKeyboardButton("Click here to Verify", url=shortlink)]]
        await message.reply(
            "Please verify to use this bot and access videos.",
            reply_markup=InlineKeyboardMarkup(btn),
            protect_content=False,
        )
        
