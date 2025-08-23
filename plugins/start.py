import asyncio
import random
import string
import time

from pyrogram import filters, Client
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import Bot
from config import (
    ADMINS,
    VERIFY_EXPIRE,
    SHORTLINK_API,
    SHORTLINK_URL,
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

    # Add user if new
    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except:
            pass

    verify_status = await get_verify_status(user_id)
    # Expire verification if expired
    if verify_status['is_verified'] and VERIFY_EXPIRE < (time.time() - verify_status['verified_time']):
        await update_verify_status(user_id, is_verified=False)

    text = message.text

    # Verification token submit handler
    if "verify_" in text:
        _, token = text.split("_", 1)
        if verify_status['verify_token'] != token:
            return await message.reply("Your token is invalid or expired. Try again by clicking /start")
        await update_verify_status(user_id, is_verified=True, verified_time=time.time())
        await message.reply("Your token is successfully verified and valid for 24 hours.")
        return

    # Handling start with video link parameter
    if len(text) > 7:
        try:
            base64_str = text.split(" ", 1)[1]
        except:
            return

        _string = await decode(base64_str)
        argument = _string.split("-")
        msg_ids = []

        try:
            if len(argument) == 3:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end = int(int(argument[9]) / abs(client.db_channel.id))
                msg_ids = list(range(start, end + 1)) if start <= end else list(range(start, end - 1, -1))
            elif len(argument) == 2:
                msg_ids = [int(int(argument[1]) / abs(client.db_channel.id))]
        except:
            return

        try:
            messages = await get_messages(client, msg_ids)
        except:
            await message.reply("Something went wrong fetching the messages.")
            return

        # Get user's video view count
        view_count = await get_view_count(user_id)

        if view_count < 3:
            # User within free limit, allow access without verification
            for msg in messages:
                caption = CUSTOM_CAPTION.format(
                    previouscaption="" if not msg.caption else msg.caption.html,
                    filename=msg.document.file_name if msg.document else ""
                ) if bool(CUSTOM_CAPTION) and bool(msg.document) else "" if not msg.caption else msg.caption.html

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
            # User at or above free limit, require verification
            if verify_status['is_verified']:
                # Verified user, allow
                for msg in messages:
                    caption = CUSTOM_CAPTION.format(
                        previouscaption="" if not msg.caption else msg.caption.html,
                        filename=msg.document.file_name if msg.document else ""
                    ) if bool(CUSTOM_CAPTION) and bool(msg.document) else "" if not msg.caption else msg.caption.html

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
                # Not verified, show verification link
                token = "".join(random.choices(string.ascii_letters + string.digits, k=10))
                await update_verify_status(user_id, verify_token=token, is_verified=False, verified_time=0, link="")
                shortlink = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f"https://telegram.dog/{client.username}?start=verify_{token}")
                btn = [[InlineKeyboardButton("Click here to Verify", url=shortlink)]]
                await message.reply(
                    "You have reached the free view limit.\nPlease verify to access more videos.",
                    reply_markup=InlineKeyboardMarkup(btn),
                    protect_content=False,
                )
        return

    # If no video parameter, show greeting or verification as appropriate
    if verify_status['is_verified']:
        reply_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("About Me", callback_data="about"), InlineKeyboardButton("Close", callback_data="close")]
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
        shortlink = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f"https://telegram.dog/{client.username}?start=verify_{token}")
        btn = [[InlineKeyboardButton("Click here to Verify", url=shortlink)]]
        await message.reply(
            "Please verify to use this bot and access videos.",
            reply_markup=InlineKeyboardMarkup(btn),
            protect_content=False,
        )
        
            
