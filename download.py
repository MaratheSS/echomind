from __future__ import unicode_literals
import yt_dlp as youtube_dl
import os
import time
import shutil

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
FILE_TOO_LARGE_MESSAGE = "The audio file is too large for the current size and rate limits using Whisper. If you used a YouTube link, please try a shorter video clip. If you uploaded an audio file, try trimming or compressing the audio to under 100 MB."
max_retries = 3
delay = 2

# Ensure downloads directory exists
DOWNLOAD_DIR = "./downloads/audio"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


class MyLogger(object):
    def __init__(self, external_logger=lambda x: None):
        self.external_logger = external_logger

    def debug(self, msg):
        print("[debug]: ", msg)
        self.external_logger(msg)

    def warning(self, msg):
        print("[warning]: ", msg)

    def error(self, msg):
        print("[error]: ", msg)


def my_hook(d):
    print("hook", d["status"])
    if d["status"] == "finished":
        print("Done downloading, now converting ...")


def check_ffmpeg_available():
    """Check if ffmpeg is available in the system"""
    import shutil
    return shutil.which("ffmpeg") is not None

def get_ydl_opts(external_logger=lambda x: None, use_ffmpeg=True):
    """
    Get yt-dlp options. If ffmpeg is not available, skip postprocessing.
    """
    opts = {
        "format": "bestaudio/best",
        "logger": MyLogger(external_logger),
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
        "progress_hooks": [my_hook],
    }
    
    # Only add postprocessor if ffmpeg is available
    if use_ffmpeg and check_ffmpeg_available():
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",  # set the preferred bitrate to 192kbps
            }
        ]
    else:
        # Try to get audio in a format that doesn't need conversion
        # Prefer formats that are already audio-only
        opts["format"] = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"
        external_logger("⚠️ FFmpeg not found. Downloading audio without conversion. Some formats may not be supported.")
    
    return opts


def download_video_audio(url, external_logger=lambda x: None):
    retries = 0
    ffmpeg_available = check_ffmpeg_available()
    
    while retries < max_retries:
        try:
            # First try with ffmpeg if available
            use_ffmpeg = ffmpeg_available and retries == 0
            ydl_opts = get_ydl_opts(external_logger, use_ffmpeg=use_ffmpeg)
            
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                print("Going to download ", url)
                info = ydl.extract_info(url, download=False)
                filesize = info.get("filesize", 0)
                if filesize > MAX_FILE_SIZE:
                    raise Exception(FILE_TOO_LARGE_MESSAGE)
                filename = ydl.prepare_filename(info)
                res = ydl.download([url])
                print("youtube-dl result :", res)
                
                # If ffmpeg was used, expect .mp3 extension
                if use_ffmpeg:
                    mp3_filename = os.path.splitext(filename)[0] + '.mp3'
                    if os.path.exists(mp3_filename):
                        print('mp3 file name - ', mp3_filename)
                        return mp3_filename
                
                # If no ffmpeg or conversion failed, return the downloaded file as-is
                # Check for common audio extensions
                downloaded_file = filename
                if os.path.exists(downloaded_file):
                    print('Downloaded file - ', downloaded_file)
                    return downloaded_file
                
                # Try to find the actual downloaded file (yt-dlp might change extension)
                base_name = os.path.splitext(filename)[0]
                for ext in ['.m4a', '.webm', '.opus', '.mp3', '.mp4']:
                    potential_file = base_name + ext
                    if os.path.exists(potential_file):
                        print('Found downloaded file - ', potential_file)
                        return potential_file
                
                # If we can't find the file, return the expected filename anyway
                return downloaded_file
                
        except Exception as e:
            error_msg = str(e)
            # If ffmpeg error and we haven't tried without it yet, retry without ffmpeg
            if "ffmpeg" in error_msg.lower() or "ffprobe" in error_msg.lower():
                if retries == 0 and ffmpeg_available:
                    external_logger("⚠️ FFmpeg not available. Retrying download without audio conversion...")
                    retries += 1
                    ffmpeg_available = False  # Disable ffmpeg for next attempt
                    continue
            
            retries += 1
            print(
                f"An error occurred during downloading (Attempt {retries}/{max_retries}):",
                error_msg,
            )
            if retries >= max_retries:
                # Provide helpful error message
                if "ffmpeg" in error_msg.lower() or "ffprobe" in error_msg.lower():
                    raise Exception(
                        "FFmpeg/FFprobe not found. Please install FFmpeg to download YouTube videos.\n"
                        "Windows: Download from https://ffmpeg.org/download.html or use: choco install ffmpeg\n"
                        "Alternatively, you can upload audio files directly instead of using YouTube links."
                    )
                raise e
            time.sleep(delay)



def delete_download(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
            print(f"File {path} has been deleted.")
        elif os.path.isdir(path):
            shutil.rmtree(path)
            print(f"Directory {path} and its contents have been deleted.")
        else:
            print(f"The path {path} is neither a file nor a directory.")
    except PermissionError:
        print(f"Permission denied: Unable to delete {path}.")
    except FileNotFoundError:
        print(f"File or directory not found: {path}")
    except Exception as e:
        print(f"An error occurred while trying to delete {path}: {str(e)}")
        