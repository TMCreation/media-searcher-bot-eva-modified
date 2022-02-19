import os
import logging
import random
import asyncio
from Script import script
from pyrogram import Client, filters
from pyrogram.errors import ChatAdminRequired, FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.ia_filterdb import Media, get_file_details, unpack_new_file_id
from database.users_chats_db import db
from info import CHANNELS, ADMINS, AUTH_CHANNEL, LOG_CHANNEL, PICS, BATCH_FILE_CAPTION, CUSTOM_FILE_CAPTION
from utils import get_size, is_subscribed, temp
import re
import json
import base64
logger = logging.getLogger(__name__)

BATCH_FILES = {}

@Client.on_message(filters.command("start") & filters.incoming & ~filters.edited)
async def start(client, message):
    if message.chat.type in ['group', 'supergroup']:
        buttons = [
            [
                InlineKeyboardButton('🤖 Updates', url='https://t.me/cinehub_family')
            ],
            [
                InlineKeyboardButton('ℹ️ Help', url=f"https://t.me/{temp.U_NAME}?start=help"),
            ]
            ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply(script.START_TXT.format(message.from_user.mention if message.from_user else message.chat.title, temp.U_NAME, temp.B_NAME), reply_markup=reply_markup)
        await asyncio.sleep(2) # 😢 https://github.com/EvamariaTG/EvaMaria/blob/master/plugins/p_ttishow.py#L17 😬 wait a bit, before checking.
        if not await db.get_chat(message.chat.id):
            total=await client.get_chat_members_count(message.chat.id)
            await client.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(message.chat.title, message.chat.id, total, "Unknown"))       
            await db.add_chat(message.chat.id, message.chat.title)
        return 
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention))
    if len(message.command) != 2:
        buttons = [[
            InlineKeyboardButton('📥 ɢᴏ ɪɴʟɪɴᴇ', switch_inline_query=''),
            InlineKeyboardButton('📽 🄲🄸🄽🄴🄷🅄🄱', url='https://t.me/cinehub_family')
            ],[
            InlineKeyboardButton('💡 ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('📕 ᴀʙᴏᴜᴛ', callback_data='about')
            ],[
            InlineKeyboardButton('🎬 ᴄʟɪᴄᴋ ᴛᴏ sᴇᴀʀᴄʜ සිංහල උපසිරැසි', switch_inline_query_current_chat='')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode='html'
        )
        return
    if AUTH_CHANNEL and not await is_subscribed(client, message):
        try:
            invite_link = await client.create_chat_invite_link(int(AUTH_CHANNEL))
        except ChatAdminRequired:
            logger.error("Make sure Bot is admin in Forcesub channel")
            return
        btn = [
            [
                InlineKeyboardButton(
                    "🤖 Join Updates Channel", url=invite_link.invite_link
                )
            ]
        ]

        if message.command[1] != "subscribe":
            btn.append([InlineKeyboardButton(" 🔄 Try Again", callback_data=f"checksub#{message.command[1]}")])
        await client.send_message(
            chat_id=message.from_user.id,
            text="**Please Join My Updates Channel to use this Bot!**",
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode="markdown"
            )
        return
    if len(message.command) ==2 and message.command[1] in ["subscribe", "error", "okay", "help"]:
        buttons = [[
            InlineKeyboardButton('📥 ɢᴏ ɪɴʟɪɴᴇ', switch_inline_query=''),
            InlineKeyboardButton('📽 🄲🄸🄽🄴🄷🅄🄱', url='https://t.me/cinehub_family')
            ],[
            InlineKeyboardButton('💡 ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('📕 ᴀʙᴏᴜᴛ', callback_data='about')
            ],[
            InlineKeyboardButton('🎬 ᴄʟɪᴄᴋ ᴛᴏ sᴇᴀʀᴄʜ සිංහල උපසිරැසි', switch_inline_query_current_chat='')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode='html'
        )
        return
    file_id = message.command[1]
    if file_id.split("-", 1)[0] == "BATCH":
        sts = await message.reply("Please wait")
        file_id = file_id.split("-", 1)[1]
        msgs = BATCH_FILES.get(file_id)
        if not msgs:
            file = await client.download_media(file_id)
            try: 
                with open(file) as file_data:
                    msgs=json.loads(file_data.read())
            except:
                await sts.edit("FAILED")
                return await client.send_message(LOG_CHANNEL, "UNABLE TO OPEN FILE.")
            os.remove(file)
            BATCH_FILES[file_id] = msgs
        for msg in msgs:
            title = msg.get("title")
            size=get_size(int(msg.get("size", 0)))
            f_caption=msg.get("caption", "")
            if BATCH_FILE_CAPTION:
                try:
                    f_caption=BATCH_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                except Exception as e:
                    logger.exception(e)
                    f_caption=f_caption
            if f_caption is None:
                f_caption = f"{title}"
            try:
                await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    )
            except FloodWait as e:
                await asyncio.sleep(e.x)
                logger.warning(f"Floodwait of {e.x} sec.")
                await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    )
            except Exception as e:
                logger.warning(e, exc_info=True)
                continue
            await asyncio.sleep(1) 
        await sts.delete()
        return
    elif file_id.split("-", 1)[0] == "DSTORE":
        sts = await message.reply("Please wait")
        b_string = file_id.split("-", 1)[1]
        decoded = (base64.urlsafe_b64decode(b_string + "=" * (-len(b_string) % 4))).decode("ascii")
        f_msg_id, l_msg_id, f_chat_id = decoded.split("_", 2)
        msgs_list = list(range(int(f_msg_id), int(l_msg_id)+1))
        for msg in msgs_list:
            try:
                await client.copy_message(chat_id=message.chat.id, from_chat_id=int(f_chat_id), message_id=msg)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await client.copy_message(chat_id=message.chat.id, from_chat_id=int(f_chat_id), message_id=msg)
            except Exception as e:
                logger.exception(e)
                continue
            await asyncio.sleep(1) 
        return await sts.delete()

    files_ = await get_file_details(file_id)           
    if not files_:
        try:
            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file_id
                )
            filetype = msg.media
            file = getattr(msg, filetype)
            title = file.file_name
            size=get_size(file.file_size)
            f_caption = f"<code>{title}</code>"
            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='')
                except:
                    return
            await msg.edit_caption(f_caption)
            return
        except:
            pass
        return await message.reply('No such file exist.')
    files = files_[0]
    title = files.file_name
    size=get_size(files.file_size)
    f_caption=files.caption
    if CUSTOM_FILE_CAPTION:
        try:
            f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
        except Exception as e:
            logger.exception(e)
            f_caption=f_caption
    if f_caption is None:
        f_caption = f"{files.file_name}"
    await client.send_cached_media(
        chat_id=message.from_user.id,
        file_id=file_id,
        caption=f_caption,
        )
                    

