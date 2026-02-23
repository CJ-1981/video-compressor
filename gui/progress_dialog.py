"""Progress dialog for compression operations."""
import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Callable, Optional


class ProgressDialog:
    """Modal dialog showing compression progress."""

    def __init__(
        self,
        parent: tk.Tk,
        title: str = "Compressing",
        on_abort: Optional[Callable] = None
    ):
        self.parent = parent
        self.on_abort = on_abort
        self.result = None
        self.start_time = None
        self.close_on_complete = True
        self.is_completed = False

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x200")
        self.dialog.resizable(False, False)

        # Make dialog modal (but allow abort)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (200 // 2)
        self.dialog.geometry(f"+{x}+{y}")

        self._create_widgets()
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close_request)

    def _create_widgets(self):
        """Create dialog widgets."""
        # Main frame with padding
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Status and file count frame
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(pady=(0, 10))

        # Status label
        self.status_label = ttk.Label(
            status_frame,
            text="Preparing...",
            font=('Segoe UI', 10)
        )
        self.status_label.pack(side=tk.LEFT)

        # File count label (x/y files)
        self.file_count_label = ttk.Label(
            status_frame,
            text="",
            font=('Segoe UI', 9),
            foreground='gray'
        )
        self.file_count_label.pack(side=tk.RIGHT, padx=(10, 0))

        # Current file label
        self.file_label = ttk.Label(
            main_frame,
            text="",
            font=('Segoe UI', 9),
            foreground='gray'
        )
        self.file_label.pack(pady=(0, 20))

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            main_frame,
            mode='determinate',
            length=460
        )
        self.progress_bar.pack(pady=(0, 10))

        # Percentage label
        self.percent_label = ttk.Label(
            main_frame,
            text="0%",
            font=('Segoe UI', 10, 'bold')
        )
        self.percent_label.pack(pady=(0, 20))

        # Time info frame
        time_frame = ttk.Frame(main_frame)
        time_frame.pack(pady=(0, 20))

        self.elapsed_label = ttk.Label(
            time_frame,
            text="Elapsed: 0:00",
            font=('Segoe UI', 9)
        )
        self.elapsed_label.pack(side=tk.LEFT, padx=(0, 20))

        self.eta_label = ttk.Label(
            time_frame,
            text="ETA: --:--",
            font=('Segoe UI', 9)
        )
        self.eta_label.pack(side=tk.LEFT)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack()

        # Abort button
        self.abort_button = ttk.Button(
            button_frame,
            text="Abort",
            command=self._abort,
            width=15
        )
        self.abort_button.pack()

    def update_progress(
        self,
        current: int,
        total: int,
        current_file: str = "",
        status: str = "running",
        file_count: str = None
    ):
        """Update progress display."""
        # Check if dialog still exists
        try:
            if not self.dialog.winfo_exists():
                return
        except tk.TclError:
            # Dialog has been destroyed
            return

        # Update progress bar
        percentage = (current / total * 100) if total > 0 else 0
        try:
            self.progress_bar['value'] = percentage
            self.percent_label.config(text=f"{int(percentage)}%")
        except (tk.TclError, AttributeError):
            return

        # Update file label
        if current_file:
            display_file = current_file
            if len(display_file) > 50:
                display_file = "..." + display_file[-47:]
            try:
                self.file_label.config(text=display_file)
            except (tk.TclError, AttributeError):
                pass

        # Update status
        status_text = {
            "running": "Compressing...",
            "completed": "Completed!",
            "error": "Error occurred",
            "aborted": "Aborted",
            "pending": "Preparing..."
        }.get(status, status)

        try:
            self.status_label.config(text=status_text)
        except (tk.TclError, AttributeError):
            pass

        # Update file count
        if file_count:
            try:
                self.file_count_label.config(text=f"Files: {file_count}")
            except (tk.TclError, AttributeError):
                pass

        # Update time info
        if self.start_time:
            elapsed = time.time() - self.start_time
            mins, secs = divmod(int(elapsed), 60)
            try:
                self.elapsed_label.config(text=f"Elapsed: {mins}:{secs:02d}")

                if percentage > 0 and status == "running":
                    remaining = (elapsed / percentage) * (100 - percentage)
                    eta_mins, eta_secs = divmod(int(remaining), 60)
                    self.eta_label.config(text=f"ETA: {eta_mins}:{eta_secs:02d}")
            except (tk.TclError, AttributeError):
                pass

        # Auto-close on completion - only for overall completion (no current file)
        if status == "completed" and not current_file:
            self.is_completed = True
            if self.close_on_complete:
                try:
                    self.abort_button.config(text="Close", command=self.dialog.destroy)
                except (tk.TclError, AttributeError):
                    pass
        elif status == "completed" and current_file:
        elif status == "running":
            self.is_completed = False

        # Update button state for errors or abort (but not per-file completion)
        if status in ["error", "aborted"]:
            self.is_completed = True
            try:
                self.abort_button.config(text="Close", command=self.dialog.destroy)
            except (tk.TclError, AttributeError):
                pass

    def _abort(self):
        """Handle abort button click."""
        if self.on_abort:
            self.on_abort()
        else:

        self.status_label.config(text="Aborting...")
        self.abort_button.config(state=tk.DISABLED)

        # Update status after a short delay
        def update_aborted():
            try:
                if self.dialog.winfo_exists():
                    self.status_label.config(text="Aborted")
                    self.abort_button.config(text="Close", command=self.dialog.destroy)
            except tk.TclError:
                pass

        self.dialog.after(500, update_aborted)

    def _on_close_request(self):
        """Handle window close request."""

        # If button already shows "Close", just close the dialog
        if self.abort_button['text'] == "Close":
            self.dialog.destroy()
        # If truly completed, allow closing
        elif self.is_completed:
            self.dialog.destroy()
        # Otherwise, treat close as abort
        elif self.on_abort and self.abort_button['state'] == tk.NORMAL:
            self._abort()
        else:

    def set_start_time(self):
        """Set the start time for time calculations."""
        self.start_time = time.time()

    def set_error(self, error_message: str):
        """Display error message."""
        self.status_label.config(text="Error")
        self.file_label.config(text=error_message[:80])
        self.abort_button.config(text="Close", command=self.dialog.destroy)

    def show(self):
        """Show the dialog."""
        self.dialog.wait_window()
        return self.result
