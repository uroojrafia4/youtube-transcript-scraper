import os
import re
import sys
import json
import subprocess
from datetime import datetime
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# --- Original Functions (unchanged) ---

def sanitize_filename(name: str, max_length=200) -> str:
    name = re.sub(r'[\r\n]+', ' ', name).strip()
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    name = re.sub(r'\s+', ' ', name)
    if len(name) > max_length:
        name = name[:max_length].rstrip()
    return name or "untitled"

def run_yt_dlp_json(channel_url: str) -> str:
    base_cmds = [
        ["yt-dlp", "-j", "--flat-playlist", channel_url],
        [sys.executable, "-m", "yt_dlp", "-j", "--flat-playlist", channel_url],  # fallback
    ]
    last_error = None
    for cmd in base_cmds:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return res.stdout
        except FileNotFoundError as e:
            last_error = e
            continue
        except subprocess.CalledProcessError as e:
            print("yt-dlp error:\n", e.stderr.strip())
            raise
    raise RuntimeError(f"Could not run yt-dlp. Last error: {last_error}")

def get_videos_from_channel(channel_url: str):
    stdout = run_yt_dlp_json(channel_url)
    lines = [l for l in stdout.splitlines() if l.strip()]
    videos = []
    for line in lines:
        try:
            j = json.loads(line)
        except json.JSONDecodeError:
            continue
        vid = j.get("id")
        title = j.get("title") or j.get("fulltitle") or vid or "untitled"
        uploader = j.get("uploader") or j.get("uploader_id") or j.get("channel") or None
        videos.append({"id": vid, "title": title, "uploader": uploader})
    if videos and videos[0].get("uploader"):
        channel_name = videos[0]["uploader"]
    else:
        channel_name = channel_url.rstrip("/").split("/")[-1]
    return channel_name, videos

def fetch_transcript_list(video_id: str, languages: list):
    try:
        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            data = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
            if isinstance(data, list):
                return data
    except Exception:
        pass

    api = YouTubeTranscriptApi()
    transcript_obj = api.fetch(video_id, languages=languages)

    if hasattr(transcript_obj, "to_raw_data"):
        return transcript_obj.to_raw_data()

    out = []
    for s in transcript_obj:
        if isinstance(s, dict):
            out.append(s)
        else:
            text = getattr(s, "text", None)
            start = getattr(s, "start", None)
            duration = getattr(s, "duration", None)
            out.append({
                "text": text if text is not None else "",
                "start": float(start) if start is not None else 0.0,
                "duration": float(duration) if duration is not None else 0.0,
            })
    return out

def download_transcripts(channel_url: str, languages: list, include_timestamps: bool, log_func=print):
    log_func("Finding videos...")
    channel_name_raw, videos = get_videos_from_channel(channel_url)
    channel_name = sanitize_filename(channel_name_raw)
    folder = os.path.join(os.getcwd(), channel_name)
    os.makedirs(folder, exist_ok=True)
    log_func(f"Saving transcripts to folder: {folder}")

    missing = {"no_transcript": [], "errors": []}
    used_filenames = set()

    for idx, v in enumerate(videos, start=1):
        vid = v.get("id")
        title_raw = v.get("title") or vid
        safe_title = sanitize_filename(title_raw)

        filename = f"{safe_title}.txt"
        if filename in used_filenames:
            filename = f"{safe_title}_{vid}.txt"
        used_filenames.add(filename)
        outpath = os.path.join(folder, filename)
        video_url = f"https://www.youtube.com/watch?v={vid}" if vid else "unknown"

        log_func(f"[{idx}/{len(videos)}] {safe_title} -> {filename}")

        try:
            data = fetch_transcript_list(vid, languages=languages)
            if include_timestamps:
                lines = []
                for item in data:
                    start = float(item.get("start", 0.0))
                    dur = float(item.get("duration", 0.0))
                    end = start + dur
                    lines.append(f"{start:.2f} --> {end:.2f}")
                    lines.append(item.get("text", ""))
                    lines.append("")  # blank line
                text = "\n".join(lines).strip()
            else:
                text = "\n".join([d.get("text", "") for d in data]).strip()

            with open(outpath, "w", encoding="utf-8") as f:
                header = f"Source: {video_url}\nTitle: {title_raw}\n\n"
                f.write(header)
                f.write(text + "\n")
            log_func("  ✅ Saved.")
        except (TranscriptsDisabled, NoTranscriptFound):
            with open(outpath, "w", encoding="utf-8") as f:
                f.write(f"Source: {video_url}\nTitle: {title_raw}\n\nNo transcript available for this video.\n")
            missing["no_transcript"].append(f"{title_raw} | {video_url}")
            log_func("  ⚠️ No transcript available.")
        except Exception as e:
            with open(outpath, "w", encoding="utf-8") as f:
                f.write(f"Source: {video_url}\nTitle: {title_raw}\n\nCould not fetch transcript.\nError: {e}\n")
            missing["errors"].append(f"{title_raw} | {video_url} | {e}")
            log_func(f"  ❌ Error: {e}")

    # write missing_transcripts.txt
    logpath = os.path.join(folder, "missing_transcripts.txt")
    with open(logpath, "w", encoding="utf-8") as f:
        f.write(f"Missing transcripts log\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        if missing["no_transcript"]:
            f.write("⚠️ No transcript available:\n")
            for m in missing["no_transcript"]:
                f.write("- " + m + "\n")
            f.write("\n")
        if missing["errors"]:
            f.write("❌ Errors while fetching:\n")
            for m in missing["errors"]:
                f.write("- " + m + "\n")

    log_func("\nAll done. Folder: " + folder)
    log_func("Missing log: " + logpath)

# --- GUI Part using Tkinter ---

class TranscriptGUI:
    def __init__(self, master):
        self.master = master
        master.title("YouTube Channel Transcript Downloader")
        master.geometry("750x500")

        ttk.Label(master, text="Channel URL:").pack(anchor='w', padx=10, pady=(10,0))
        self.entry_url = ttk.Entry(master, width=90)
        self.entry_url.pack(padx=10)

        ttk.Label(master, text="Languages (comma-separated, default 'en'):").pack(anchor='w', padx=10, pady=(10,0))
        self.entry_langs = ttk.Entry(master, width=50)
        self.entry_langs.insert(0, "en")
        self.entry_langs.pack(padx=10)

        self.var_timestamps = tk.BooleanVar(value=False)
        ttk.Checkbutton(master, text="Include timestamps", variable=self.var_timestamps).pack(anchor='w', padx=10, pady=10)

        self.btn_run = ttk.Button(master, text="Run", command=self.start_download)
        self.btn_run.pack(pady=5)

        ttk.Label(master, text="Log:").pack(anchor='w', padx=10)
        self.txt_log = scrolledtext.ScrolledText(master, width=90, height=20)
        self.txt_log.pack(padx=10, pady=5)

    def log(self, msg):
        self.txt_log.insert(tk.END, msg + "\n")
        self.txt_log.see(tk.END)
        self.master.update()

    def start_download(self):
        channel_url = self.entry_url.get().strip()
        if not channel_url:
            messagebox.showwarning("Input Error", "Please enter a channel URL")
            return
        langs = [x.strip() for x in self.entry_langs.get().split(",") if x.strip()]
        include_ts = self.var_timestamps.get()

        threading.Thread(target=download_transcripts, args=(channel_url, langs, include_ts, self.log)).start()


# --- Main Execution ---

if __name__ == "__main__":
    root = tk.Tk()
    gui = TranscriptGUI(root)
    root.mainloop()
