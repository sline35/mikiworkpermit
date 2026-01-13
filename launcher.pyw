import os
import sys
import zipfile
import urllib.request
import urllib.parse
import subprocess
from tkinter import messagebox, Toplevel, Label, font
import tkinter as tk 
import time
import threading

FILES_TO_DOWNLOAD = [
    ("https://github.com/sline35/mikiworkpermit/raw/refs/heads/main/SK BM.pdf", "docs/SK BM.pdf"),
    ("https://github.com/sline35/mikiworkpermit/raw/refs/heads/main/addition.pdf", "docs/addition.pdf"),
    ("https://github.com/sline35/mikiworkpermit/raw/refs/heads/main/preview_temp_output.pdf", "preview_temp_output.pdf"),
    ("https://github.com/sline35/mikiworkpermit/raw/refs/heads/main/main_app.pyw", "main_app.pyw"),
    ("https://github.com/sline35/mikiworkpermit/raw/refs/heads/main/launcher.pyw", "launcher.pyw"),
    ("https://github.com/sline35/mikiworkpermit/raw/refs/heads/main/jsa_processor.py", "jsa_processor.py"),
]

MAIN_APP_NAME = "main_app.pyw"

def create_loading_window():
    root = tk.Tk()
    root.withdraw() 
    
    loading_win = Toplevel(root)
    loading_win.title("File Update")
    loading_win.attributes('-topmost', True)

    win_width = 300
    win_height = 80
    screen_width = loading_win.winfo_screenwidth()
    screen_height = loading_win.winfo_screenheight()
    x = (screen_width // 2) - (win_width // 2)
    y = (screen_height // 2) - (win_height // 2)
    loading_win.geometry(f'{win_width}x{win_height}+{x}+{y}')
    
    loading_win.protocol("WM_DELETE_WINDOW", lambda: None) 

    Label(loading_win, 
          text="✨ Updating important files. Please wait...",
          font=font.Font(family="Helvetica", size=10, weight="bold")
    ).pack(pady=20)
    
    loading_win.update()
    return root, loading_win

def download_and_run(root, loading_win):
    if getattr(sys, 'frozen', False):
        script_dir = os.path.dirname(sys.executable)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
    main_app_dir = os.path.join(script_dir, "miki")
    
    if not os.path.exists(main_app_dir):
        os.makedirs(main_app_dir)
        
    loading_win.update()

    try:
        for url, relative_path in FILES_TO_DOWNLOAD:
            safe_url = urllib.parse.quote(url, safe=':/?&=')
            
            target_file_path = os.path.join(main_app_dir, relative_path)
            
            target_sub_dir = os.path.dirname(target_file_path)
            if not os.path.exists(target_sub_dir):
                os.makedirs(target_sub_dir)

            req = urllib.request.Request(
                safe_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response, open(target_file_path, 'wb') as out_file:
                out_file.write(response.read())

        loading_win.destroy()
        root.destroy()
        
    except Exception as e:
        loading_win.destroy()
        root.destroy()
        messagebox.showerror("Launcher Error", f"File restoration and update failed: {e}\n"
                                               f"Check network connection and Google Drive sharing settings.")
        sys.exit(1)
        return

    try:
        main_app_path = os.path.join(main_app_dir, MAIN_APP_NAME)
        subprocess.Popen([sys.executable, main_app_path], cwd=main_app_dir)
    except Exception as e:
        messagebox.showerror("Launch Error", f"Main app failed to run: {e}")
        sys.exit(1)

    sys.exit(0) 

def run_launcher():
    root, loading_win = create_loading_window()
    download_and_run(root, loading_win)

if __name__ == "__main__":
    run_launcher()
