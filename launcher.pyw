import os
import sys
import urllib.request
import urllib.parse
import subprocess
from tkinter import messagebox, Toplevel, Label, font
import tkinter as tk 

FILES_TO_DOWNLOAD = [
    ("https://github.com/sline35/mikiworkpermit/raw/refs/heads/main/SK%20BM.pdf", "docs/SK BM.pdf"),
    ("https://github.com/sline35/mikiworkpermit/raw/refs/heads/main/addition.pdf", "docs/addition.pdf"),
    ("https://github.com/sline35/mikiworkpermit/raw/refs/heads/main/preview_temp_output.pdf", "preview_temp_output.pdf"),
    ("https://github.com/sline35/mikiworkpermit/raw/refs/heads/main/main_app.pyw", "miki/main_app.pyw"),
    ("https://github.com/sline35/mikiworkpermit/raw/refs/heads/main/launcher.pyw", "launcher.pyw"),
    ("https://github.com/sline35/mikiworkpermit/raw/refs/heads/main/jsa_processor.py", "jsa_processor.py"),
]

MAIN_APP_NAME = "main_app.pyw"

def kill_existing_app():
    """실행 중인 메인 앱을 강제로 종료하여 파일 잠금을 해제합니다."""
    try:
        # main_app.pyw를 실행 중인 모든 프로세스 종료 (방화벽 무관)
        kill_cmd = 'wmic process where "commandline like \'%main_app.pyw%\'" delete'
        subprocess.run(kill_cmd, shell=True, capture_output=True)
        import time
        time.sleep(1) # 종료될 때까지 잠시 대기
    except:
        pass

def create_loading_window():
    root = tk.Tk()
    root.withdraw() 
    loading_win = Toplevel(root)
    loading_win.title("File Update")
    loading_win.attributes('-topmost', True)
    win_width, win_height = 300, 80
    x = (loading_win.winfo_screenwidth() // 2) - (win_width // 2)
    y = (loading_win.winfo_screenheight() // 2) - (win_height // 2)
    loading_win.geometry(f'{win_width}x{win_height}+{x}+{y}')
    loading_win.protocol("WM_DELETE_WINDOW", lambda: None) 
    Label(loading_win, text="✨ 업데이트를 위해 파일을 교체 중입니다...",
          font=font.Font(family="Helvetica", size=10, weight="bold")).pack(pady=20)
    
    # 중요: 창을 즉시 화면에 띄우기 위해 강제 업데이트
    root.update()
    loading_win.update()
    return root, loading_win

def download_and_run(root, loading_win):
    # 1. 파일 다운로드 전 기존 앱 먼저 종료 (덮어쓰기 가능하게 함)
    kill_existing_app()

    if getattr(sys, 'frozen', False):
        script_dir = os.path.dirname(sys.executable)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
    try:
        for url, relative_path in FILES_TO_DOWNLOAD:
            safe_url = urllib.parse.quote(url, safe=':/?&=')
            target_file_path = os.path.normpath(os.path.join(script_dir, relative_path))
            
            os.makedirs(os.path.dirname(target_file_path), exist_ok=True)

            req = urllib.request.Request(safe_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()
                # 2. 파일 쓰기 (기존 앱이 꺼졌으므로 정상 작동함)
                with open(target_file_path, 'wb') as out_file:
                    out_file.write(content)

        loading_win.destroy()
        root.destroy()
        
    except Exception as e:
        loading_win.destroy()
        root.destroy()
        messagebox.showerror("Update Error", f"파일 덮어쓰기 실패: {e}\n앱이 켜져있다면 수동으로 끄고 실행해주세요.")
        return

    try:
        # 3. 모든 작업 완료 후 메인 앱 실행
        main_app_path = os.path.join(script_dir, "miki", MAIN_APP_NAME)
        subprocess.Popen([sys.executable, main_app_path], cwd=os.path.join(script_dir, "miki"))
    except Exception as e:
        messagebox.showerror("Launch Error", f"실행 실패: {e}")

    sys.exit(0) 

def run_launcher():
    root, loading_win = create_loading_window()
    download_and_run(root, loading_win)

if __name__ == "__main__":
    run_launcher()
