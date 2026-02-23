"""
Simplified build script for creating standalone executable.
Run this after placing ffmpeg.exe and ffprobe.exe in the project root.
"""
import os
import sys
import subprocess

def main():
    """Build executable using PyInstaller."""
    print("Building Video Compressor executable...")
    print("=" * 60)

    # Check for required files
    if not os.path.exists("ffmpeg.exe"):
        print("\n❌ Error: ffmpeg.exe not found!")
        print("\nTo build the executable:")
        print("1. Download FFmpeg static build from:")
        print("   https://www.gyan.dev/ffmpeg/builds/")
        print("   Download 'ffmpeg-release-essentials.zip'")
        print("\n2. Extract and copy these files to project root:")
        print("   - ffmpeg.exe")
        print("   - ffprobe.exe")
        print("\n3. Run this script again.")
        return

    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--name=VideoCompressor",
        "--onefile",
        "--windowed",
        "--add-data=ffmpeg.exe;.",
        "--add-data=ffprobe.exe;.",
        "--add-data=config/presets.json;config",
        "--hidden-import=tkinterdnd2",
        "main.py"
    ]

    print("\nRunning PyInstaller...")
    print("Command:", " ".join(cmd))
    print()

    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("✅ Build successful!")
        print(f"\nExecutable: dist/VideoCompressor.exe")
        print(f"Size: {os.path.getsize('dist/VideoCompressor.exe') / (1024*1024):.1f} MB")
        print("\nYou can distribute the exe file alone - it includes everything!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed: {e}")
        print("\nMake sure PyInstaller is installed:")
        print("  pip install pyinstaller")
    except FileNotFoundError:
        print("\n❌ PyInstaller not found!")
        print("\nInstall it with:")
        print("  pip install pyinstaller")

if __name__ == "__main__":
    main()
