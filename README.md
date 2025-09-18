# YouTube Transcript Scraper

A simple Python script to download transcripts of all public videos from a YouTube channel into individual `.txt` files.  
Each file is named after the video title and stored in a folder named after the channel.

---

## Features
- Fetches transcripts of all public videos in a channel.
- Saves each transcript in a separate `.txt` file.
- Logs videos that have no transcript or couldn’t be fetched in `missing_transcripts.txt`.
- Handles errors gracefully , the script won’t crash if some videos fail.

---

## Virtual Environment (Recommended)

To avoid conflicts with other Python packages, it’s recommended to use a virtual environment:

```bash
# Create a virtual environment in the project folder
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```
## Requirements

- Python 3.8+
- Packages: yt-dlp, youtube-transcript-api
Install with:
```bash
pip install -r requirements.txt

```
## How to Run

1. Open terminal or command prompt in the project folder.
2. Run the script with the channel URL:
```bash
python app.py "https://www.youtube.com/@ChannelName"
```
3. Transcripts will be saved in a folder named after the channel.
4. Check missing_transcripts.txt for any videos that couldn’t be fetched.

## Notes / Limitations

- Some videos may not have transcripts (YouTube didn’t provide them).
- Occasionally, YouTube may temporarily block your IP if too many requests are made.
- In that case, all videos might fail. To bypass:
  1. Wait a few hours and try again.
  2. Or run the script on a different network (like a mobile hotspot or VPN).
- The script only saves plain text transcripts (.txt).
- Timestamps or .srt files are optional and not included.

## 🎉 That’s it!

- Open example_output/ to see sample transcripts.
- Run the script again anytime to fetch new videos from the channel.