@Client.on_message(filters.command('channel') & filters.user(ADMINS))
async def channel_info(bot, message):
           
    """Send basic information of channel"""
    if isinstance(CHANNELS, (int, str)):
        channels = [CHANNELS]
    elif isinstance(CHANNELS, list):
        channels = CHANNELS
    else:
        raise ValueError("Unexpected type of CHANNELS")

    text = '📑 **Indexed channels/groups**\n'
    for channel in channels:
        chat = await bot.get_chat(channel)
        if chat.username:
            text += '\n@' + chat.username
        else:
            text += '\n' + chat.title or chat.first_name

    text += f'\n\n**Total:** {len(CHANNELS)}'

    if len(text) < 4096:
        await message.reply(text)
    else:
        file = 'Indexed channels.txt'
        with open(file, 'w') as f:
            f.write(text)
        await message.reply_document(file)
        os.remove(file)


@Client.on_message(filters.command('logs') & filters.user(ADMINS))
async def log_file(bot, message):
    """Send log file"""
    try:
        await message.reply_document('TelegramBot.log')
    except Exception as e:
        await message.reply(str(e))

@Client.on_message(filters.command('delete') & filters.user(ADMINS))
async def delete(bot, message):
    """Delete file from database"""
    reply = message.reply_to_message
    if reply and reply.media:
        msg = await message.reply("Processing...⏳", quote=True)
    else:
        await message.reply('Reply to file with /delete which you want to delete', quote=True)
        return

    for file_type in ("document", "video", "audio"):
        media = getattr(reply, file_type, None)
        if media is not None:
            break
    else:
        await msg.edit('This is not supported file format')
        return
    
    file_id, file_ref = unpack_new_file_id(media.file_id)

    result = await Media.collection.delete_one({
        '_id': file_id,
    })
    if result.deleted_count:
        await msg.edit('File is successfully deleted from database')
    else:
        file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
        result = await Media.collection.delete_one({
            'file_name': file_name,
            'file_size': media.file_size,
            'mime_type': media.mime_type
            })
        if result.deleted_count:
            await msg.edit('File is successfully deleted from database')
        else:
            # files indexed before https://github.com/EvamariaTG/EvaMaria/commit/f3d2a1bcb155faf44178e5d7a685a1b533e714bf#diff-86b613edf1748372103e94cacff3b578b36b698ef9c16817bb98fe9ef22fb669R39 
            # have original file name.
            result = await Media.collection.delete_one({
                'file_name': media.file_name,
                'file_size': media.file_size,
                'mime_type': media.mime_type
            })
            if result.deleted_count:
                await msg.edit('File is successfully deleted from database')
            else:
                await msg.edit('File not found in database')


