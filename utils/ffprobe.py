"""FFprobe wrapper for file metadata extraction."""
import subprocess
import json
from typing import Optional, Dict, Any
import os


class FFprobeError(Exception):
    """Exception raised when FFprobe operations fail."""
    pass


class MediaType:
    """Media type constants."""
    VIDEO = "video"
    IMAGE = "image"
    UNKNOWN = "unknown"


class FFprobeInfo:
    """Container for media file information."""

    def __init__(self, raw_data: Dict[str, Any]):
        self.raw_data = raw_data
        self._parse_data()

    def _parse_data(self):
        """Parse raw FFprobe data."""
        self.format = self.raw_data.get('format', {})
        self.streams = self.raw_data.get('streams', [])

        # Find video and audio streams
        self.video_stream = None
        self.audio_stream = None

        for stream in self.streams:
            codec_type = stream.get('codec_type')
            if codec_type == 'video' and self.video_stream is None:
                self.video_stream = stream
            elif codec_type == 'audio' and self.audio_stream is None:
                self.audio_stream = stream

    @property
    def duration(self) -> float:
        """Get duration in seconds."""
        return float(self.format.get('duration', 0))

    @property
    def width(self) -> int:
        """Get video width."""
        if self.video_stream:
            return int(self.video_stream.get('width', 0))
        return 0

    @property
    def height(self) -> int:
        """Get video height."""
        if self.video_stream:
            return int(self.video_stream.get('height', 0))
        return 0

    @property
    def video_codec(self) -> str:
        """Get video codec name."""
        if self.video_stream:
            return self.video_stream.get('codec_name', '')
        return ''

    @property
    def audio_codec(self) -> str:
        """Get audio codec name."""
        if self.audio_stream:
            return self.audio_stream.get('codec_name', '')
        return ''

    @property
    def bitrate(self) -> int:
        """Get bitrate in bits per second."""
        return int(self.format.get('bit_rate', 0))

    @property
    def format_name(self) -> str:
        """Get format name."""
        return self.format.get('format_name', '')

    @property
    def is_video(self) -> bool:
        """Check if file is a video."""
        # Video has duration greater than a small threshold (images might have tiny duration)
        return self.video_stream is not None and self.duration > 0.5

    @property
    def is_image(self) -> bool:
        """Check if file is an image."""
        # Images have video stream but very short or no duration
        # Also check format name for common image formats
        duration_ok = self.video_stream is not None and self.duration <= 0.5
        format_ok = any(fmt in self.format_name.lower() for fmt in ['image2', 'singlejpeg', 'png_pipe', 'webp_pipe'])
        return duration_ok or format_ok


def find_ffprobe(ffmpeg_path: str = "") -> Optional[str]:
    """
    Find FFprobe executable.

    Args:
        ffmpeg_path: Custom path to FFmpeg directory

    Returns:
        Path to FFprobe or None if not found
    """
    if ffmpeg_path:
        custom_path = os.path.join(ffmpeg_path, 'ffprobe')
        if os.name == 'nt':
            custom_path += '.exe'
        if os.path.exists(custom_path):
            return custom_path

    # Try system PATH
    cmd = 'ffprobe' if os.name != 'nt' else 'ffprobe.exe'
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


def get_file_info(file_path: str, ffprobe_path: str = None) -> FFprobeInfo:
    """
    Get media file information using FFprobe.

    Args:
        file_path: Path to media file
        ffprobe_path: Path to FFprobe executable

    Returns:
        FFprobeInfo object with file metadata

    Raises:
        FFprobeError: If FFprobe fails or file is invalid
    """
    if ffprobe_path is None:
        ffprobe_path = find_ffprobe()

    if ffprobe_path is None:
        raise FFprobeError("FFprobe not found. Please install FFmpeg.")

    if not os.path.exists(file_path):
        raise FFprobeError(f"File not found: {file_path}")

    try:
        cmd = [
            ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise FFprobeError(f"FFprobe failed: {result.stderr}")

        data = json.loads(result.stdout)
        return FFprobeInfo(data)

    except subprocess.TimeoutExpired:
        raise FFprobeError("FFprobe timeout")
    except json.JSONDecodeError as e:
        raise FFprobeError(f"Failed to parse FFprobe output: {e}")
    except Exception as e:
        raise FFprobeError(f"Error getting file info: {e}")


def detect_media_type(file_path: str, ffprobe_path: str = None) -> str:
    """
    Detect if file is video, image, or unknown.

    Args:
        file_path: Path to media file
        ffprobe_path: Path to FFprobe executable

    Returns:
        MediaType constant (VIDEO, IMAGE, or UNKNOWN)
    """
    # First, try to detect by extension as a fallback
    ext = os.path.splitext(file_path)[1].lower()
    image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif', '.gif', '.jp2', '.j2k']
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.ts', '.m2ts', '.mts']

    if ext in image_extensions:
        return MediaType.IMAGE
    if ext in video_extensions:
        return MediaType.VIDEO

    # Then try FFprobe detection
    try:
        info = get_file_info(file_path, ffprobe_path)
        if info.is_video:
            return MediaType.VIDEO
        elif info.is_image:
            return MediaType.IMAGE
    except FFprobeError:
        pass
    return MediaType.UNKNOWN
