import sys
import subprocess
import json
from pathlib import Path


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def get_default_download_dir():
    """Get the system's Downloads folder"""
    try:
        # Try to get user's Downloads folder (works on Windows, Linux, macOS)
        import os
        if sys.platform == "win32":
            # Windows
            downloads = Path.home() / "Downloads"
        else:
            # Linux/macOS
            downloads = Path.home() / "Downloads"

        # Create if it doesn't exist
        downloads.mkdir(parents=True, exist_ok=True)
        return downloads
    except:
        # Fallback to current directory if Downloads folder can't be accessed
        return Path.cwd()


def get_bin_paths():
    base_dir = get_base_dir()
    bin_dir = base_dir / "bin"
    return bin_dir / "yt-dlp.exe", bin_dir / "ffmpeg.exe"


class YTVideoDownloader:
    def __init__(
        self, progress_hook=None, use_rich=False, browsers=None, download_dir=None
    ):
        self.progress_hook = progress_hook
        self.use_rich = use_rich
        self.browsers = browsers if browsers else []

        if download_dir:
            self.download_dir = Path(download_dir)
        else:
            # Default to system's Downloads folder
            self.download_dir = get_default_download_dir()

        self.download_dir.mkdir(parents=True, exist_ok=True)

    def get_formats(self, url):
        try:
            yt_dlp, _ = get_bin_paths()

            if not yt_dlp.exists():
                return {
                    "status": False,
                    "message": "yt-dlp.exe not found in bin folder",
                }

            cmd = [str(yt_dlp), url, "-J"]

            if self.browsers:
                for browser in self.browsers:
                    cmd.extend(["--cookies-from-browser", browser])

            # Hide console window on Windows
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=60,
                startupinfo=startupinfo
            )

            info = json.loads(result.stdout)
            formats = info.get("formats", [])

            return {"status": True, "formats": formats, "info": info}
        except subprocess.TimeoutExpired:
            return {"status": False, "message": "Request timed out"}
        except subprocess.CalledProcessError as e:
            return {"status": False, "message": f"Failed to fetch formats: {e.stderr}"}
        except json.JSONDecodeError:
            return {"status": False, "message": "Failed to parse format data"}
        except Exception as e:
            return {"status": False, "message": str(e)}

    def download_video(self, url, format_string=None):
        try:
            yt_dlp, ffmpeg = get_bin_paths()

            if not yt_dlp.exists():
                return {
                    "status": False,
                    "message": "yt-dlp.exe not found",
                    "filepath": None,
                }

            cmd = [
                str(yt_dlp),
                url,
                "-o",
                str(self.download_dir / "%(title)s.%(ext)s"),
                "--newline",
                "--progress",
                "--extractor-args",
                "youtube:player_client=default,web",
            ]

            if self.browsers:
                for browser in self.browsers:
                    cmd.extend(["--cookies-from-browser", browser])

            is_audio_conversion = format_string in ["mp3", "wav"]

            if ffmpeg.exists():
                cmd.extend(["--ffmpeg-location", str(ffmpeg.parent)])
            elif is_audio_conversion:
                return {
                    "status": False,
                    "message": "ffmpeg.exe not found (required for audio conversion)",
                    "filepath": None,
                }

            if is_audio_conversion:
                cmd.extend(
                    ["-x", "--audio-format", format_string, "--audio-quality", "0"]
                )
                cmd.extend(["--add-metadata"])
            else:
                if format_string:
                    cmd.extend(["-f", format_string])
                else:
                    cmd.extend(["-f", "bestvideo+bestaudio/best"])
                cmd.extend(
                    [
                        "--merge-output-format",
                        "mp4",
                        "--add-metadata",
                        "--embed-thumbnail",
                    ]
                )

            # Hide console window on Windows
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                startupinfo=startupinfo
            )

            current_file = None
            error_output = []
            for line in process.stdout:
                # Removed print() to prevent console window from appearing

                if "ERROR:" in line or "WARNING:" in line:
                    error_output.append(line.strip())

                if self.progress_hook:
                    progress_data = {
                        "status": "downloading",
                        "percent": 0,
                        "speed": 0,
                        "downloaded": 0,
                        "total": 0,
                        "filename": None,
                    }

                    if "[download]" in line and "%" in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if "%" in part:
                                try:
                                    progress_data["percent"] = int(
                                        float(part.strip("%"))
                                    )
                                except:
                                    pass
                            if "MiB" in part or "KiB" in part or "GiB" in part:
                                try:
                                    if i > 0 and "of" in parts[i - 1]:
                                        size_parts = parts[i - 2 : i + 1]
                                        progress_data["downloaded"] = self._parse_size(
                                            size_parts[0]
                                        )
                                        progress_data["total"] = self._parse_size(
                                            size_parts[2]
                                        )
                                except:
                                    pass

                    if "[download] Destination:" in line:
                        current_file = line.split("Destination:")[-1].strip()
                        progress_data["filename"] = current_file

                    if "[ExtractAudio]" in line or "[ffmpeg]" in line:
                        progress_data["status"] = "converting"

                    self.progress_hook(progress_data)

            process.wait()

            if process.returncode == 0:
                if not current_file:
                    files = list(self.download_dir.glob("*.*"))
                    if files:
                        current_file = str(max(files, key=lambda p: p.stat().st_mtime))

                if self.progress_hook:
                    self.progress_hook({"status": "finished", "filename": current_file})

                return {
                    "status": True,
                    "message": "Download succeeded",
                    "filepath": current_file,
                }
            else:
                error_msg = "Download failed"
                if error_output:
                    error_msg += f": {'; '.join(error_output[:3])}"
                return {"status": False, "message": error_msg, "filepath": None}

        except subprocess.TimeoutExpired:
            return {"status": False, "message": "Download timed out", "filepath": None}
        except FileNotFoundError:
            return {
                "status": False,
                "message": "yt-dlp.exe not found or cannot be executed",
                "filepath": None,
            }
        except Exception as e:
            return {
                "status": False,
                "message": f"Download failed: {e}",
                "filepath": None,
            }

    def _parse_size(self, size_str):
        try:
            size_str = size_str.strip()
            if "GiB" in size_str:
                return float(size_str.replace("GiB", "")) * 1024 * 1024 * 1024
            elif "MiB" in size_str:
                return float(size_str.replace("MiB", "")) * 1024 * 1024
            elif "KiB" in size_str:
                return float(size_str.replace("KiB", "")) * 1024
            return 0
        except:
            return 0
