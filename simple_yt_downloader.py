import sys
import subprocess
import urllib.request
from pathlib import Path


def get_paths():
    base_dir = Path(
        sys.executable if getattr(sys, "frozen", False) else __file__
    ).parent
    bin_dir = base_dir / "bin"
    yt_dlp = bin_dir / "yt-dlp.exe"
    ffmpeg = bin_dir / "ffmpeg.exe"

    if not yt_dlp.exists():
        print(f"Error: yt-dlp.exe not found in bin folder")
        return None, None

    return str(yt_dlp), str(ffmpeg) if ffmpeg.exists() else None


def download(url, output_dir="downloaded_videos", quality="best", audio_only=False):
    yt_dlp, ffmpeg = get_paths()
    if not yt_dlp:
        return False

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    cmd = [
        yt_dlp,
        url,
        "-o",
        str(output / "%(title)s.%(ext)s"),
        "--progress",
        "--newline",
    ]

    if ffmpeg:
        cmd.extend(["--ffmpeg-location", str(Path(ffmpeg).parent)])

    if audio_only:
        cmd.extend(
            ["-f", "bestaudio", "-x", "--audio-format", "mp3", "--audio-quality", "0"]
        )
    else:
        format_str = "bestvideo+bestaudio/best" if quality == "best" else quality
        cmd.extend(["-f", format_str, "--merge-output-format", "mp4"])

    cmd.extend(["--add-metadata", "--embed-thumbnail"])

    print(f"\nDownloading: {url}")
    print(f"Output: {output.absolute()}\n")

    try:
        subprocess.run(cmd, check=True)
        print(f"\n✅ Download completed!")
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def list_formats(url):
    yt_dlp, _ = get_paths()
    if not yt_dlp:
        return

    print(f"\nFormats for: {url}\n")
    try:
        subprocess.run([yt_dlp, url, "-F"], check=True)
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    print("\n" + "=" * 60)
    print("YouTube Downloader (yt-dlp + ffmpeg)")
    print("=" * 60)

    yt_dlp, ffmpeg = get_paths()
    if not yt_dlp:
        input("\nPress Enter to exit...")
        return

    print(f"\n✅ yt-dlp.exe found")
    print(f"{'✅' if ffmpeg else '⚠️'} ffmpeg.exe {'found' if ffmpeg else 'not found'}")

    while True:
        print("\n" + "-" * 60)
        print("1. Download video (best quality)")
        print("2. Download audio (MP3)")
        print("3. List formats")
        print("4. Custom format")
        print("5. Exit")
        print("-" * 60)

        choice = input("\nChoice (1-5): ").strip()

        if choice == "5":
            break

        if choice not in ["1", "2", "3", "4"]:
            print("❌ Invalid choice")
            continue

        url = input("\nYouTube URL: ").strip()
        if not url:
            print("❌ URL required")
            continue

        if choice == "1":
            download(url)
        elif choice == "2":
            download(url, audio_only=True)
        elif choice == "3":
            list_formats(url)
        elif choice == "4":
            fmt = input("Format code: ").strip()
            if fmt:
                download(url, quality=fmt)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExited")
    except Exception as e:
        print(f"\n❌ Error: {e}")
