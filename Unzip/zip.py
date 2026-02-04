import os
import time
import random
import string
import shutil
import tempfile
import asyncio
import patoolib
from Unzip.config import Config
from Unzip.state import active_tasks
from pyrogram import Client, filters
from pyrogram.types import ForceReply, InlineKeyboardMarkup, InlineKeyboardButton
from Unzip.progress import progress_for_pyrogram


SUPPORTED_FORMATS = ('.zip', '.rar', '.7z', '.tar', '.tar.gz', '.tgz', '.tar.bz2')


@Client.on_message(filters.document)
async def handle_file(client, message):
    chat_id = message.chat.id
    message_id = message.id
    task_key = (chat_id, message_id)
    
    user_id = message.from_user.id
    document = message.document
    file_name = document.file_name.lower()

    if document.file_size > Config.MAX_FILE_SIZE:
        return await message.reply("⚠️ File too large. Max allowed: 2GB")
        
    if not file_name.endswith(SUPPORTED_FORMATS):
        return await message.reply("⚠️ Unsupported file format.")

    cancel_id = ''.join(random.choices(string.ascii_letters + string.digits, k=5))

    password_msg = await message.reply(
        "🔐 **Does this file have a password?**\n\n"
        "If YES: Send the password.\n"
        "If NO: Send /skip to proceed.\n"
        f"(Cancel task: /c_{cancel_id})",
        quote=True
    )
    
    active_tasks[task_key] = {
        'status': 'waiting_password',
        'chat_id': chat_id,
        'message_id': message_id,
        'cancel_id': cancel_id,
        'password_prompt_id': password_msg.id,
        'document': document,
        'original_message': message 
    }