@Client.on_message(filters.command('deleteall') & filters.user(ADMINS))
async def delete_all_index(bot, message):
    await message.reply_text(
        'This will delete all indexed files.\nDo you want to continue??',
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="YES", callback_data="autofilter_delete"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="CANCEL", callback_data="close_data"
                    )
                ],
            ]
        ),
        quote=True,
    )


@Client.on_callback_query(filters.regex(r'^autofilter_delete'))
async def delete_all_index_confirm(bot, message):
    await Media.collection.drop()
    await message.answer()
    await message.message.edit('Succesfully Deleted All The Indexed Files.')

@Client.on_message(filters.command('help'))
async def go(bot, message):
    if len(message.command) > 1 and message.command[1] == 'subscribe':
        await message.reply("<a href='https://telegra.ph/%CA%9C%E1%B4%87%CA%9F%E1%B4%98-11-16'>Tutorial Video of 🄲🄸🄽🄴🄷🅄🄱 ᴍᴇᴅɪᴀ sᴇᴀʀᴄʜᴇʀ ʙᴏᴛ</a> ", quote=True)
    else:
        buttons = [[
        InlineKeyboardButton("🏠 Mαιη Mєηυ ", callback_data='start'),
        InlineKeyboardButton("📚 ᴛᴜᴛᴏʀɪᴀʟ ᴠɪᴅᴇᴏ", url="https://telegra.ph/ʜᴇʟᴘ-11-16")
        ],[
        InlineKeyboardButton("🅢🅗🅐🅡🅔 & 🅢🅤🅟🅟🅞🅡🅣", url="https://telegram.me/share/url?url=https://t.me/sub_searcher_bot"),
        ],[
        InlineKeyboardButton("🎬 ᴄʟɪᴄᴋ ᴛᴏ sᴇᴀʀᴄʜ සිංහල උපසිරැසි", switch_inline_query_current_chat=''),
    ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply("📌 ѕтєρѕ\n\n1. ᴛᴀᴘ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ɴᴀᴍᴇᴅ <b>' 🎬 ᴄʟɪᴄᴋ ᴛᴏ sᴇᴀʀᴄʜ සිංහල උපසිරැසි '</b>\n2. ᴛʜᴇɴ ᴛʏᴘᴇ ғɪʟᴍ ᴏʀ ᴛᴠ sᴇʀɪᴇs ɴᴀᴍᴇ ᴛʜᴀᴛ ʏᴏᴜ ᴡᴀɴᴛᴇᴅ ᴛᴏ sᴇᴀʀᴄʜ \n3. sᴇʟᴇᴄᴛ ʏᴏᴜʀ ᴍᴇᴅɪᴀ ғɪʟᴇ (ᴀᴍᴏɴɢ ᴠᴀʀɪᴏᴜs ғᴏʀᴍᴀᴛs) & ᴅᴏᴡɴʟɪᴀᴅ ɪᴛ\n\n 😜<b>ɪғ ʏᴏᴜ ᴅᴏɴ'ᴛ ᴋɴᴏᴡ ᴛʜᴀᴛ sʏsᴛᴇᴍ ,ᴊᴜsᴛ ᴛʏᴘᴇ ᴛʜᴇ ɴᴀᴍᴇ ᴏғ ᴛʜᴇ ᴍᴏᴠɪᴇ<b> \n\n❔ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴀ ʜᴇʟᴘ , ᴛᴀᴘ' 📕 ᴛᴜᴛᴏʀɪᴀʟ ᴠɪᴅᴇᴏ ' ʙᴜᴛᴛᴏɴ ᴛᴏ ʀᴇsᴏʟᴠᴇ ʏᴏᴜ ɪssᴜᴇ\n\n🔅 𝐈𝐟 𝐭𝐡𝐞𝐫𝐞 𝐰𝐚𝐬𝐧'𝐭 𝐲𝐨𝐮𝐫 𝐟𝐢𝐥𝐦 𝐨𝐫 𝐓𝐕 𝐬𝐞𝐫𝐢𝐞𝐬 𝐉𝐮𝐬𝐭 𝐭𝐲𝐩𝐞 𝐚𝐬 𝐚 𝐧𝐨𝐫𝐦𝐚𝐥 𝐜𝐡𝐚𝐭 𝐰𝐞 𝐰𝐢𝐥𝐥 𝐮𝐩𝐥𝐨𝐚𝐝 𝐢𝐭 𝐚𝐬 𝐬𝐨𝐨𝐧 𝐚𝐬 𝐩𝐨𝐬𝐬𝐢𝐛𝐥𝐞\n\n<a href='https://t.me/sub_searcher_bot'>🤖</a> | © ᴅᴇᴠᴇʟᴏᴘᴇᴅ ʙʏ @cinehub_family ", reply_markup=reply_markup)

@Client.on_message(filters.command('info'))
async def info(bot, message):
    msg = await message.reply("😎 ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴋɴᴏᴡ ᴍᴏᴠɪᴇs & ᴛᴠ sᴇʀɪᴇs sᴛᴏʀʏ ʟɪɴᴇ , ᴀᴄᴛᴏʀs , ʀᴇʟᴇsᴇ ᴅᴀᴛᴇ , .. .\n\n ᴡᴇ ʜᴀᴠᴇ ᴀʀʀᴀɴɢᴇ ɪᴛ ғᴏʀ ʏᴏᴜ ❕ \n\n🔥ᴊᴜsᴛ ᴛʏᴘᴇ ᴀs **/imdb <code>movie or TV series</code>** \n\nσρтιση ѕυρρσят ву : @imdb", quote=True)
    msg = await message.reply("🗂")  

@Client.on_message(filters.command('movie_tvseries'))
async def play(bot, message):
    msg = await message.reply("🍿 **Movie | Series time**\n\n\n🎬 ඔන්න ඉතින් ඔයලගෙ පහසුවට අපි ᴍᴏᴠɪᴇ | ᴛᴠ sᴇʀɪᴇs බොට් කෙනෙක්වත් හදලා තියෙනවා \n\nකරන්න තියෙන්නෙ මේ උපසිරැසි බොට්ව ඔයා පවිච්චි කරපු විදියටම ᴍᴏᴠɪᴇ එකේ හෝ sᴇʀɪᴇs එකේ Name එක English වලින් type කරන එකයි \n\n\n⚡ **ᴍᴏᴠɪᴇ | sᴇʀɪᴇs ʙᴏᴛ; @media_searcher_bot** \n\n\n<a href='https://t.me/media_searcher_bot'>🤖</a> | Powered By; © <a href='https://t.me/cinehub_family'>🄲🄸🄽🄴🄷🅄🄱</a>", quote=True)
    msg = await message.reply("😇")

@Client.on_message(filters.command('total') & filters.user(ADMINS))
async def total(bot, message):
    """Show total files in database"""
    msg = await message.reply("Processing...⏳", quote=True)
    try:
        total = await Media.count_documents()
        await msg.edit(f'📁 Saved files: {total} \n\n Boss තව Movie & Series ටිකක් Add කලා නම් හරිනේ 😜')
    except Exception as e:
        logger.exception('Failed to check total files')
        await msg.edit(f'Error: {e}')


@Client.on_message(filters.command('logger') & filters.user(ADMINS))
async def log_file(bot, message):
    """Send log file"""
    try:
        await message.reply_document('TelegramBot.log')
    except Exception as e:
        await message.reply(str(e))
