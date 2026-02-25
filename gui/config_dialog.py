"""Configuration dialog for application settings."""
import tkinter as tk
from tkinter import ttk, filedialog
import json
import os


class ConfigDialog:
    """Settings dialog for compressor configuration."""

    def __init__(self, parent: tk.Tk, config_path: str, current_config: dict):
        self.parent = parent
        self.config_path = config_path
        self.config = current_config.copy()
        self.result = None

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("600x550")
        self.dialog.resizable(False, False)

        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (450 // 2)
        self.dialog.geometry(f"+{x}+{y}")

        self._create_widgets()

    def _create_widgets(self):
        """Create dialog widgets."""
        # Main frame with padding
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # General tab
        general_frame = ttk.Frame(notebook, padding=15)
        notebook.add(general_frame, text="General")
        self._create_general_tab(general_frame)

        # Video tab
        video_frame = ttk.Frame(notebook, padding=15)
        notebook.add(video_frame, text="Video")
        self._create_video_tab(video_frame)

        # Image tab
        image_frame = ttk.Frame(notebook, padding=15)
        notebook.add(image_frame, text="Image")
        self._create_image_tab(image_frame)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(20, 0))

        # Save button
        ttk.Button(
            button_frame,
            text="Save",
            command=self._save,
            width=12
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Cancel button
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.dialog.destroy,
            width=12
        ).pack(side=tk.LEFT)

    def _create_general_tab(self, parent):
        """Create general settings tab."""
        # Output settings frame
        output_frame = ttk.LabelFrame(parent, text="Output Settings", padding=10)
        output_frame.pack(fill=tk.X, pady=(0, 15))

        # Use common output directory
        self.use_common_output = tk.BooleanVar(
            value=self.config.get('output', {}).get('use_common_output', False)
        )
        ttk.Checkbutton(
            output_frame,
            text="Use common output directory",
            variable=self.use_common_output
        ).pack(anchor=tk.W, pady=(0, 10))

        # Common output path
        path_frame = ttk.Frame(output_frame)
        path_frame.pack(fill=tk.X)

        ttk.Label(path_frame, text="Common output path:").pack(anchor=tk.W)

        self.common_path_entry = ttk.Entry(path_frame)
        self.common_path_entry.pack(
            fill=tk.X,
            pady=(5, 0)
        )
        self.common_path_entry.insert(
            0,
            self.config.get('output', {}).get('common_output_path', '')
        )

        ttk.Button(
            path_frame,
            text="Browse...",
            command=self._browse_output_path,
            width=10
        ).pack(anchor=tk.W, pady=(5, 0))

        # Default subdirectory
        subdir_frame = ttk.Frame(output_frame)
        subdir_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(subdir_frame, text="Default subdirectory:").pack(anchor=tk.W)

        self.subdir_entry = ttk.Entry(subdir_frame)
        self.subdir_entry.pack(fill=tk.X, pady=(5, 0))
        self.subdir_entry.insert(
            0,
            self.config.get('output', {}).get('default_subdirectory', 'compressed_output')
        )

        # File handling
        file_frame = ttk.LabelFrame(parent, text="File Handling", padding=10)
        file_frame.pack(fill=tk.X)

        self.preserve_original = tk.BooleanVar(
            value=self.config.get('output', {}).get('preserve_original', True)
        )
        ttk.Checkbutton(
            file_frame,
            text="Preserve original files",
            variable=self.preserve_original
        ).pack(anchor=tk.W)

        # FFmpeg settings frame
        ffmpeg_frame = ttk.LabelFrame(parent, text="FFmpeg Settings", padding=10)
        ffmpeg_frame.pack(fill=tk.X, pady=(15, 0))

        path_frame2 = ttk.Frame(ffmpeg_frame)
        path_frame2.pack(fill=tk.X)

        ttk.Label(path_frame2, text="FFmpeg path (optional):").pack(anchor=tk.W)

        self.ffmpeg_path_entry = ttk.Entry(path_frame2)
        self.ffmpeg_path_entry.pack(fill=tk.X, pady=(5, 0))
        self.ffmpeg_path_entry.insert(
            0,
            self.config.get('ffmpeg', {}).get('path', '')
        )

        ttk.Button(
            path_frame2,
            text="Browse...",
            command=self._browse_ffmpeg_path,
            width=10
        ).pack(anchor=tk.W, pady=(5, 0))

    def _create_video_tab(self, parent):
        """Create video settings tab."""
        video_config = self.config.get('video', {})

        for level in ['low', 'medium', 'high']:
            level_frame = ttk.LabelFrame(
                parent,
                text=f"{level.capitalize()} Quality",
                padding=10
            )
            level_frame.pack(fill=tk.X, pady=(0, 10))

            level_data = video_config.get(level, {})

            # CRF
            crf_frame = ttk.Frame(level_frame)
            crf_frame.pack(fill=tk.X, pady=(0, 5))

            ttk.Label(crf_frame, text="CRF (Quality):").pack(side=tk.LEFT)
            crf_var = tk.IntVar(value=level_data.get('crf', 23))
            setattr(self, f'video_crf_{level}', crf_var)

            crf_scale = ttk.Scale(
                crf_frame,
                from_=0,
                to=51,
                variable=crf_var,
                orient=tk.HORIZONTAL,
                length=200
            )
            crf_scale.pack(side=tk.LEFT, padx=(10, 5))

            crf_label = ttk.Label(crf_frame, textvariable=crf_var, width=5)
            crf_label.pack(side=tk.LEFT)

            # Preset
            preset_frame = ttk.Frame(level_frame)
            preset_frame.pack(fill=tk.X, pady=(5, 0))

            ttk.Label(preset_frame, text="Preset:").pack(side=tk.LEFT)

            preset_var = tk.StringVar(value=level_data.get('preset', 'medium'))
            setattr(self, f'video_preset_{level}', preset_var)

            preset_combo = ttk.Combobox(
                preset_frame,
                textvariable=preset_var,
                values=['veryslow', 'slow', 'medium', 'fast', 'faster', 'veryfast'],
                state='readonly',
                width=15
            )
            preset_combo.pack(side=tk.LEFT, padx=(10, 0))

            # Audio bitrate
            audio_frame = ttk.Frame(level_frame)
            audio_frame.pack(fill=tk.X, pady=(5, 0))

            ttk.Label(audio_frame, text="Audio bitrate:").pack(side=tk.LEFT)

            audio_var = tk.StringVar(value=level_data.get('audio_bitrate', '192k'))
            setattr(self, f'video_audio_{level}', audio_var)

            ttk.Combobox(
                audio_frame,
                textvariable=audio_var,
                values=['64k', '96k', '128k', '192k', '256k', '320k'],
                state='readonly',
                width=10
            ).pack(side=tk.LEFT, padx=(10, 0))

    def _create_image_tab(self, parent):
        """Create image settings tab."""
        image_config = self.config.get('image', {})

        for level in ['low', 'medium', 'high']:
            level_frame = ttk.LabelFrame(
                parent,
                text=f"{level.capitalize()} Quality",
                padding=10
            )
            level_frame.pack(fill=tk.X, pady=(0, 10))

            level_data = image_config.get(level, {})

            quality_frame = ttk.Frame(level_frame)
            quality_frame.pack(fill=tk.X)

            ttk.Label(quality_frame, text="Quality:").pack(side=tk.LEFT)

            quality_var = tk.IntVar(value=level_data.get('quality', 80))
            setattr(self, f'image_quality_{level}', quality_var)

            quality_scale = ttk.Scale(
                quality_frame,
                from_=1,
                to=100,
                variable=quality_var,
                orient=tk.HORIZONTAL,
                length=200
            )
            quality_scale.pack(side=tk.LEFT, padx=(10, 5))

            quality_label = ttk.Label(quality_frame, textvariable=quality_var, width=5)
            quality_label.pack(side=tk.LEFT)

    def _browse_output_path(self):
        """Browse for output directory."""
        path = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.common_path_entry.get()
        )
        if path:
            self.common_path_entry.delete(0, tk.END)
            self.common_path_entry.insert(0, path)

    def _browse_ffmpeg_path(self):
        """Browse for FFmpeg directory."""
        path = filedialog.askdirectory(
            title="Select FFmpeg Directory",
            initialdir=self.ffmpeg_path_entry.get()
        )
        if path:
            self.ffmpeg_path_entry.delete(0, tk.END)
            self.ffmpeg_path_entry.insert(0, path)

    def _save(self):
        """Save configuration and close dialog."""
        # Build new config
        new_config = {
            'video': {},
            'image': {},
            'output': {
                'use_common_output': self.use_common_output.get(),
                'common_output_path': self.common_path_entry.get(),
                'default_subdirectory': self.subdir_entry.get(),
                'preserve_original': self.preserve_original.get()
            },
            'ffmpeg': {
                'path': self.ffmpeg_path_entry.get(),
                'threads': 0
            }
        }

        # Video settings
        for level in ['low', 'medium', 'high']:
            new_config['video'][level] = {
                'crf': getattr(self, f'video_crf_{level}').get(),
                'preset': getattr(self, f'video_preset_{level}').get(),
                'audio_bitrate': getattr(self, f'video_audio_{level}').get(),
                'codec': 'libx264',
                'output_format': 'mp4'
            }

        # Image settings
        for level in ['low', 'medium', 'high']:
            new_config['image'][level] = {
                'quality': getattr(self, f'image_quality_{level}').get()
            }

        # Save to file
        try:
            with open(self.config_path, 'w') as f:
                json.dump(new_config, f, indent=2)
            self.result = new_config
            self.dialog.destroy()
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to save configuration: {e}")

    def show(self):
        """Show the dialog."""
        self.dialog.wait_window()
        return self.result
