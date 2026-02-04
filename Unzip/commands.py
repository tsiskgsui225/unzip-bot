from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from Unzip.state import active_tasks

@Client.on_message(filters.command("start"))
async def start(client, message):
    start_message = (
        "Hello!\n\n"
        "Send me a ZIP file, and I'll extract it for you. I also support .RAR, .7z, .tar, and more.\n\n"
        "If a file is password protected, I will ask you for it."
    )
    await message.reply(start_message)


# Callback query handler
@Client.on_callback_query(filters.regex(r"^cancel_unzip"))
async def cancel(client, callback_query):
    try:
        # Parse data: cancel_unzip_chatId_messageId
        parts = callback_query.data.split("_")
        if len(parts) >= 3:
            chat_id = int(parts[2])
            message_id = int(parts[3])
            task_key = (chat_id, message_id)
            
            task_info = active_tasks.get(task_key)
            if task_info:
                if 'task' in task_info and task_info['task']:
                     task_info['task'].cancel()
                
                active_tasks.pop(task_key, None)
                await callback_query.answer("⛔ Task Cancelled", show_alert=True)
                # Try to edit the message to show cancelled instead of just deleting
                try:
                    await callback_query.message.edit("❌ Unzipping cancelled by user.")
                except:
                    pass
            else:
                await callback_query.answer("⚠️ Task not found or already completed", show_alert=True)
                # If stray message, delete it
                try:
                   await callback_query.message.delete()
                except:
                   pass
        else:
             # Fallback for old cancel buttons
             await callback_query.message.delete()
             
    except Exception as e:
        print(f"Error in cancel callback: {e}")



@Client.on_message(filters.command("help"))
async def help_command(client, message):
    help_message = (
        "Here are the commands you can use:\n\n"
        "/start - Start the bot and get the welcome message\n"
        "/help - Get help on how to use the bot\n\n"
        "To unzip a file, simply send me a ZIP file and I will extract its contents and send them back to you."
    )
    await message.reply(help_message)


@Client.on_message(filters.regex(r"^/c_(\w+)"))
async def cancel_command_handler(client, message):
    try:
        cancel_id = message.matches[0].group(1)
        # Find task with this cancel_id
        task_key = None
        for key, info in active_tasks.items():
            if info.get('cancel_id') == cancel_id:
                task_key = key
                break
        
        if task_key:
             task_info = active_tasks[task_key]
             if 'task' in task_info and task_info['task']:
                 task_info['task'].cancel()
            
             active_tasks.pop(task_key, None)
             await message.reply("⛔ Unzipping has been cancelled.")
             
             # Try to update the original download message too
             try:
                 await task_info['download_message'].edit("❌ Unzipping cancelled by user.")
             except:
                 pass
        else:
            await message.reply("⚠️ Valid task not found for this ID.")

    except Exception as e:
        await message.reply(f"⚠️ Error: {e}")


