import sys
import curl_cffi
from pathlib import Path


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def get_latest_version():
    url = "https://github.com/yt-dlp/yt-dlp/releases/latest"
    session = curl_cffi.Session(impersonate="chrome", timeout=60)
    response = session.get(url, allow_redirects=True)
    return response.url.split("/")[-1]


def download_yt_dlp():
    base_dir = get_base_dir()
    bin_dir = base_dir / "bin"
    bin_dir.mkdir(exist_ok=True)
    yt_dlp_path = bin_dir / "yt-dlp.exe"

    version = get_latest_version()
    download_url = f"https://github.com/yt-dlp/yt-dlp/releases/download/{version}/yt-dlp.exe"

    session = curl_cffi.Session(impersonate="chrome", timeout=120)
    response = session.get(download_url, stream=True)

    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}")

    with open(yt_dlp_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    if not yt_dlp_path.exists() or yt_dlp_path.stat().st_size == 0:
        raise Exception("Download failed")

    return str(yt_dlp_path)


if __name__ == "__main__":
    print(download_yt_dlp())
