"""Video/Image Compressor - Main entry point."""
import tkinter as tk
import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gui.main_window import MainWindow


def main():
    """Main application entry point."""
    root = tk.Tk()
    root.title("Video/Image Compressor")

    # Set window icon if available
    try:
        icon_path = os.path.join(project_root, 'icon.ico')
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass

    # Create main window
    app = MainWindow(root)

    # Handle window close
    def on_closing():
        root.quit()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Start the application
    root.mainloop()


if __name__ == "__main__":
    main()
