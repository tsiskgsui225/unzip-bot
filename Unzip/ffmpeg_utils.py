import os
import subprocess
import json
import shutil

async def get_video_metadata(file_path):
    """
    Extracts video metadata (duration, width, height) using ffprobe.
    Returns a dict or specific values.
    """
    try:
        # Standard system command - assumes ffmpeg is in PATH
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration:stream=width,height",
            "-of", "json",
            file_path
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        
        if process.returncode != 0:
            print(f"ffprobe error: {err.decode()}")
            return 0, 0, 0
            
        data = json.loads(out.decode('utf-8'))
        
        duration = 0
        width = 0
        height = 0
        
        if 'format' in data and 'duration' in data['format']:
            duration = int(float(data['format']['duration']))
            
        if 'streams' in data and len(data['streams']) > 0:
            width = int(data['streams'][0].get('width', 0))
            height = int(data['streams'][0].get('height', 0))
            
        return duration, width, height
        
    except Exception as e:
        print(f"Error getting metadata: {e}")
        return 0, 0, 0

async def generate_thumbnail(file_path):
    """
    Generates a thumbnail for the video at 5% of duration or 5 seconds.
    Returns path to thumbnail or None.
    """
    try:
        thumb_path = f"{file_path}.jpg"
        
        # Simple thumbnail at 00:00:05
        cmd = [
            "ffmpeg",
            "-i", file_path,
            "-ss", "00:00:05.000",
            "-vframes", "1",
            "-q:v", "2",
            thumb_path,
            "-y"
        ]
        
        # We can also attempt to be smarter, but let's stick to basic
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        
        if process.returncode != 0:
            # Maybe video is shorter than 5s? try 0s
            cmd[3] = "00:00:01.000"
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = process.communicate()
            
        if os.path.exists(thumb_path):
            return thumb_path
        else:
            return None
            
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return None
