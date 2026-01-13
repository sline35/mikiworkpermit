import os
import sys
import zipfile
import urllib.request
import subprocess
from tkinter import messagebox, Toplevel, Label, font
import tkinter as tk 
import time
import threading

MASTER_ZIP_URL = "https://github.com/sline35/mikiworkpermit/raw/refs/heads/main/miki.zip" 
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
        
    temp_zip_path = os.path.join(script_dir, "master_update.zip")
    
    loading_win.update()

    try:
        req = urllib.request.Request(
            MASTER_ZIP_URL, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        
        with urllib.request.urlopen(req, timeout=30) as response, open(temp_zip_path, 'wb') as out_file:
            out_file.write(response.read())

        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(script_dir) 

        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)

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
        main_app_path = os.path.join(script_dir, MAIN_APP_NAME)
        subprocess.Popen([sys.executable, main_app_path], cwd=script_dir) 
    except Exception as e:
        messagebox.showerror("Launch Error", f"Main app failed to run: {e}")
        sys.exit(1)

    sys.exit(0) 

def run_launcher():
    root, loading_win = create_loading_window()
    download_and_run(root, loading_win)

if __name__ == "__main__":
    run_launcher()
