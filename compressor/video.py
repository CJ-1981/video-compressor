"""Video compression using FFmpeg."""
import subprocess
import re
import os
import sys
import time
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from compressor.base import BaseCompressor
from utils.ffprobe import get_file_info, find_ffprobe


class VideoCompressor(BaseCompressor):
    """Compressor for video files."""

    # Video file extensions
    SUPPORTED_EXTENSIONS = [
        '.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv',
        '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.ts',
        '.m2ts', '.mts'
    ]

    def __init__(self, ffmpeg_path: str = ""):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path

    def get_supported_extensions(self) -> list[str]:
        """Return list of supported video file extensions."""
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

    def _parse_progress(self, line: str, duration: float) -> Optional[int]:
        """Parse FFmpeg progress output and return progress percentage."""
        # Match "frame=123 time=00:00:05.00"
        time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
        if time_match:
            hours = int(time_match.group(1))
            minutes = int(time_match.group(2))
            seconds = float(time_match.group(3))
            current_time = hours * 3600 + minutes * 60 + seconds

            if duration > 0:
                return int((current_time / duration) * 100)
        return None

    def _time_to_seconds(self, time_str: str) -> float:
        """Convert time string (HH:MM:SS.mmm) to seconds."""
        parts = time_str.split(':')
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        return 0.0

    def compress(
        self,
        input_path: str,
        output_path: str,
        level: str = "medium",
        config: dict = None
    ) -> bool:
        """
        Compress video file.

        Args:
            input_path: Path to input video file
            output_path: Path to output video file
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

        # Get video info for progress tracking
        try:
            file_info = get_file_info(input_path)
            duration = file_info.duration
        except Exception as e:
            self.progress.error = f"Failed to read video info: {e}"
            self.progress.status = "error"
            self._notify_progress()
            return False

        # Default config if not provided
        if config is None:
            config = {
                "crf": 23,
                "preset": "medium",
                "audio_bitrate": "192k",
                "codec": "libx264",
                "output_format": "mp4"
            }

        # Apply level-specific settings (optimized for lower CPU usage)
        level_configs = {
            "low": {"crf": 28, "preset": "faster", "audio_bitrate": "128k", "threads": 2},
            "medium": {"crf": 23, "preset": "medium", "audio_bitrate": "192k", "threads": 4},
            "high": {"crf": 18, "preset": "fast", "audio_bitrate": "320k", "threads": 4}
        }

        if level in level_configs:
            for key, value in level_configs[level].items():
                if key not in config:
                    config[key] = value

        # Build FFmpeg command with resource limits
        # Limit threads to prevent CPU overload
        threads = config.get('threads', min(4, os.cpu_count() or 4))

        cmd = [
            ffmpeg,
            '-threads', str(threads),  # Limit thread count
            '-thread_type', 'frame',   # Use frame threading (more efficient)
            '-i', input_path,
            '-c:v', config.get('codec', 'libx264'),
            '-crf', str(config.get('crf', 23)),
            '-preset', config.get('preset', 'medium'),
            '-tune', 'fastdecode',     # Optimize for faster decoding
            '-c:a', 'aac',
            '-b:a', config.get('audio_bitrate', '192k'),
            '-movflags', '+faststart',  # Optimize for streaming
            '-y'  # Overwrite output file
        ]

        # Add output file
        cmd.append(output_path)

        self.progress.current_file = os.path.basename(input_path)
        self.progress.status = "running"
        self._notify_progress()

        try:
            # Run FFmpeg and capture output for progress
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors='replace'  # Handle encoding errors
            )

            # Parse stderr for progress with non-blocking read
            import threading
            stop_reading = threading.Event()

            def read_stderr():
                """Read stderr in a separate thread to avoid blocking."""
                for line in iter(process.stderr.readline, ''):
                    if stop_reading.is_set():
                        break
                    if line:
                        progress = self._parse_progress(line, duration)
                        if progress is not None:
                            self.progress.update(progress, 100)
                            self._notify_progress()

            # Start reading stderr in background thread
            reader_thread = threading.Thread(target=read_stderr, daemon=True)
            reader_thread.start()

            # Monitor process and check for abort
            while process.poll() is None:
                if self._should_abort():
                    # Signal reader thread to stop
                    stop_reading.set()

                    # Terminate the process aggressively
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

                time.sleep(0.05)  # Check abort flag frequently

            # Wait for reader thread to finish
            reader_thread.join(timeout=1.0)

            return_code = process.poll()

            if return_code == 0:
                self.progress.update(100, 100)
                self.progress.status = "completed"
                self._notify_progress()
                return True
            else:
                self.progress.error = f"FFmpeg failed with code {return_code}"
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
