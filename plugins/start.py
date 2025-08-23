import asyncio
import base64
import logging
import os
import random
import re
import string
import time

from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import Bot
from config import (
    ADMINS,
    FORCE_MSG,
    START_MSG,
    CUSTOM_CAPTION,
    IS_VERIFY,
    VERIFY_EXPIRE,
    SHORTLINK_API,
    SHORTLINK_URL,
    DISABLE_CHANNEL_BUTTON,
    PROTECT_CONTENT,
    TUT_VID,
    OWNER_ID,
)
from helper_func import subscribed, encode, decode, get_messages, get_shortlink, get_verify_status, update_verify_status, get_exp_time
from database.database import add_user, del_user, full_userbase, present_user, get_user_video_count, increment_user_video_count, user_data, db_update_verify_status
from shortzy import Shortzy

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    try:
        logger.debug(f"Received /start from user {user_id}")

        if user_id in ADMINS:
            await message.reply("Hello Owner! Your bot is running smoothly.")
            return

        if not await present_user(user_id):
            try:
                await add_user(user_id)
            except Exception as e:
                logger.error(f"Error adding user {user_id}: {e}")

        verify_status = await get_verify_status(user_id)

        if verify_status['is_verified'] and VERIFY_EXPIRE < (time.time() - verify_status['verified_time']):
            await update_verify_status(user_id, is_verified=False)
            verify_status['is_verified'] = False  # update local copy

        video_count = await get_user_video_count(user_id)
        logger.debug(f"User {user_id} video_count: {video_count}")
        logger.debug(f"User {user_id} verified status: {verify_status['is_verified']}")

        if video_count < 3:
            allow_video = True
        elif verify_status['is_verified']:
            allow_video = True
        else:
            allow_video = False

        if allow_video:
            try:
                base64_string = message.text.split(" ", 1)[1]
            except:
                base64_string = None

            if base64_string:
                _string = await decode(base64_string)
                argument = _string.split("-")

                if len(argument) == 3:
                    try:
                        start = int(int(argument[1]) / abs(client.db_channel.id))
                        end = int(int(argument) / abs(client.db_channel.id))
                    except Exception as exc:
                        logger.error(f"Invalid argument numbers from user {user_id}: {exc}")
                        return
                    ids = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))
                elif len(argument) == 2:
                    try:
                        ids = [int(int(argument[1]) / abs(client.db_channel.id))]
                    except Exception as exc:
                        logger.error(f"Invalid argument single number from user {user_id}: {exc}")
                        return
                else:
                    ids = []

                temp_msg = await message.reply("Please wait...")

                try:
                    messages = await get_messages(client, ids)
                except Exception as exc:
                    logger.error(f"Error fetching messages for user {user_id}: {exc}")
                    await message.reply_text("Something went wrong..!")
                    return

                await temp_msg.delete()

                for msg in messages:
                    caption = ""
                    if CUSTOM_CAPTION and msg.document:
                        caption = CUSTOM_CAPTION.format(previouscaption="" if not msg.caption else msg.caption.html, filename=msg.document.file_name)
                    elif msg.caption:
                        caption = msg.caption.html

                    reply_markup = None if DISABLE_CHANNEL_BUTTON else msg.reply_markup

                    try:
                        await msg.copy(chat_id=user_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                        await asyncio.sleep(0.5)
                    except FloodWait as e:
                        logger.warning(f"FloodWait for user {user_id}, sleeping for {e.x} seconds")
                        await asyncio.sleep(e.x)
                        await msg.copy(chat_id=user_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                    except Exception as exc:
                        logger.error(f"Error copying message to user {user_id}: {exc}")

                if video_count < 3:
                    await increment_user_video_count(user_id)
                    logger.debug(f"Incremented video count for user {user_id}")
            else:
                await message.reply_text("Please send a valid command with encoded video ID.")
        else:
            if IS_VERIFY:
                token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                await update_verify_status(user_id, verify_token=token, link="")
                link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://telegram.dog/{client.username}?start=verify_{token}')
                btn = [
                    [InlineKeyboardButton("Click here to verify", url=link)],
                    [InlineKeyboardButton('How to use the bot', url=f"https://t.me/neprosz/3")]
                ]
                await message.reply(
                    "You have reached the free limit of 3 videos.\nPlease complete the shortlink verification to continue watching.",
                    reply_markup=InlineKeyboardMarkup(btn),
                    protect_content=False,
                    quote=True
                )
            else:
                await message.reply_text("Access denied. Please verify to continue.")

    except Exception as e:
        logger.error(f"Unhandled exception in start_handler for user {user_id}: {e}", exc_info=True)

@Bot.on_message(filters.command('reset') & filters.private)
async def reset_handler(client: Client, message: Message):
    user_id = message.from_user.id
    try:
        await update_verify_status(user_id, verify_token="", is_verified=False, verified_time=0, link="")
        await user_data.update_one({'_id': user_id}, {'$set': {'video_count': 0}})
        await message.reply("Your video count and verification status have been reset.")
        logger.info(f"Reset data for user {user_id}")
    except Exception as e:
        logger.error(f"Error resetting data for user {user_id}: {e}", exc_info=True)
        await message.reply("An error occurred while resetting your data. Please try again later.")

# Generic handler - reply with sharable link only for non-commands
@Bot.on_message(filters.private & ~filters.command(["start", "reset"]))
async def generic_handler(client: Client, message: Message):
    # Example: send the sharable link here
    share_link = "https://t.me/your_bot_username"
    await message.reply(f"Here is your shareable link: {share_link}")
            
                
