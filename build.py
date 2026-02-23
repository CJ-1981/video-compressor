"""Build script to create standalone executable with PyInstaller."""
import os
import sys
import shutil
from pathlib import Path

def download_ffmpeg():
    """Download FFmpeg binaries for bundling."""
    print("Downloading FFmpeg...")

    # Create ffmpeg directory
    ffmpeg_dir = Path("ffmpeg_bin")
    ffmpeg_dir.mkdir(exist_ok=True)

    if os.name == 'nt':
        # Windows - download static build
        import urllib.request
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        zip_path = ffmpeg_dir / "ffmpeg.zip"

        print(f"Downloading from {url}...")
        urllib.request.urlretrieve(url, zip_path)

        # Extract
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(ffmpeg_dir)

        # Find and copy ffmpeg.exe
        for root, dirs, files in os.walk(ffmpeg_dir):
            if "ffmpeg.exe" in files:
                shutil.copy(os.path.join(root, "ffmpeg.exe"), "ffmpeg.exe")
                shutil.copy(os.path.join(root, "ffprobe.exe"), "ffprobe.exe")
                break

        # Cleanup
        os.remove(zip_path)
        shutil.rmtree(ffmpeg_dir, ignore_errors=True)

    print("FFmpeg downloaded successfully!")

def build_exe():
    """Build the executable using PyInstaller."""
    print("Building executable...")

    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--name=VideoCompressor",
        "--onefile",
        "--windowed",
        "--icon=icon.ico" if os.path.exists("icon.ico") else "",
        "--add-data=ffmpeg.exe;.",
        "--add-data=ffprobe.exe;.",
        "--add-data=config/presets.json;config",
        "--hidden-import=tkinterdnd2",
        "--hidden-import=PIL",
        "main.py"
    ]

    # Remove empty strings
    cmd = [c for c in cmd if c]

    import subprocess
    subprocess.run(cmd, check=True)

    print("\nBuild complete!")
    print("Executable location: dist/VideoCompressor.exe")

def cleanup():
    """Clean up build files."""
    print("Cleaning up build files...")
    for dir_name in ["build", "__pycache__"]:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name, ignore_errors=True)

    spec_file = "VideoCompressor.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)

if __name__ == "__main__":
    try:
        # Check if FFmpeg exists
        if not os.path.exists("ffmpeg.exe"):
            download_ffmpeg()
        else:
            print("FFmpeg already downloaded, skipping...")

        # Build executable
        build_exe()

        # Optional: cleanup
        response = input("\nClean up build files? (y/n): ")
        if response.lower() == 'y':
            cleanup()

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
