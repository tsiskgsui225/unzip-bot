# Unzip Bot

A high-performance Telegram bot to extract various archive formats (`.zip`, `.rar`, `.7z`, `.tar`, etc.) and upload the contents to Telegram.

## Features
- **High Speed**: Powered by `PyroTGFork` v2.2.17 and `TgCrypto` (C++).
- **Video Support**: Automatically detects video files, generates thumbnails, and extracts metadata (duration, resolution).
- **Format Support**: ZIP, RAR, 7Z, TAR, GZ, BZ2, and more.
- **Privacy**: Password-protected archives are supported (interactive prompt).
- **Robustness**: Cancellation support and crash recovery.

## Deploy on VPS (Ubuntu/Debian)

### 1. Update and Install System Dependencies
Update your system and install Python 3, Git, and FFmpeg (required for video processing).
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip git ffmpeg p7zip-full p7zip-rar unrar -y
```

### 2. Clone the Repository
```bash
git clone https://github.com/tsiskgsui225/unzip-bot.git
cd unzip-bot
```

### 3. Install Python Dependencies
```bash
pip3 install -r requirements.txt
```

### 4. Configure the Bot
Edit `Unzip/config.py` with your credentials, or use environment variables if you prefer to modify the code to support them.
*   `API_ID`: Get from my.telegram.org
*   `API_HASH`: Get from my.telegram.org
*   `BOT_TOKEN`: Get from @BotFather

### 5. Run the Bot
**Direct Run:**
```bash
python3 bot.py
```

**Run in Background (Systemd):**
Create a service file:
```bash
sudo nano /etc/systemd/system/unzip-bot.service
```
Paste the following (adjust paths/user):
```ini
[Unit]
Description=Unzip Telegram Bot
After=network.target

[Service]
User=root
WorkingDirectory=/root/unzip-bot
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```
Save and exit. Then enable and start:
```bash
sudo systemctl enable unzip-bot
sudo systemctl start unzip-bot
sudo systemctl status unzip-bot
```

## Commands
*   `/start` - Check if bot is online.
*   `/help` - Usage instructions.
*   `/c_<id>` - Cancel an active task (ID is provided during operation).

## License
MIT