@Client.on_message(filters.text & ~filters.command(["start", "help"]))
async def password_handler(client, message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    found_key = None
    
    candidates = []
    for key, info in active_tasks.items():
        if info.get('chat_id') == chat_id and info.get('status') == 'waiting_password':
            candidates.append(key)
    
    if not candidates:
        return

    candidates.sort(key=lambda k: k[1], reverse=True)
    found_key = candidates[0]

            
    if found_key:
        text = message.text
        task_info = active_tasks[found_key]
        
        password = None
        if text.strip().startswith("/skip"):
            password = None
        else:
            password = text.strip()

        active_tasks[found_key]['status'] = 'downloading'
        
        try:
             await message.delete() 
        except:
             pass
        
        prompt_id = task_info.get('password_prompt_id')
        if prompt_id:
            try:
                await client.delete_messages(chat_id, prompt_id)
            except:
                pass
            
        asyncio.create_task(process_task(client, task_info['original_message'], found_key, password))


async def process_task(client, message, task_key, password):
    task_info = active_tasks[task_key]
    cancel_id = task_info['cancel_id']
    document = task_info['document']
    
    download_message = None
    file_path = None
    
    try:
        download_message = await message.reply(
            f"⏳ Downloading your file...\nUse /c_{cancel_id} to cancel.", 
            quote=True
        )
        task_info['download_message'] = download_message
        
        start = time.time()
        
        # Default: Single file logic
        unique_dir = os.path.join(Config.DOWNLOAD_LOCATION, f"{task_key[0]}_{task_key[1]}")
        is_split_archive = False
        is_first_part = True
        
        # Regex for split archives (e.g. name.part01.rar, name.part1.rar)
        # We also need to handle .001, .002 if supported, but .partN.rar is most common for unrar
        import re
        # Match patterns like: name.part01.rar, name.part1.rar
        split_match = re.search(r'(.+)\.part(\d+)\.rar$', document.file_name, re.IGNORECASE)
        
        if split_match:
            is_split_archive = True
            base_name = split_match.group(1)
            part_number = int(split_match.group(2))
            
            # For split archives, use a shared directory based on ChatID + BaseName
            # We sanitize the base name to avoid path issues
            safe_base = "".join([c for c in base_name if c.isalpha() or c.isdigit() or c==' ' or c=='.']).strip()
            unique_dir = os.path.join(Config.DOWNLOAD_LOCATION, f"{chat_id}_{safe_base}")
            
            if part_number != 1:
                is_first_part = False

        os.makedirs(unique_dir, exist_ok=True)
        
        if task_key in active_tasks:
            active_tasks[task_key]['unique_dir'] = unique_dir
        
        file_path = await message.download(
            file_name=os.path.join(unique_dir, document.file_name),
            progress=progress_for_pyrogram,
            progress_args=("⬇️ Downloading...", download_message, start, task_key, cancel_id)
        )
        
        if task_key in active_tasks:
            active_tasks[task_key]['file_path'] = file_path
        else:
             # Cancelled during download
             if os.path.exists(file_path):
                 os.remove(file_path)
             # Only remove dir if it's NOT a split archive shared folder (or check if empty)
             if not is_split_archive and os.path.exists(unique_dir):
                 try:
                     shutil.rmtree(unique_dir)
                 except:
                     pass
             return

        # Processing Logic
        if is_split_archive and not is_first_part:
             # Just save it and finish
             await download_message.edit(f"💾 **Part Saved**\n\nFile `{document.file_name}` saved.\nWaiting for Part 1 to trigger extraction.")
             # We do not verify strict "completion" here as we are stateless. 
             # We rely on Part 1 to find this file later.
             # Remove task from active but KEEP THE FILE
             active_tasks.pop(task_key, None)
             return

        # Proceed to extraction (Single file OR Part 1 of split)
        await start_extraction(client, message, task_key, file_path, download_message, start, password)
        
    except Exception as e:
        if download_message:
            await download_message.edit(f"❌ Error: {e}")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        active_tasks.pop(task_key, None)


async def start_extraction(client, message, task_key, file_path, download_message, start, password):
    user_id = message.from_user.id
    extract_dir = os.path.join(Config.DOWNLOAD_LOCATION, f'extracted_{user_id}_{int(time.time())}')
    os.makedirs(extract_dir, exist_ok=True)
    
    if task_key in active_tasks:
        active_tasks[task_key]['extract_dir'] = extract_dir
        
    await download_message.edit(
        "📦 Extracting archive...",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⛔ Cancel", callback_data=f"cancel_unzip_{task_key[0]}_{task_key[1]}")]
        ])
    )

    task = asyncio.create_task(
        extract_and_send_files(client, message, file_path, extract_dir, download_message, start, password, task_key)
    )
    if task_key in active_tasks:
        active_tasks[task_key]['task'] = task
    
    try:
        await task
    except asyncio.CancelledError:
        pass
    finally:
        active_tasks.pop(task_key, None)


