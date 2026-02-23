"""Base compressor interface."""
from abc import ABC, abstractmethod
from typing import Optional, Callable
import threading


class CompressionProgress:
    """Progress tracking for compression operations."""

    def __init__(self):
        self.current = 0
        self.total = 100
        self.current_file = ""
        self.status = "pending"
        self.error: Optional[str] = None

    def update(self, current: int, total: int = None):
        """Update progress."""
        self.current = current
        if total is not None:
            self.total = total

    def get_percentage(self) -> float:
        """Get progress as percentage."""
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100


class BaseCompressor(ABC):
    """Abstract base class for compressors."""

    def __init__(self):
        self._abort_flag = False
        self._lock = threading.Lock()
        self.progress = CompressionProgress()
        self._progress_callback: Optional[Callable[[CompressionProgress], None]] = None

    def set_progress_callback(self, callback: Callable[[CompressionProgress], None]):
        """Set callback for progress updates."""
        with self._lock:
            self._progress_callback = callback

    def _notify_progress(self):
        """Notify progress callback."""
        if self._progress_callback:
            self._progress_callback(self.progress)

    def abort(self):
        """Signal abort to the compression process."""
        with self._lock:
            self._abort_flag = True

    def _should_abort(self) -> bool:
        """Check if abort was requested."""
        with self._lock:
            result = self._abort_flag
        if result:
        return result

    def reset(self):
        """Reset compressor state for new operation."""
        with self._lock:
            self._abort_flag = False
            self.progress = CompressionProgress()

    @abstractmethod
    def compress(self, input_path: str, output_path: str, level: str = "medium") -> bool:
        """
        Compress a file.

        Args:
            input_path: Path to input file
            output_path: Path to output file
            level: Compression level (low, medium, high)

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        pass
