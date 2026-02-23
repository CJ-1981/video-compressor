"""Image compression using FFmpeg."""
import subprocess
import os
import sys
import time
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from compressor.base import BaseCompressor
from utils.ffprobe import find_ffprobe


class ImageCompressor(BaseCompressor):
    """Compressor for image files."""

    # Image file extensions
    SUPPORTED_EXTENSIONS = [
        '.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff',
        '.tif', '.gif'
    ]

    def __init__(self, ffmpeg_path: str = ""):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path

    def get_supported_extensions(self) -> list[str]:
        """Return list of supported image file extensions."""
        return self.SUPPORTED_EXTENSIONS

    def _find_ffmpeg(self) -> Optional[str]:
        """Find FFmpeg executable."""
        # Check if bundled with PyInstaller (in _MEIPASS or same directory)
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            bundle_dir = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
            bundled_ffmpeg = os.path.join(bundle_dir, 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
            if os.path.exists(bundled_ffmpeg):
                return bundled_ffmpeg

        if self.ffmpeg_path:
            custom_path = os.path.join(self.ffmpeg_path, 'ffmpeg')
            if os.name == 'nt':
                custom_path += '.exe'
            if os.path.exists(custom_path):
                return custom_path

        # Try system PATH
        cmd = 'ffmpeg' if os.name != 'nt' else 'ffmpeg.exe'
        try:
            result = subprocess.run(
                ['where', cmd] if os.name == 'nt' else ['which', cmd],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return None

    def compress(
        self,
        input_path: str,
        output_path: str,
        level: str = "medium",
        config: dict = None
    ) -> bool:
        """
        Compress image file.

        Args:
            input_path: Path to input image file
            output_path: Path to output image file
            level: Compression level (low, medium, high)
            config: Configuration dict with compression settings

        Returns:
            True if successful, False otherwise
        """
        self.reset()

        ffmpeg = self._find_ffmpeg()
        if ffmpeg is None:
            self.progress.error = "FFmpeg not found. Please install FFmpeg."
            self.progress.status = "error"
            self._notify_progress()
            return False

        if not os.path.exists(input_path):
            self.progress.error = f"Input file not found: {input_path}"
            self.progress.status = "error"
            self._notify_progress()
            return False

        # Default config if not provided
        if config is None:
            config = {"quality": 80}

        # Apply level-specific settings
        level_configs = {
            "low": {"quality": 70},
            "medium": {"quality": 80},
            "high": {"quality": 90}
        }

        if level in level_configs:
            config["quality"] = level_configs[level]["quality"]

        # Determine output format from extension
        output_ext = os.path.splitext(output_path)[1].lower()

        self.progress.current_file = os.path.basename(input_path)
        self.progress.status = "running"
        self.progress.update(50, 100)
        self._notify_progress()

        # Build FFmpeg command based on output format
        if output_ext in ['.jpg', '.jpeg']:
            # For JPEG: use -frames:v 1 with -update 1 for single image output
            # Quality scale: 2-31 (2=best, 31=worst)
            quality = config.get('quality', 80)
            ffmpeg_quality = max(2, min(31, 32 - (quality * 30 // 100)))

            cmd = [
                ffmpeg,
                '-i', input_path,
                '-frames:v', '1',        # Output only 1 frame
                '-qscale:v', str(ffmpeg_quality),  # Quality setting
                '-y',
                output_path
            ]

        elif output_ext == '.png':
            # For PNG
            cmd = [
                ffmpeg,
                '-i', input_path,
                '-frames:v', '1',
                '-vcodec', 'png',
                '-compression_level', '9',
                '-y',
                output_path
            ]

        elif output_ext == '.webp':
            # For WebP
            quality = config.get('quality', 80)
            cmd = [
                ffmpeg,
                '-i', input_path,
                '-frames:v', '1',
                '-vcodec', 'libwebp',
                '-quality', str(quality),
                '-y',
                output_path
            ]

        else:
            # Default: try JPEG for unknown formats
            quality = config.get('quality', 80)
            ffmpeg_quality = max(2, min(31, 32 - (quality * 30 // 100)))
            cmd = [
                ffmpeg,
                '-i', input_path,
                '-frames:v', '1',
                '-qscale:v', str(ffmpeg_quality),
                '-y',
                output_path
            ]

        try:
            # Run FFmpeg with Popen for abort support
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors='replace'
            )

            # Monitor process and check for abort more frequently
            while process.poll() is None:
                if self._should_abort():
                    # More aggressive termination
                    try:
                        process.terminate()
                        time.sleep(0.2)
                        if process.poll() is None:
                            process.kill()
                            time.sleep(0.1)

                        # On Windows, also try to kill any orphaned ffmpeg processes
                        if os.name == 'nt':
                            try:
                                subprocess.run(
                                    ['taskkill', '/F', '/IM', 'ffmpeg.exe'],
                                    capture_output=True,
                                    timeout=2
                                )
                            except Exception:
                                pass
                    except Exception:
                        pass

                    # Clean up partial output file
                    if os.path.exists(output_path):
                        try:
                            os.remove(output_path)
                        except OSError:
                            pass

                    self.progress.status = "aborted"
                    self._notify_progress()
                    return False
                time.sleep(0.05)  # Check abort flag more frequently

            return_code = process.wait()

            # Capture stderr before closing
            stderr_output = ""
            if process.stderr:
                stderr_output = process.stderr.read()

            # Check if output file was created and is valid
            # FFmpeg may return non-zero for warnings but still create valid files
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                # Verify it's a valid image file
                try:
                    with open(output_path, 'rb') as f:
                        header = f.read(3)
                        # Check for JPEG magic number
                        if output_ext in ['.jpg', '.jpeg'] and header == b'\xff\xd8\xff':
                            self.progress.update(100, 100)
                            self.progress.status = "completed"
                            self._notify_progress()
                            return True
                        # For other formats, just check if file exists and has content
                        elif len(header) >= 3:
                            self.progress.update(100, 100)
                            self.progress.status = "completed"
                            self._notify_progress()
                            return True
                except Exception:
                    pass

            # If we get here, the file is not valid
            self.progress.error = f"Output file invalid. FFmpeg code {return_code}"
            if stderr_output:
                self.progress.error += f": {stderr_output[:200]}"
            self.progress.status = "error"
            self._notify_progress()
            return False

        except Exception as e:
            self.progress.error = f"Compression error: {e}"
            self.progress.status = "error"
            self._notify_progress()
            # Clean up partial output file
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            return False

    def _get_format_from_ext(self, ext: str) -> Optional[str]:
        """Get FFmpeg format name from file extension."""
        format_map = {
            '.jpg': 'mjpeg',
            '.jpeg': 'mjpeg',
            '.png': 'png',
            '.webp': 'webp',
            '.bmp': 'bmp',
            '.tiff': 'tiff',
            '.tif': 'tiff',
            '.gif': 'gif'
        }
        return format_map.get(ext.lower())