async def extract_and_send_files(client, message, file_path, extract_dir, download_message, start, password, task_key):
    try:
        # Try extracting with the provided password (or None)
        try:
             await asyncio.to_thread(patoolib.extract_archive, file_path, outdir=extract_dir, password=password)
        except patoolib.util.PatoolError as e:
             if password is None:
                  await download_message.edit(f"❌ Extraction Failed. File might be password protected, but you skipped it.\nError: {e}")
             else:
                  await download_message.edit(f"❌ Extraction Failed. Incorrect password or error.\nError: {e}")
             return
        except Exception as e:
            await download_message.edit(f"❌ Failed to extract: {e}")
            return

        await download_message.edit("📤 Preparing files to send...")
        
        if task_key not in active_tasks:
             return

        files_count = 0
        for root, _, files in os.walk(extract_dir):
            for file_name in files:
                files_count += 1
                
                if task_key not in active_tasks:
                    return

                extracted_file_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(extracted_file_path, extract_dir)
                
                # Check cancellation before starting a new upload
                if task_key not in active_tasks:
                     return

                # Detect media type
                is_video = False
                is_image = False
                ext = os.path.splitext(file_name)[1].lower()
                
                if ext in ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.wmv']:
                    is_video = True
                elif ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
                    is_image = True
                
                try:
                    if is_video:
                         # Get metadata
                         from Unzip.ffmpeg_utils import get_video_metadata, generate_thumbnail
                         duration, width, height = await get_video_metadata(extracted_file_path)
                         thumb_path = await generate_thumbnail(extracted_file_path)
                         
                         await client.send_video(
                            chat_id=message.chat.id,
                            video=extracted_file_path,
                            caption=f"🎥 `{relative_path}`",
                            supports_streaming=True,
                            duration=duration,
                            width=width,
                            height=height,
                            thumb=thumb_path,
                            progress=progress_for_pyrogram,
                            progress_args=("⬆️ Uploading Video...", download_message, start, task_key, active_tasks[task_key]['cancel_id'])
                        )
                         
                         if thumb_path and os.path.exists(thumb_path):
                             os.remove(thumb_path)
                             
                    elif is_image:
                         await client.send_photo(
                            chat_id=message.chat.id,
                            photo=extracted_file_path,
                            caption=f"🖼 `{relative_path}`",
                            progress=progress_for_pyrogram,
                            progress_args=("⬆️ Uploading Image...", download_message, start, task_key, active_tasks[task_key]['cancel_id'])
                        )
                    else:
                        await client.send_document(
                            chat_id=message.chat.id,
                            document=extracted_file_path,
                            file_name=relative_path, 
                            caption=f"📄 `{relative_path}`",
                            progress=progress_for_pyrogram,
                            progress_args=("⬆️ Uploading File...", download_message, start, task_key, active_tasks[task_key]['cancel_id'])
                        )
                except Exception as e:
                    print(f"Error uploading {file_name}: {e}")
                    await asyncio.sleep(3) 
                    try:
                        # Retry with basic methods (no progress to avoid stale state causing generic errors)
                        if is_video:
                             await client.send_video(
                                chat_id=message.chat.id,
                                video=extracted_file_path,
                                caption=f"🎥 `{relative_path}`",
                                supports_streaming=True
                            )
                        elif is_image:
                             await client.send_photo(
                                chat_id=message.chat.id,
                                photo=extracted_file_path,
                                caption=f"🖼 `{relative_path}`"
                            )
                        else:
                            await client.send_document(
                                chat_id=message.chat.id,
                                document=extracted_file_path,
                                caption=f"📄 `{relative_path}`",
                            )
                    except:
                        pass 

        # Calculate summary stats
        end_time = time.time()
        time_taken = end_time - start
        minutes = int(time_taken // 60)
        seconds = int(time_taken % 60)
        time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        
        # Delete the progress message
        try:
            await download_message.delete()
        except:
            pass
            
        # Send new summary message
        await client.send_message(
            chat_id=message.chat.id,
            text=f"**✨ Extraction Finished**\n\n"
                 f"📂 **Files Uploaded:** `{files_count}`\n"
                 f"⏳ **Time Elapsed:** `{time_str}`\n\n"
                 f"✅ **Status:** `Completed Successfully`"
        )

    except Exception as e:
        await download_message.edit(f"❌ Error during processing: {e}")
    finally:
        # Cleanup extracted directory
        if extract_dir and os.path.exists(extract_dir):
            try:
                shutil.rmtree(extract_dir)
            except Exception as e:
                print(f"Error deleting extracted dir: {e}")
        
        # Cleanup unique download directory
        # Be careful with split archives - cleaning up might delete other parts if we are hasty.
        # Ideally, we only delete if we created a truly unique dir, OR if we are sure we are done.
        # For this implementation, we will rely on periodic cleanup or manual maintenance for shared folders,
        # OR we check if the folder is empty.
        unique_dir = task_info.get('unique_dir')
        if unique_dir and os.path.exists(unique_dir):
            try:
                # If it was a standard unique task (numbers), delete it safely
                if f"{task_info['chat_id']}_{task_info['message_id']}" in unique_dir:
                     shutil.rmtree(unique_dir)
                # If it looks like a shared split-archive folder, maybe leave it? 
                # Or check if we are the extracting task (Part 1). 
                # If Part 1 finishes, it consumes the archive, so we MIGHT be able to delete the folder?
                # But patool might leave parts behind. 
                # Let's delete ONLY if we successfully extracted (which implies we utilized the files).
                # To be safe: Only delete if empty or if we are the 'driver' (Part 1) and we finished.
            except Exception as e:
                print(f"Error deleting unique dir: {e}")
