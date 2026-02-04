import math
import os
import time
from pyrogram import enums 
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Dictionary to store last update time for each progress message
# Key: (chat_id, message_id) -> timestamp
progress_state = {}

# Progress function with cancel button
async def progress_for_pyrogram(current, total, ud_type, message, start, task_key=None, cancel_id=None):
    now = time.time()
    diff = now - start
    
    chat_id = message.chat.id
    message_id = message.id
    msg_key = (chat_id, message_id)
    
    last_updated = progress_state.get(msg_key, 0)
    
    # Throttle updates: only update if 3 seconds have passed since LAST UPDATE or 100% complete
    if (now - last_updated) < 3 and current != total:
        return
    
    progress_state[msg_key] = now

    percentage = current * 100 / total
    speed = current / diff
    elapsed_time = round(diff) * 1000
    time_to_completion = round((total - current) / speed) * 1000
    estimated_total_time = elapsed_time + time_to_completion

    elapsed_time = TimeFormatter(milliseconds=elapsed_time)
    estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

    progress = "[{0}{1}] \n➪ Progress: {2}%\n".format(
        ''.join(["▓" for i in range(math.floor(percentage / 10))]),
        ''.join(["░" for i in range(10 - math.floor(percentage / 10))]),
        round(percentage, 2))

    tmp = progress + "➪ Done: {0}\n➪ Total: {1}\n➪ Speed: {2}/s\n➪ Time: {3}\n".format(
        humanbytes(current),
        humanbytes(total),
        humanbytes(speed),
        estimated_total_time if estimated_total_time != '' else "0 s"
    )
    
    if cancel_id:
        tmp += f"\nUse `/c_{cancel_id}` to cancel this task."
    
    cancel_callback = "cancel_unzip"
    if task_key:
         cancel_callback = f"cancel_unzip_{task_key[0]}_{task_key[1]}"

    try:
        await message.edit(
            text="{}\n {}".format(
                ud_type,
                tmp
            ),
            parse_mode=enums.ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                    [ 
                    InlineKeyboardButton('⛔ Cancel', callback_data=cancel_callback)
                   ]
               ]
             )
        )
    except:
        pass

def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]
