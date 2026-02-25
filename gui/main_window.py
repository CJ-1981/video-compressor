"""Main application window."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import threading
import time
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.progress_dialog import ProgressDialog
from gui.config_dialog import ConfigDialog
from compressor.video import VideoCompressor
from compressor.image import ImageCompressor
from utils.ffprobe import detect_media_type, MediaType, find_ffprobe


class MainWindow:
    """Main application window."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Video/Image Compressor")
        self.root.geometry("800x600")

        self.selected_files: List[str] = []
        self.config = {}
        self.config_path = os.path.join(
            os.path.dirname(__file__),
            '..', 'config', 'presets.json'
        )

        self._load_config()
        self._check_ffmpeg()
        self._create_widgets()
        self._create_menu()
        self._setup_drag_drop()

    def _load_config(self):
        """Load configuration from file."""
        try:
            import json
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = self._get_default_config()
        except Exception:
            self.config = self._get_default_config()

    def _get_default_config(self):
        """Get default configuration."""
        return {
            'video': {
                'low': {'crf': 28, 'preset': 'slow', 'audio_bitrate': '128k'},
                'medium': {'crf': 23, 'preset': 'medium', 'audio_bitrate': '192k'},
                'high': {'crf': 18, 'preset': 'fast', 'audio_bitrate': '320k'}
            },
            'image': {
                'low': {'quality': 70},
                'medium': {'quality': 80},
                'high': {'quality': 90}
            },
            'output': {
                'use_common_output': False,
                'common_output_path': '',
                'default_subdirectory': 'compressed_output',
                'preserve_original': True
            },
            'ffmpeg': {'path': '', 'threads': 0}
        }

    def _check_ffmpeg(self):
        """Check if FFmpeg is available."""
        ffmpeg_path = self.config.get('ffmpeg', {}).get('path', '')
        self.ffmpeg_available = find_ffprobe(ffmpeg_path) is not None

    def _create_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings", command=self._show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _create_widgets(self):
        """Create main window widgets."""
        # Top frame for file selection
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        # Add files button
        ttk.Button(
            top_frame,
            text="Add Files...",
            command=self._add_files,
            width=15
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Add folder button
        ttk.Button(
            top_frame,
            text="Add Folder...",
            command=self._add_folder,
            width=15
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Clear button
        ttk.Button(
            top_frame,
            text="Clear All",
            command=self._clear_files,
            width=15
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Remove Selected button
        ttk.Button(
            top_frame,
            text="Remove Selected",
            command=self._remove_selected,
            width=15
        ).pack(side=tk.LEFT)

        # FFmpeg status indicator
        self.ffmpeg_status = ttk.Label(
            top_frame,
            text="✓ FFmpeg" if self.ffmpeg_available else "✗ FFmpeg not found",
            foreground="green" if self.ffmpeg_available else "red"
        )
        self.ffmpeg_status.pack(side=tk.RIGHT)

        # File list frame
        list_frame = ttk.LabelFrame(self.root, text="Selected Files", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Treeview for file list
        columns = ('name', 'size', 'type', 'status')
        self.file_tree = ttk.Treeview(list_frame, columns=columns, show='headings', selectmode='extended')

        self.file_tree.heading('name', text='File Name')
        self.file_tree.heading('size', text='Size')
        self.file_tree.heading('type', text='Type')
        self.file_tree.heading('status', text='Status')

        self.file_tree.column('name', width=350)
        self.file_tree.column('size', width=100)
        self.file_tree.column('type', width=100)
        self.file_tree.column('status', width=100)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)

        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Define item tags for status coloring
        self.file_tree.tag_configure('pending', foreground='gray')
        self.file_tree.tag_configure('running', foreground='blue')
        self.file_tree.tag_configure('completed', foreground='green')
        self.file_tree.tag_configure('failed', foreground='red')
        self.file_tree.tag_configure('aborted', foreground='orange')

        # Bind keyboard events
        self.file_tree.bind('<Delete>', lambda e: self._remove_selected())
        self.file_tree.bind('<BackSpace>', lambda e: self._remove_selected())

        # Bind right-click for context menu
        self.file_tree.bind('<Button-3>', self._show_context_menu)

        # Bottom frame for options and actions
        bottom_frame = ttk.Frame(self.root, padding=10)
        bottom_frame.pack(fill=tk.X)

        # Compression level
        level_frame = ttk.Frame(bottom_frame)
        level_frame.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(level_frame, text="Compression Level:").pack(side=tk.LEFT)

        self.compression_level = tk.StringVar(value='medium')
        level_combo = ttk.Combobox(
            level_frame,
            textvariable=self.compression_level,
            values=['low', 'medium', 'high'],
            state='readonly',
            width=10
        )
        level_combo.pack(side=tk.LEFT, padx=(10, 0))

        # Output directory
        output_frame = ttk.Frame(bottom_frame)
        output_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(output_frame, text="Output:").pack(side=tk.LEFT)

        self.output_path = tk.StringVar()
        output_entry = ttk.Entry(output_frame, textvariable=self.output_path)
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))

        ttk.Button(
            output_frame,
            text="Browse...",
            command=self._browse_output,
            width=10
        ).pack(side=tk.LEFT)

        # Update output path display
        self._update_output_display()

        # Action buttons
        action_frame = ttk.Frame(bottom_frame)
        action_frame.pack(side=tk.RIGHT)

        ttk.Button(
            action_frame,
            text="Settings",
            command=self._show_settings,
            width=12
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.compress_button = ttk.Button(
            action_frame,
            text="Compress",
            command=self._start_compression,
            width=12
        )
        self.compress_button.pack(side=tk.LEFT)

    def _add_files(self):
        """Add individual files."""
        files = filedialog.askopenfilenames(
            title="Select Files",
            filetypes=[
                ("Media Files", "*.mp4 *.mov *.avi *.mkv *.jpg *.jpeg *.png *.webp"),
                ("Video Files", "*.mp4 *.mov *.avi *.mkv *.flv *.wmv"),
                ("Image Files", "*.jpg *.jpeg *.png *.webp"),
                ("All Files", "*.*")
            ]
        )
        if files:
            self._add_files_to_list(files)

    def _add_folder(self):
        """Add all files from a folder."""
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            # Get all media files in folder
            video_exts = VideoCompressor.SUPPORTED_EXTENSIONS
            image_exts = ImageCompressor.SUPPORTED_EXTENSIONS
            all_exts = video_exts + image_exts

            files = []
            for filename in os.listdir(folder):
                ext = os.path.splitext(filename)[1].lower()
                if ext in all_exts:
                    files.append(os.path.join(folder, filename))

            if files:
                self._add_files_to_list(files)
            else:
                messagebox.showinfo("No Files", "No supported media files found in this folder.")

    def _add_files_to_list(self, files):
        """Add files to the list."""
        for file_path in files:
            if file_path not in self.selected_files:
                self.selected_files.append(file_path)

                # Get file info
                size = os.path.getsize(file_path)
                size_str = self._format_size(size)

                # Detect type
                media_type = detect_media_type(file_path)
                type_str = {
                    MediaType.VIDEO: "Video",
                    MediaType.IMAGE: "Image",
                    MediaType.UNKNOWN: "Unknown"
                }.get(media_type, "Unknown")

                # Add to treeview
                self.file_tree.insert(
                    '', 
                    tk.END, 
                    values=(os.path.basename(file_path), size_str, type_str, "Pending"),
                    tags=('pending',)
                )

    def _clear_files(self):
        """Clear all selected files."""
        self.selected_files.clear()
        self.file_tree.delete(*self.file_tree.get_children())

    def _remove_selected(self):
        """Remove selected files from the list."""
        selected_items = self.file_tree.selection()
        if not selected_items:
            return

        # Get the indices of selected items
        indices_to_remove = []
        for item in selected_items:
            # Get the index of this item in the tree
            index = self.file_tree.index(item)
            indices_to_remove.append(index)

        # Remove from selected_files list (in reverse order to maintain indices)
        for index in sorted(indices_to_remove, reverse=True):
            if 0 <= index < len(self.selected_files):
                self.selected_files.pop(index)

        # Delete from treeview
        self.file_tree.delete(*selected_items)

    def _setup_drag_drop(self):
        """Setup drag and drop functionality."""
        try:
            from tkinterdnd2 import DND_FILES

            # Make the root window a drop target
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self._on_drop)
            self.root.dnd_bind('<<DragEnter>>', self._on_drag_enter)
            self.root.dnd_bind('<<DragLeave>>', self._on_drag_leave)

            # Also make the file treeview accept drops
            self.file_tree.drop_target_register(DND_FILES)
            self.file_tree.dnd_bind('<<Drop>>', self._on_drop)

            self.drag_drop_enabled = True
        except (ImportError, AttributeError):
            # Library not available or root not set up for DnD, silently skip
            self.drag_drop_enabled = False

    def _on_drop(self, event):
        """Handle file drop event."""
        # Extract file paths from the drop data
        data = event.data

        # tkinterdnd2 provides data in different formats
        if hasattr(event, 'data') and data:
            # Handle curly braces format on Windows (tkinterdnd2 format)
            if data.startswith('{') and '}' in data:
                files = self._parse_tkinterdnd2_paths(data)
            else:
                # Fallback: try splitting by whitespace/newlines
                files = [f.strip() for f in data.replace('\n', ' ').split() if f.strip()]

            # Remove any leading/trailing braces or quotes
            files = [f.strip('{}').strip('"').strip("'") for f in files]

            # Add valid files
            if files:
                valid_files = [f for f in files if os.path.exists(f)]
                if valid_files:
                    self._add_files_to_list(valid_files)

    def _parse_tkinterdnd2_paths(self, data: str) -> list:
        """Parse file paths from tkinterdnd2 drop data (Windows format)."""
        files = []
        current = ""
        in_braces = False

        for char in data:
            if char == '{':
                in_braces = True
                current = ""
            elif char == '}':
                if current:
                    files.append(current)
                current = ""
                in_braces = False
            elif char in ' \n\r' and not in_braces:
                # Skip whitespace outside braces
                continue
            else:
                current += char

        return files

    def _on_drag_enter(self, event):
        """Handle drag enter event - visual feedback."""
        self.file_tree.configure(selectbackground='#4a6fa5')

    def _on_drag_leave(self, event):
        """Handle drag leave event - restore visual."""
        self.file_tree.configure(selectbackground='#4a6fa5' if ttk.Style().theme_use() == 'vista' else '#c3c3c3')

    def _show_context_menu(self, event):
        """Show right-click context menu for file list."""
        # Select the item that was right-clicked
        item = self.file_tree.identify_row(event.y)
        if item:
            # If the item isn't already selected, select it
            selection = self.file_tree.selection()
            if item not in selection:
                self.file_tree.selection_set(item)

            # Create context menu
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label="Remove Selected", command=self._remove_selected)
            context_menu.add_separator()
            context_menu.add_command(label="Clear All", command=self._clear_files)

            # Show menu at cursor position
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()

    def _browse_output(self):
        """Browse for output directory."""
        path = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_path.get()
        )
        if path:
            self.output_path.set(path)

    def _update_output_display(self):
        """Update output path display based on config."""
        output_config = self.config.get('output', {})
        if output_config.get('use_common_output', False):
            common_path = output_config.get('common_output_path', '')
            self.output_path.set(common_path if common_path else os.getcwd())
        else:
            self.output_path.set(f"(Default: {output_config.get('default_subdirectory', 'compressed_output')})")

    def _format_size(self, bytes_size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} TB"

    def _show_settings(self):
        """Open settings dialog."""
        dialog = ConfigDialog(self.root, self.config_path, self.config)
        result = dialog.show()
        if result:
            self.config = result
            self._check_ffmpeg()
            self.ffmpeg_status.config(
                text="✓ FFmpeg" if self.ffmpeg_available else "✗ FFmpeg not found",
                foreground="green" if self.ffmpeg_available else "red"
            )
            self._update_output_display()

    def _show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About",
            "Video/Image Compressor\n\n"
            "A simple tool for compressing videos and images using FFmpeg.\n\n"
            "Supports:\n"
            "• Videos: MP4, MOV, AVI, MKV, and more\n"
            "• Images: JPG, PNG, WebP\n"
            "• Apple iPhone MOV files"
        )

    def _get_output_path(self, input_file: str) -> str:
        """Determine output path for a file."""
        output_config = self.config.get('output', {})
        use_common = output_config.get('use_common_output', False)

        basename = os.path.splitext(os.path.basename(input_file))[0]
        ext = os.path.splitext(input_file)[1]
        level = self.compression_level.get()

        if use_common:
            # Use common output directory with level suffix
            output_dir = output_config.get('common_output_path', '')
            if not output_dir:
                output_dir = os.getcwd()
            # For videos, convert to mp4; for images keep original format
            if ext.lower() in VideoCompressor.SUPPORTED_EXTENSIONS:
                ext = '.mp4'  # Convert to MP4
            filename = f"{basename}_{level}{ext}"
        else:
            # Use subdirectory in source folder
            output_dir = os.path.join(os.path.dirname(input_file), output_config.get('default_subdirectory', 'compressed_output'))
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.basename(input_file)

        return os.path.join(output_dir, filename)

    def _start_compression(self):
        """Start compression process."""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please add files to compress first.")
            return

        if not self.ffmpeg_available:
            messagebox.showerror(
                "FFmpeg Not Found",
                "FFmpeg is not installed or not in PATH.\n\n"
                "Please install FFmpeg and try again.\n"
                "You can configure the FFmpeg path in Settings."
            )
            return

        # Reset all file statuses to Pending
        for item_id in self.file_tree.get_children():
            values = list(self.file_tree.item(item_id, 'values'))
            if len(values) > 3:
                values[3] = "Pending"
                self.file_tree.item(item_id, values=values, tags=('pending',))

        # Disable compress button
        self.compress_button.config(state=tk.DISABLED)

        # Create progress dialog
        progress_dialog = ProgressDialog(
            self.root,
            "Compressing Files",
            on_abort=self._abort_compression
        )
        progress_dialog.set_start_time()

        # Store dialog reference for abort handler
        self._current_dialog = progress_dialog

        # Get output path
        output_dir = self.output_path.get()
        if output_dir.startswith("(Default:"):
            output_dir = None

        # Start compression in thread
        thread = threading.Thread(
            target=self._compression_thread,
            args=(progress_dialog, output_dir),
            daemon=True
        )
        thread.start()

        # Show dialog modally (this blocks until dialog is closed)
        progress_dialog.show()

        # Re-enable compress button after dialog closes
        self.compress_button.config(state=tk.NORMAL)

    def _abort_compression(self):
        """Abort compression process."""
        self._abort_requested = True
        # Set abort flag on both compressors - they will check it during compression
        if hasattr(self, 'video_compressor'):
            self.video_compressor.abort()
        if hasattr(self, 'image_compressor'):
            self.image_compressor.abort()

        # Update dialog immediately
        if hasattr(self, '_current_dialog'):
            try:
                if self._current_dialog.dialog.winfo_exists():
                    self._current_dialog.status_label.config(text="Aborting...")
                    self._current_dialog.abort_button.config(state=tk.DISABLED)
            except (tk.TclError, AttributeError):
                pass

    def _compression_thread(self, dialog: ProgressDialog, output_dir: str = None):
        """Compression thread."""
        # Reset abort flag at start
        self._abort_requested = False

        # Get item IDs for all files in the treeview
        tree_items = self.file_tree.get_children()

        def update_item_status(idx, status, tag):
            """Safely update treeview item status from thread."""
            if idx < len(tree_items):
                item_id = tree_items[idx]
                try:
                    # Get current values and update the status column (index 3)
                    values = list(self.file_tree.item(item_id, 'values'))
                    if len(values) > 3:
                        values[3] = status
                        self.file_tree.item(item_id, values=values, tags=(tag,))
                except tk.TclError:
                    pass

        ffmpeg_path = self.config.get('ffmpeg', {}).get('path', '')
        level = self.compression_level.get()

        # Create compressors
        self.video_compressor = VideoCompressor(ffmpeg_path)
        self.image_compressor = ImageCompressor(ffmpeg_path)

        total_files = len(self.selected_files)
        successful = 0
        failed = 0

        # Progress callback for current file
        def on_progress(progress):
            current_file = progress.current_file
            percentage = progress.get_percentage()
            status = progress.status

            # Update dialog with current file progress and file count
            self.root.after(0, lambda cf=current_file, p=percentage, s=status, idx=i+1, total=total_files:
                dialog.update_progress(int(p), 100, cf, s, file_count=f"{idx}/{total}"))

        # Set progress callbacks
        self.video_compressor.set_progress_callback(on_progress)
        self.image_compressor.set_progress_callback(on_progress)

        for i, file_path in enumerate(self.selected_files):
            # Check for abort at start of each file
            if self._abort_requested:
                # Mark remaining files as aborted
                for j in range(i, total_files):
                    self.root.after(0, lambda idx=j: update_item_status(idx, "Aborted", "aborted"))
                break

            # Mark current file as running
            self.root.after(0, lambda idx=i: update_item_status(idx, "Running", "running"))

            # Determine output path
            if output_dir:
                basename = os.path.splitext(os.path.basename(file_path))[0]
                ext = os.path.splitext(file_path)[1]
                # For videos, convert to mp4
                if ext.lower() in VideoCompressor.SUPPORTED_EXTENSIONS:
                    ext = '.mp4'
                output_file = os.path.join(output_dir, f"{basename}_{level}{ext}")
                os.makedirs(output_dir, exist_ok=True)
            else:
                output_file = self._get_output_path(file_path)

            # Update dialog to show new file starting
            def safe_update():
                try:
                    if dialog.dialog.winfo_exists():
                        dialog.update_progress(0, 100, os.path.basename(file_path), "running", file_count=f"{i+1}/{total_files}")
                except (tk.TclError, AttributeError):
                    pass
            self.root.after(0, safe_update)

            # Detect file type and compress
            media_type = detect_media_type(file_path)
            result = False

            try:
                if media_type == MediaType.VIDEO:
                    result = self.video_compressor.compress(
                        file_path,
                        output_file,
                        level,
                        self.config.get('video', {}).get(level, {})
                    )
                elif media_type == MediaType.IMAGE:
                    result = self.image_compressor.compress(
                        file_path,
                        output_file,
                        level,
                        self.config.get('image', {}).get(level, {})
                    )
                else:
                    # Try video compressor for unknown types
                    result = self.video_compressor.compress(
                        file_path,
                        output_file,
                        level,
                        self.config.get('video', {}).get(level, {})
                    )
            except Exception as e:
                print(f"Error compressing {file_path}: {e}")
                result = False

            # Check if aborted during compression
            if self._abort_requested:
                self.root.after(0, lambda idx=i: update_item_status(idx, "Aborted", "aborted"))
                # Mark remaining files as aborted
                for j in range(i + 1, total_files):
                    self.root.after(0, lambda idx=j: update_item_status(idx, "Aborted", "aborted"))
                break

            if result:
                successful += 1
                self.root.after(0, lambda idx=i: update_item_status(idx, "Completed", "completed"))
            else:
                failed += 1
                self.root.after(0, lambda idx=i: update_item_status(idx, "Failed", "failed"))

            # Check for errors (safely)
            video_error = getattr(self.video_compressor, 'progress', None)
            image_error = getattr(self.image_compressor, 'progress', None)
            if video_error and video_error.error:
                def safe_set_error():
                    try:
                        if dialog.dialog.winfo_exists():
                            dialog.set_error(video_error.error)
                    except (tk.TclError, AttributeError):
                        pass
                self.root.after(0, safe_set_error)
            elif image_error and image_error.error:
                def safe_set_error():
                    try:
                        if dialog.dialog.winfo_exists():
                            dialog.set_error(image_error.error)
                    except (tk.TclError, AttributeError):
                        pass
                self.root.after(0, safe_set_error)


        # Re-enable compress button
        self.root.after(0, lambda: self.compress_button.config(state=tk.NORMAL))

        # Update progress dialog to show completion or abort (safely)
        def safe_update_dialog():
            try:
                if dialog.dialog.winfo_exists():
                    if self._abort_requested:
                        dialog.update_progress(100, 100, "", "aborted", file_count=f"{successful + failed}/{total_files}")
                    else:
                        dialog.update_progress(100, 100, "", "completed", file_count=f"{total_files}/{total_files}")
            except (tk.TclError, AttributeError):
                pass

        self.root.after(0, safe_update_dialog)

        # Show completion message after a short delay (only if not aborted)
        if not self._abort_requested:
            def show_completion():
                time.sleep(0.5)

                def show_message():
                    try:
                        messagebox.showinfo(
                            "Compression Complete",
                            f"Processed {total_files} files\n"
                            f"Successful: {successful}\n"
                            f"Failed: {failed}"
                        )
                    except Exception:
                        pass

                # Close the progress dialog safely
                def close_dialog():
                    try:
                        if dialog.dialog.winfo_exists():
                            dialog.dialog.destroy()
                    except (tk.TclError, AttributeError):
                        pass

                self.root.after(0, show_message)
                self.root.after(0, close_dialog)

            threading.Thread(target=show_completion, daemon=True).start()
        else:
            # Just close the dialog if aborted
            def close_aborted():
                try:
                    if dialog.dialog.winfo_exists():
                        dialog.dialog.destroy()
                except (tk.TclError, AttributeError):
                    pass
            self.root.after(1000, close_aborted)
