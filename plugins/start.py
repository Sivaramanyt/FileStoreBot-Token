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
from database.database import add_user, del_user, full_userbase, present_user, get_user_video_count, increment_user_video_count
from shortzy import Shortzy

@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    owner_id = ADMINS  # Your Admin list from config

    # Owner-specific logic (optional)
    if user_id == owner_id:
        await message.reply("You are the owner! Additional actions can be added here.")
        return

    # Add user if not present
    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except:
            pass

    # Verify status & expiry check
    verify_status = await get_verify_status(user_id)
    if verify_status['is_verified'] and VERIFY_EXPIRE < (time.time() - verify_status['verified_time']):
        await update_verify_status(user_id, is_verified=False)

    # Token verification flow
    if "verify_" in message.text:
        _, token = message.text.split("_", 1)
        if verify_status['verify_token'] != token:
            return await message.reply("Your token is invalid or Expired. Try again by clicking /start")
        await update_verify_status(user_id, is_verified=True, verified_time=time.time())
        await message.reply(f"Your token successfully verified and valid for: 24 Hour", protect_content=False, quote=True)
        return

    # Check user's video access count
    video_count = await get_user_video_count(user_id)

    if video_count < 3:
        # User gets free video access

        # Your existing logic to parse and send messages/videos below
        try:
            base64_string = message.text.split(" ", 1)[1]
        except:
            base64_string = None

        if base64_string:
            _string = await decode(base64_string)
            argument = _string.split("-")

            # Your existing logic for getting message ids to send (keep unchanged)
            if len(argument) == 3:
                try:
                    start = int(int(argument[1]) / abs(client.db_channel.id))
                    end = int(int(argument[11]) / abs(client.db_channel.id))
                except:
                    return
                if start <= end:
                    ids = range(start, end+1)
                else:
                    ids = []
                    i = start
                    while True:
                        ids.append(i)
                        i -= 1
                        if i < end:
                            break
            elif len(argument) == 2:
                try:
                    ids = [int(int(argument[1]) / abs(client.db_channel.id))]
                except:
                    return
            else:
                ids = []

            temp_msg = await message.reply("Please wait...")

            try:
                messages = await get_messages(client, ids)
            except:
                await message.reply_text("Something went wrong..!")
                return

            await temp_msg.delete()

            # Send messages/videos, apply captions and buttons as per your config
            for msg in messages:
                if bool(CUSTOM_CAPTION) and bool(msg.document):
                    caption = CUSTOM_CAPTION.format(previouscaption="" if not msg.caption else msg.caption.html, filename=msg.document.file_name)
                else:
                    caption = "" if not msg.caption else msg.caption.html

                reply_markup = None if DISABLE_CHANNEL_BUTTON else msg.reply_markup

                try:
                    await msg.copy(chat_id=user_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                    await asyncio.sleep(0.5)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    await msg.copy(chat_id=user_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                except:
                    pass

            # Increment user's video count after sending free videos
            await increment_user_video_count(user_id)
            return

    else:
        # Require shortlink verification for 4th+ video access
        if not verify_status['is_verified'] and IS_VERIFY:
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
            return

    # Other existing /start command flow here (e.g., send welcome message or about info)
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("About Me", callback_data="about"),
          InlineKeyboardButton("Close", callback_data="close")]]
    )
    await message.reply_text(
        text=START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=None if not message.from_user.username else '@' + message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=reply_markup,
        disable_web_page_preview=True,
        quote=True
            )
                    
