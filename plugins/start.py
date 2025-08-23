import asyncio
import logging
import random
import time

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import Bot
from config import ADMINS, IS_VERIFY, VERIFY_EXPIRE, SHORTLINK_API, SHORTLINK_URL, DISABLE_CHANNEL_BUTTON, CUSTOM_CAPTION, PROTECT_CONTENT, START_MSG
from helper_func import subscribed, decode, get_messages, get_shortlink, get_verify_status, update_verify_status
from database.database import add_user, present_user, get_user_video_count, increment_user_video_count, user_data

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_handler(client: Client, message):
    user_id = message.from_user.id

    # Log types and values for debugging
    logger.debug(f"user_id: {user_id} type: {type(user_id)}")
    logger.debug(f"ADMINS: {ADMINS} types: {[type(a) for a in ADMINS]}")

    # Ensure correct admin check with matching types by casting both to str for safety
    is_admin = str(user_id) in [str(admin) for admin in ADMINS]
    logger.debug(f"is admin: {is_admin}")

    if is_admin:
        await message.reply("Hello Owner! Your bot is running smoothly.")
        return

    # New user addition
    if not await present_user(user_id):
        await add_user(user_id)

    verify_status = await get_verify_status(user_id)
    # Reset verification if expired
    if verify_status['is_verified'] and VERIFY_EXPIRE < (time.time() - verify_status['verified_time']):
        await update_verify_status(user_id, is_verified=False)
        verify_status['is_verified'] = False

    video_count = await get_user_video_count(user_id)
    logger.debug(f"User {user_id} video_count: {video_count}")
    logger.debug(f"User {user_id} verified status: {verify_status['is_verified']}")

    allow_video = False
    if video_count < 3:
        allow_video = True
    elif verify_status['is_verified']:
        allow_video = True

    if allow_video:
        try:
            base64_string = message.text.split(" ", 1)[1]
        except Exception:
            base64_string = None

        if base64_string:
            _string = await decode(base64_string)
            argument = _string.split("-")

            if len(argument) == 3:
                try:
                    start = int(int(argument[1]) / abs(client.db_channel.id))
                    end = int(int(argument) / abs(client.db_channel.id))
                except Exception as e:
                    logger.error(f"Invalid argument numbers: {e}")
                    return
                ids = range(start, end + 1) if start <= end else range(start, end - 1, -1)
            elif len(argument) == 2:
                try:
                    ids = [int(int(argument[1]) / abs(client.db_channel.id))]
                except Exception as e:
                    logger.error(f"Invalid argument single number: {e}")
                    return
            else:
                ids = []

            temp_msg = await message.reply("Please wait...")

            try:
                messages = await get_messages(client, ids)
            except Exception as e:
                logger.error(f"Error fetching messages: {e}")
                await message.reply_text("Something went wrong..!")
                return

            await temp_msg.delete()

            for msg in messages:
                if CUSTOM_CAPTION and msg.document:
                    caption = CUSTOM_CAPTION.format(previouscaption="" if not msg.caption else msg.caption.html, filename=msg.document.file_name)
                else:
                    caption = "" if not msg.caption else msg.caption.html

                reply_markup = None if DISABLE_CHANNEL_BUTTON else msg.reply_markup

                try:
                    await msg.copy(chat_id=user_id, caption=caption, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"Error sending message: {e}")

            if video_count < 3:
                await increment_user_video_count(user_id)
                logger.debug(f"Incremented video count for {user_id}")
        else:
            await message.reply_text("Please provide valid video ID arguments.")
    else:
        if IS_VERIFY:
            token = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
            await update_verify_status(user_id, verify_token=token, link="")
            link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://telegram.dog/{client.username}?start=verify_{token}')
            btn = [
                [InlineKeyboardButton("Click here to verify", url=link)],
                [InlineKeyboardButton('How to use the bot', url='https://t.me/neprosz/3')]
            ]
            await message.reply(
                "You reached the free limit of 3 videos.\nPlease verify to continue.",
                reply_markup=InlineKeyboardMarkup(btn)
            )
        else:
            await message.reply_text("Verification is currently disabled.")

@Bot.on_message(filters.command('reset') & filters.private)
async def reset_handler(client: Client, message):
    user_id = message.from_user.id
    try:
        await update_verify_status(user_id, verify_token="", is_verified=False, verified_time=0, link="")
        await user_data.update_one({'_id': user_id}, {'$set': {'video_count': 0}})
        await message.reply("Your video count and verification status have been reset.")
        logger.info(f"Data reset for user {user_id}")
    except Exception as e:
        logger.error(f"Reset failed for user {user_id}: {e}")
        await message.reply("An error occurred while resetting your data.")

# You can keep generic handler below to handle other messages if needed
                                
