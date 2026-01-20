import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import datetime
import json
import os
import sys
from config import GEMINI_API_KEY, TEMP_DIR_PATH, PDF_SAVE_DIR_PATH, GEMINI_MODEL_NAME, GEMINI_MODEL_LIST
import google.generativeai as genai
import fitz
import subprocess
import threading
from ttkbootstrap import Style
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import Frame, Label, Entry, Button, Combobox, Radiobutton
import uuid
import re
import jsa_processor
import subcontractor_gui 
import responsible_person_gui
import json_viewer_popup
import settings_popup
import shutil

def extract_subcontractor_name(subcontractor_full):
    if not subcontractor_full:
        return "NO_SUBCONTRACTOR"
        
    subcontractor_part = subcontractor_full.split(' - ')[0].strip()
    
    cleaned_name = re.sub(r'\s+', '_', subcontractor_part)
    cleaned_name = re.sub(r'[^\w가-힣]+', '', cleaned_name)
    
    return cleaned_name

def extract_manager_details(responsible_person_full_str):
    name = responsible_person_full_str
    phone = ""
    if not responsible_person_full_str:
        return name, phone

    m_phone = re.search(r"\(([^)]*)\)\s*$", responsible_person_full_str)
    if m_phone:
        phone = m_phone.group(1).strip()
        name = responsible_person_full_str[:m_phone.start()].strip()
    return name, phone

class JSAInputGUI:
    def __init__(self, master):
        self.style = Style(theme='cosmo')
        self.master = master
        master.title("📋 Work Permit Assistant for Miki 🐭")
        master.geometry("600x700")
    
        self.focusable_widgets = []

        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.generated_pdf_path = os.path.join(self.script_dir, "preview_temp_output.pdf")
      
        self.generated_json_path = os.path.join(self.script_dir, "preview_temp_output.json")
        
        self.subcontractor_file = os.path.join(self.script_dir, "sub_contractors.txt")
    
        self.manager_file = os.path.join(self.script_dir, "site_responsible_persons.txt")
        
        self.prompt_json_path = os.path.join(self.script_dir, "gemini_prompt_input.json")
        self.temp_dir = TEMP_DIR_PATH
        self.pdf_save_dir = PDF_SAVE_DIR_PATH
        self.model_name = GEMINI_MODEL_NAME
    
        self.model_list = GEMINI_MODEL_LIST
        self.jsa_json = None

        # --- [NEW] In-memory PDF preview storage + local preview server state ---
        self.current_pdf_bytes = None
        self._preview_server_started = False
        self._preview_port = 8765
        # ----------------------------------------------------------------------
        
        os.makedirs(self.temp_dir, exist_ok=True)
   
        os.makedirs(self.pdf_save_dir, exist_ok=True)

        genai.configure(api_key=GEMINI_API_KEY)
        
        main_frame = Frame(master, padding=15)
        
        main_frame.pack(fill=BOTH, expand=True)

        input_frame = Frame(main_frame)
        input_frame.pack(fill=X, pady=(0, 10))
 
        input_frame.columnconfigure(1, weight=1)

        today = datetime.date.today()
    
        Label(input_frame, text="Company", font=("Helvetica", 10)).grid(row=0, 
        column=0, padx=(0, 5), pady=3, sticky="w")
        company_frame = Frame(input_frame)
        company_frame.grid(row=0, column=1, pady=3, sticky="ew")
      
        company_frame.columnconfigure(0, weight=1)
        self.company_var = tk.StringVar(value="SK BM")
        
        radio_frame = Frame(company_frame)
       
        radio_frame.grid(row=0, column=0, sticky="w")
        
        sk_bm_btn = Radiobutton(radio_frame, text="SK BM", variable=self.company_var, value="SK BM")
    
        sk_bm_btn.pack(side=LEFT, padx=(5, 10))
        
        settings_button = Button(company_frame, text="⚙️", command=self.open_settings_popup, bootstyle=INFO, width=3)
      
        settings_button.grid(row=0, column=1, padx=(5, 0), sticky="e")

        self.focusable_widgets.extend([sk_bm_btn, settings_button])        
        
        Label(input_frame, text="Building & Floor", font=("Helvetica", 10)).grid(row=1, column=0, padx=(0, 5), pady=3, sticky="w")
 
        building_floor_frame = Frame(input_frame)
        building_floor_frame.grid(row=1, column=1, pady=3, sticky="ew")
        
        building_floor_frame.columnconfigure(1, weight=1)
        building_floor_frame.columnconfigure(3, weight=1)

        Label(building_floor_frame, text="Building number", font=("Helvetica", 10)).grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.building_entry = Entry(building_floor_frame, bootstyle=PRIMARY, font=("Helvetica", 10))
 
        self.building_entry.grid(row=0, column=1, sticky="ew")
        
      
        Label(building_floor_frame, text="Floor and room number", font=("Helvetica", 10)).grid(row=0, column=2, padx=(5, 5), sticky="w")
        
        self.floor_entry = Entry(building_floor_frame, bootstyle=PRIMARY, font=("Helvetica", 10))
        self.floor_entry.grid(row=0, column=3, sticky="ew")
        
        
        self.focusable_widgets.extend([self.building_entry, self.floor_entry])

        self.create_date_input_fields(input_frame, 2, "Creation Date", 
        "creation", today)
        self.create_date_input_fields(input_frame, 3, "Start Date", "start", today)
        self.create_date_input_fields(input_frame, 4, "End Date", "end", today)
        
        fire_alarm_frame = Frame(input_frame)
        fire_alarm_frame.grid(row=5, column=1, pady=3, sticky="ew")
        Label(input_frame, text="Fire Alarm (ASD) Off", font=("Helvetica", 10)).grid(row=5, column=0, sticky="w", padx=(0, 5), pady=3)

        self.fire_alarm_var = tk.StringVar(value="NO")
 
        
      
        yes_button = Radiobutton(fire_alarm_frame, text="YES", 
        variable=self.fire_alarm_var, value="YES")
        yes_button.pack(side=LEFT, padx=(5, 20))
        
        no_button = Radiobutton(fire_alarm_frame, text="NO", variable=self.fire_alarm_var, value="NO")
        no_button.pack(side=LEFT, padx=(0, 5))
        
        self.focusable_widgets.extend([yes_button, no_button])

        
        responsible_frame = Frame(input_frame)
        responsible_frame.grid(row=6, column=1, pady=3, sticky="ew")
 
        responsible_frame.columnconfigure(0, weight=1)
  
        Label(input_frame, text="Subcontractor", font=("Helvetica", 10)).grid(row=6, column=0, padx=(0, 5), pady=3, sticky="w")
        
        self.subcontractors_list = self.load_persons(self.subcontractor_file) 
        self.subcontractor_combobox = Combobox(responsible_frame, bootstyle=PRIMARY, font=("Helvetica", 10), values=self.subcontractors_list)
        self.subcontractor_combobox.grid(row=0, column=0, sticky="ew")
    
        self.focusable_widgets.append(self.subcontractor_combobox)
        
        
        settings_button = Button(responsible_frame, text="⚙️", command=self.open_subcontractor_manager, bootstyle=INFO, width=3)
 
        settings_button.grid(row=0, column=1, padx=(5, 0))
        self.focusable_widgets.append(settings_button)

        
        Label(input_frame, text="Responsible Person", font=("Helvetica", 10)).grid(row=7, column=0, padx=(0, 5), pady=3, sticky="w")
        manager_frame = Frame(input_frame)
        manager_frame.grid(row=7, column=1, pady=3, sticky="ew")
        
        manager_frame.columnconfigure(0, weight=1)      
        
  
        self.managers_list = self.load_persons(self.manager_file)
        self.responsible_person_manager_combobox = Combobox(manager_frame, bootstyle=PRIMARY, font=("Helvetica", 10), values=self.managers_list)
        self.responsible_person_manager_combobox.grid(row=0, column=0, sticky="ew")
        self.focusable_widgets.append(self.responsible_person_manager_combobox)
        
        
        manager_settings_button = Button(manager_frame, text="⚙️", 
        command=self.open_manager_manager, bootstyle=INFO, width=3)
        manager_settings_button.grid(row=0, column=1, padx=(5, 0))
        self.focusable_widgets.append(manager_settings_button)
   
        
        Label(input_frame, text="Permit to Work", font=("Helvetica", 10)).grid(row=8, column=0, padx=(0, 5), pady=3, sticky="w")
        permit_frame = Frame(input_frame)
        permit_frame.grid(row=8, column=1, pady=3, sticky="ew")
        
 
        self.fire_permit_var = tk.BooleanVar()
        self.enclosed_permit_var = tk.BooleanVar()
        
        self.heavy_machinery_permit_var = tk.BooleanVar()
 
        self.electrical_permit_var = tk.BooleanVar()
        self.high_place_permit_var = tk.BooleanVar()
        self.hazardous_material_permit_var = tk.BooleanVar()

        fire_check = tk.Checkbutton(permit_frame, text="Fire", variable=self.fire_permit_var, onvalue=True, offvalue=False)
        fire_check.pack(side=tk.LEFT, padx=(5, 5))
        
        self.focusable_widgets.append(fire_check)
        
        enclosed_check = tk.Checkbutton(permit_frame, text="Confined Space", variable=self.enclosed_permit_var, onvalue=True, offvalue=False)
        
        enclosed_check.pack(side=tk.LEFT, padx=(5, 5))
    
        self.focusable_widgets.append(enclosed_check)

        heavy_machinery_check = tk.Checkbutton(permit_frame, text="Heavy Machinery", variable=self.heavy_machinery_permit_var, onvalue=True, offvalue=False)
        heavy_machinery_check.pack(side=tk.LEFT, padx=(5, 5))
        self.focusable_widgets.append(heavy_machinery_check)

        
        permit_frame2 = Frame(input_frame)
        permit_frame2.grid(row=9, column=1, pady=3, sticky="ew")

        electrical_check = tk.Checkbutton(permit_frame2, text="Electrical", variable=self.electrical_permit_var, onvalue=True, offvalue=False)
        electrical_check.pack(side=tk.LEFT, padx=(5, 
        5))
        self.focusable_widgets.append(electrical_check)

        high_place_check = tk.Checkbutton(permit_frame2, text="Work at Height", variable=self.high_place_permit_var, onvalue=True, offvalue=False)
        high_place_check.pack(side=tk.LEFT, padx=(5, 5))
        self.focusable_widgets.append(high_place_check)

        hazardous_material_check = tk.Checkbutton(permit_frame2, text="Hazardous Materials", variable=self.hazardous_material_permit_var, onvalue=True, offvalue=False)
        
        hazardous_material_check.pack(side=tk.LEFT, padx=(5, 5))
        self.focusable_widgets.append(hazardous_material_check)
        
        
 
        self.create_multiline_label_entry(input_frame, 10, "Task Description", "task_description", height=5)
        
        button_frame = Frame(main_frame)
    
        button_frame.pack(fill=X, pady=(10, 5))
        
        self.start_button = Button(button_frame, text="✅ Generate", command=self.start_generation, bootstyle=SUCCESS, 
        width=12)
        self.start_button.pack(side=LEFT, expand=True, padx=(0, 5))
        self.focusable_widgets.append(self.start_button)
      
        self.save_button = Button(button_frame, text="💾 Save JSON", command=self.save_as_file, bootstyle=INFO, width=12)
        self.save_button.pack(side=LEFT, expand=True, padx=(0, 5))

        self.load_button = Button(button_frame, text="📂 Load", command=self.open_json_viewer_popup, bootstyle=PRIMARY, width=12)
 
        self.load_button.pack(side=LEFT, expand=True, padx=5)
        self.focusable_widgets.append(self.load_button)

        self.pdf_save_button = Button(button_frame, 
        text="📝 Save PDF", command=self.save_pdf_as_file, bootstyle=INFO, width=12)
        self.pdf_save_button.pack(side=LEFT, expand=True, padx=(0, 5))
  
        self.focusable_widgets.append(self.pdf_save_button)

        # 수정: regenerate_pdf 함수 바인딩
        self.reopen_button = Button(button_frame, text="📄 Open PDF", command=self.regenerate_pdf, state=tk.NORMAL, bootstyle=INFO, width=12)
        self.reopen_button.pack(side=RIGHT, expand=True, padx=(5, 0))
        self.focusable_widgets.append(self.reopen_button)
        
    
        status_label = Label(main_frame, text="Logs & Progress", font=("Helvetica", 10, "bold"))
        status_label.pack(fill=X, pady=(5, 0))
 
        self.status_text = scrolledtext.ScrolledText(main_frame, height=15, width=100, font=("Helvetica", 9), wrap=tk.WORD)
    
        self.status_text.pack(fill=BOTH, expand=True, padx=0, pady=(5, 0))
        
        self.master.bind_all("<Tab>", self._manual_focus_next)
        self.master.bind_all("<Shift-Tab>", self._manual_focus_prev)
        
        
        if self.subcontractors_list:
            self.subcontractor_combobox.set(self.subcontractors_list[0])
        
        if self.managers_list:
            
            self.responsible_person_manager_combobox.set(self.managers_list[0])

    # --- [NEW] Local in-memory PDF preview server helpers ---
    def _ensure_preview_server(self):
        if self._preview_server_started:
            return

        from http.server import HTTPServer, BaseHTTPRequestHandler

        gui = self

        class _MemPDFHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                path = self.path.split('?', 1)[0]
                if path != "/preview.pdf":
                    self.send_response(404)
                    self.end_headers()
                    return

                data = gui.current_pdf_bytes or b""
                if not data:
                    self.send_response(204)
                    self.end_headers()
                    return

                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
                self.send_header("Pragma", "no-cache")
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, format, *args):
                return

        def _run():
            httpd = HTTPServer(("127.0.0.1", self._preview_port), _MemPDFHandler)
            httpd.serve_forever()

        threading.Thread(target=_run, daemon=True).start()
        self._preview_server_started = True

    def _open_pdf_preview_in_browser(self):
        import time
        url = f"http://127.0.0.1:{self._preview_port}/preview.pdf?ts={int(time.time()*1000)}"
        try:
            if sys.platform == "win32":
                os.system(f'start "" "{url}"')
            elif sys.platform == "darwin":
                subprocess.Popen(["open", url])
            else:
                subprocess.Popen(["xdg-open", url])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open preview: {e}")
    # -------------------------------------------------------

    def create_date_input_fields(self, parent, row, label_text, attr_prefix, default_date):
        date_frame = Frame(parent)
 
        date_frame.grid(row=row, column=1, pady=3, sticky="ew")
        Label(parent, text=label_text, font=("Helvetica", 10)).grid(row=row, column=0, padx=(0, 5), pady=3, sticky="w")
        
        year_entry = Entry(date_frame, width=6, bootstyle=PRIMARY, font=("Helvetica", 10))
        year_entry.pack(side=LEFT, padx=(0, 2))
      
        Label(date_frame, text="Year", font=("Helvetica", 10)).pack(side=LEFT)
   
        month_entry = Entry(date_frame, width=4, bootstyle=PRIMARY, font=("Helvetica", 
        10))
        month_entry.pack(side=LEFT, padx=(2, 
        2))
        Label(date_frame, text="Month", font=("Helvetica", 10)).pack(side=LEFT)
        day_entry = Entry(date_frame, width=4, bootstyle=PRIMARY, font=("Helvetica", 10))
        day_entry.pack(side=LEFT, padx=(2, 2))
        Label(date_frame, text="Day", font=("Helvetica", 10)).pack(side=LEFT)

        year_entry.insert(0, 
        
        default_date.year)
        month_entry.insert(0, f"{default_date.month:02d}")
        day_entry.insert(0, f"{default_date.day:02d}")

        setattr(self, f"{attr_prefix}_year_entry", year_entry)
        
        setattr(self, f"{attr_prefix}_month_entry", 
        month_entry)
        setattr(self, f"{attr_prefix}_day_entry", day_entry)
        self.focusable_widgets.extend([year_entry, month_entry, day_entry])

    
    def load_persons(self, file_path):
    
        try:
    
            persons = []
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        
         
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split(',')
   
                        
                        if len(parts) >= 3:
                            
    
                            company = parts[0].strip()
                            name = parts[1].strip()
                            phone = ','.join(parts[2:]).strip()
              
                        elif len(parts) == 2 and file_path == self.manager_file:
                            
                            company = ""
         
        
                            name = parts[0].strip()
                            phone = parts[1].strip()
                        else:
         
                            continue
                        

                        if company and phone:
  
                            display_text = f"{company} - {name} ({phone})"
                        elif company:
                        
                            display_text = f"{company} - {name}"
                        
    
                        elif phone:
                            
           
                            display_text = f"{name} ({phone})"
              
                        else:
                            display_text = name

            
                        persons.append(display_text)
            return persons
        except Exception as e:
            
            return []

    
    def update_combobox(self, combobox_widget, file_path, new_list):
        combobox_widget['values'] = new_list
        
        if new_list:
            combobox_widget.set(new_list[0])
        else:
            combobox_widget.set("")
 
            
        
        
        if file_path == self.subcontractor_file:
            self.subcontractors_list = new_list
        elif file_path == self.manager_file:
   
            self.managers_list = new_list

    
    def open_subcontractor_manager(self):
        def update_callback(new_list):
 
            self.update_combobox(self.subcontractor_combobox, self.subcontractor_file, new_list)
            
        
        manager_window = subcontractor_gui.ResponsiblePersonManager(
            self, self.subcontractor_file, update_callback
        )
    
        manager_window.grab_set()

    
    def open_manager_manager(self):
    
        def update_callback(new_list):
            self.update_combobox(self.responsible_person_manager_combobox, self.manager_file, new_list)
            
        
        manager_window = responsible_person_gui.ResponsiblePersonManager(
            self, self.manager_file, update_callback
        )
        
        manager_window.grab_set()

    def open_json_viewer_popup(self):
        json_viewer_popup.JSONViewerPopup(self.master, self)

    # 수정: 불필요한 줄바꿈 및 공백 제거
    def _manual_focus_next(self, event):
        focused_widget = self.master.focus_get()
        if isinstance(focused_widget, tk.Text):
            for widget in self.focusable_widgets:
                if isinstance(widget, scrolledtext.ScrolledText) and widget.winfo_children()[0] == focused_widget:
                    focused_widget = widget
                    break
        try:
            current_index = self.focusable_widgets.index(focused_widget)
            next_index = (current_index + 1) % len(self.focusable_widgets)
            self.focusable_widgets[next_index].focus_set()
        except ValueError:
            self.focusable_widgets[0].focus_set()
        
        return "break"

    # 수정: 불필요한 줄바꿈 및 공백 제거
    def _manual_focus_prev(self, event):
        focused_widget = self.master.focus_get()
        if isinstance(focused_widget, tk.Text):
            for widget in self.focusable_widgets:
                if isinstance(widget, scrolledtext.ScrolledText) and widget.winfo_children()[0] == focused_widget:
                    focused_widget = widget
                    break
        try:
            current_index = self.focusable_widgets.index(focused_widget)
            prev_index = (current_index - 1 + len(self.focusable_widgets)) % len(self.focusable_widgets)
            self.focusable_widgets[prev_index].focus_set()
        except ValueError:
            self.focusable_widgets[-1].focus_set()
        return "break"

    
    def create_grid_label_entry(self, parent, row, label_text, 
    attr_name, default=""):
        label = Label(parent, text=label_text, width=20, anchor="w", font=("Helvetica", 10))
        label.grid(row=row, column=0, padx=(0, 5), pady=3, sticky="w")
   
        entry = Entry(parent, bootstyle=PRIMARY, font=("Helvetica", 10))
        entry.insert(0, default)
        entry.grid(row=row, column=1, pady=3, sticky="ew")
        setattr(self, attr_name + "_entry", entry)
        self.focusable_widgets.append(entry)

    def create_multiline_label_entry(self, parent, row, label_text, attr_name, height=1, default=""):
        label = Label(parent, text=label_text, width=20, anchor=tk.N, font=("Helvetica", 10))
        label.grid(row=row, column=0, padx=(0, 5), pady=3, sticky="w")
        entry = scrolledtext.ScrolledText(parent, 
        height=height, undo=True, font=("Helvetica", 10))
        entry.grid(row=row, column=1, pady=3, sticky="ew")
        entry.configure(font=("Helvetica", 10))
        if default:
            entry.insert("1.0", default)
        setattr(self, attr_name + "_entry", entry)
        self.focusable_widgets.append(entry)
        entry.bind("<Control-z>", lambda event: entry.edit_undo())
        entry.bind("<Return>", lambda event: self.start_generation() or "break") 

    # 수정: 파일 열기 기능만 수행하도록 이름 변경
    def _open_pdf_file(self):
        if not os.path.exists(self.generated_pdf_path):
            messagebox.showwarning("Warning", "PDF not yet generated.")
            return

        
        try:
            command = self._get_open_command()
            if sys.platform == "win32":
                subprocess.Popen(command, shell=True)
            else:
                subprocess.Popen(command)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open PDF: {e}")

    def _get_open_command(self):
     
        if sys.platform == "win32": 
            return f'start "" "{self.generated_pdf_path}"' 
        elif sys.platform == "darwin": 
            return ["open", self.generated_pdf_path] 
        else: 
            return ["xdg-open", self.generated_pdf_path] 

    def _get_combined_date(self, attr_prefix):
        try:
            
            year_entry = getattr(self, f"{attr_prefix}_year_entry")
            month_entry = getattr(self, f"{attr_prefix}_month_entry")
            day_entry = getattr(self, f"{attr_prefix}_day_entry")
            year = year_entry.get().zfill(4)
            month = month_entry.get().zfill(2)
            day = day_entry.get().zfill(2)
            return f"{year}-{month}-{day}"
        except Exception:
   
            return ""

    def get_user_inputs(self):
        return { 
            "task_description": self.task_description_entry.get("1.0", "end-1c"), 
            "company": self.company_var.get(), 
            "building": self.building_entry.get(), 
            "floor": self.floor_entry.get(), 
            "subcontractor_full": self.subcontractor_combobox.get(), 
    
            "responsible_person_manager_full": self.responsible_person_manager_combobox.get(), 
            "creation_date": self._get_combined_date("creation"), 
            "start_date": self._get_combined_date("start"), 
            "end_date": self._get_combined_date("end"), 
            "fire_alarm_status": self.fire_alarm_var.get(), 
            "permits": { 
                "fire": self.fire_permit_var.get(), 
  
                "enclosed": self.enclosed_permit_var.get(), 
                "heavy_machinery": self.heavy_machinery_permit_var.get(), 
                "electrical": self.electrical_permit_var.get(), 
                "high_place": self.high_place_permit_var.get(), 
                "hazardous_material": self.hazardous_material_permit_var.get() 
            
            } 
        } 

    def _generate_json_filename(self, user_inputs, gemini_response):
        try:
            start_date_full = user_inputs.get("start_date", "")
            start_date_yy_mm_dd = start_date_full[2:] if len(start_date_full) == 10 else "NO_DATE"
            company = user_inputs.get("company", "NO_COMPANY").replace(" ", "_")
            building = user_inputs.get("building", "NO_BUILDING").replace(" ", "_")
      
            subcontractor_full = user_inputs.get("subcontractor_full", "")
            subcontractor_part = extract_subcontractor_name(subcontractor_full)
            work_details_en = gemini_response.get("WORK DETAILS EN", "NO_TASK")
            work_details_sanitized = re.sub(r'[^a-zA-Z0-9가-힣\s_-]', '', work_details_en).strip()
            work_details_sanitized = work_details_sanitized.replace(" ", "_")
            if len(work_details_sanitized) > 100:
             
                work_details_sanitized = work_details_sanitized[:100]
            unique_code = uuid.uuid4().hex[:6]
            filename = f"{start_date_yy_mm_dd}-{company}-{building}-{subcontractor_part}-{work_details_sanitized}-{unique_code}.json"
            return filename
        except Exception:
            return f"Error_File_{uuid.uuid4().hex[:6]}.json"

    def save_as_file(self):
        user_inputs = self.get_user_inputs()
        if not user_inputs.get("start_date") or not user_inputs.get("company") or not user_inputs.get("building"):
 
            messagebox.showwarning("Warning", "Date, company, and building are required to save the file.") 
            return
        if not self.jsa_json: 
            messagebox.showwarning("Warning", "You must click 'Generate' before saving the file.") 
            return
        combined_data = { 
           
            "user_inputs": user_inputs, 
            "gemini_response": self.jsa_json 
        } 
        try: 
            filename = self._generate_json_filename(user_inputs, self.jsa_json)
        except Exception as e: 
            messagebox.showerror("Error", f"Error creating filename: {e}\nSome required JSON fields may be missing.") 
            return
   
        save_path = os.path.join(self.temp_dir, filename) 
        try: 
            with open(save_path, "w", encoding="utf-8") as f: 
                json.dump(combined_data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Saved", f"'{filename}' has been successfully saved to TEMP folder.") 
        except Exception as e: 
            
            messagebox.showerror("Error", f"Error saving file: {e}")

    # --- [MODIFIED] Save PDF from in-memory bytes (no preview file copy) ---
    def save_pdf_as_file(self):
        if not self.current_pdf_bytes:
            messagebox.showwarning("Warning", "You must generate the PDF first.")
            return

        try:
            user_inputs = self.get_user_inputs()
            if self.jsa_json:
                pdf_filename = self._generate_json_filename(user_inputs, self.jsa_json).replace(".json", ".pdf")
            else:
                pdf_filename = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S") + ".pdf"
        except:
            pdf_filename = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S") + ".pdf"

        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=pdf_filename,
            initialdir=self.pdf_save_dir
        )
        
        if save_path:
            try:
                with open(save_path, "wb") as f:
                    f.write(self.current_pdf_bytes)
                messagebox.showinfo("Saved", f"PDF has been successfully saved as '{os.path.basename(save_path)}'.")
            except Exception as e:
                messagebox.showerror("Error", f"Error saving PDF file: {e}")
    # ---------------------------------------------------------------------

    # 수정: PDF를 재생성하고 여는 새 함수 구현
    def regenerate_pdf(self):
        if not self.jsa_json:
            messagebox.showwarning("Warning", "No JSON data loaded. Please use '✅ Generate' first or '📂 Load' a saved JSON.")
            return
        threading.Thread(target=self._thread_regenerate_pdf).start()
        
    def _thread_regenerate_pdf(self):
        self.master.after(0, lambda: self.status_text.insert(tk.END, "🔄 Re-generating PDF with current inputs and loaded JSON data...\n"))
        self.master.after(0, lambda: self.reopen_button.config(state=tk.DISABLED))
        
        user_inputs = self.get_user_inputs()
        
        subcontractor_data_string = user_inputs.get("subcontractor_full", "")
        manager_full_str = user_inputs.get("responsible_person_manager_full", "")
        responsible_name, responsible_phone = extract_manager_details(manager_full_str)
        
        try:
            jsa_pdf_path, template_json_path = jsa_processor.get_file_paths(self.script_dir, user_inputs['company'])
            
            doc = jsa_processor.insert_to_pdf(
                self.master, 
                self.script_dir, 
                self.jsa_json, # 로드된 JSON 데이터 사용
                user_inputs.get("creation_date", ""), 
                user_inputs.get("start_date", ""), 
                user_inputs.get("end_date", ""), 
                user_inputs.get("company", ""), 
                user_inputs.get("building", ""), 
                user_inputs.get("floor", ""),
                
                subcontractor_data_string, 
                responsible_name, 
                responsible_phone, 
                
                user_inputs.get("fire_alarm_status", "NO"),
                user_inputs.get("permits", {}),
                jsa_pdf_path, 
                template_json_path
            )

            if doc:
                self.master.after(0, lambda: self.status_text.insert(tk.END, "📄 PDF regeneration successful. Building in-memory preview...\n"))
                try:
                    try:
                        pdf_bytes = doc.tobytes(garbage=3, deflate=True)
                    except Exception:
                        pdf_bytes = doc.write()

                    self.current_pdf_bytes = pdf_bytes

                    self._ensure_preview_server()
                    self.master.after(0, lambda: self.status_text.insert(tk.END, "🌐 Opening in-memory PDF preview in browser...\n"))
                    self.master.after(0, self._open_pdf_preview_in_browser)
                except Exception as e:
                    self.master.after(0, lambda e=e: messagebox.showerror("Error", f"Error occurred while building PDF preview: {e}"))
                    self.master.after(0, lambda e=e: self.status_text.insert(tk.END, f"❌ Error: {e}\n"))
            else:
                self.master.after(0, lambda: self.status_text.insert(tk.END, "❌ PDF document object is None.\n"))

        except Exception as e:
            self.master.after(0, lambda e=e: messagebox.showerror("Error", f"An unexpected error occurred during PDF regeneration: {e}"))
            self.master.after(0, lambda e=e: self.status_text.insert(tk.END, f"❌ Unexpected error during regeneration: {e}\n"))
            
        finally: 
            self.master.after(0, lambda: self.reopen_button.config(state=tk.NORMAL))


    def start_generation(self):
        threading.Thread(target=self._thread_generate).start()

    def _thread_generate(self):
        self.master.after(0, lambda: self.status_text.insert(tk.END, "🚀 Starting generation...\n"))
        self.master.after(0, lambda: self.reopen_button.config(state=tk.DISABLED))
        
        user_inputs = self.get_user_inputs()
        
        subcontractor_data_string = user_inputs.get("subcontractor_full", "")
        
        manager_full_str = user_inputs.get("responsible_person_manager_full", "")
 
        responsible_name, responsible_phone = extract_manager_details(manager_full_str)
        

        if not user_inputs.get("task_description"):
            self.master.after(0, lambda: messagebox.showerror("Input Error", "Task Description is required."))
            self.master.after(0, lambda: self.status_text.insert(tk.END, "❌ Task Description missing.\n"))
            self.master.after(0, lambda: self.reopen_button.config(state=tk.NORMAL))
            return
         
        
        if not user_inputs.get("company"):
            self.master.after(0, lambda: messagebox.showerror("Input Error", "Company selection is required."))
            self.master.after(0, lambda: self.status_text.insert(tk.END, "❌ Company selection missing.\n"))
            self.master.after(0, lambda: self.reopen_button.config(state=tk.NORMAL))
            return

        try:
            model = genai.GenerativeModel(self.model_name)
  
            
            with open(self.prompt_json_path, 'r', encoding='utf-8') as f:
                prompt_data = json.load(f)

            prompt_data["TASK DESCRIPTION"] = user_inputs["task_description"]
            
            prompt_text = json.dumps(prompt_data, ensure_ascii=False, indent=4)
            
 
            self.master.after(0, lambda: self.status_text.insert(tk.END, "🧠 Calling Gemini API...\n"))
            response = model.generate_content(prompt_text)
            
            if response.text.strip().startswith('{') and response.text.strip().endswith('}'):
                self.jsa_json = json.loads(response.text.strip())
            else:
           
                self.master.after(0, lambda: messagebox.showerror("API Error", "Gemini response is not a valid JSON string."))
                self.master.after(0, lambda: self.status_text.insert(tk.END, f"❌ Gemini response invalid. Output: {response.text[:50]}...\n"))
                self.master.after(0, lambda: self.reopen_button.config(state=tk.NORMAL))
                return

            self.master.after(0, lambda: self.status_text.insert(tk.END, "✅ Gemini API call successful.\n"))
            self.master.after(0, self.save_as_file)
            jsa_pdf_path, template_json_path = jsa_processor.get_file_paths(self.script_dir, user_inputs['company'])
            
            doc = jsa_processor.insert_to_pdf(
    
                self.master, 
                self.script_dir, 
                self.jsa_json, 
                user_inputs.get("creation_date", ""), 
                user_inputs.get("start_date", ""), 
                user_inputs.get("end_date", 
                ""), 
                user_inputs.get("company", ""), 
                user_inputs.get("building", ""), 
                user_inputs.get("floor", ""),
                
                subcontractor_data_string, 
             
                responsible_name, 
                responsible_phone, 
                
                user_inputs.get("fire_alarm_status", "NO"),
                user_inputs.get("permits", {}),
                jsa_pdf_path, 
            
                template_json_path
            )

            if doc:
                self.master.after(0, lambda: self.status_text.insert(tk.END, "📄 PDF generation successful. Building in-memory preview...\n"))
                try:
                    try:
                        pdf_bytes = doc.tobytes(garbage=3, deflate=True)
                    except Exception:
                        pdf_bytes = doc.write()

                    self.current_pdf_bytes = pdf_bytes

                    self._ensure_preview_server()
                    self.master.after(0, lambda: self.status_text.insert(tk.END, "🌐 Opening in-memory PDF preview in browser...\n"))
                    self.master.after(0, self._open_pdf_preview_in_browser)
                except Exception as e:
                    self.master.after(0, lambda e=e: messagebox.showerror("Error", f"Error occurred while building PDF preview: {e}"))
                    self.master.after(0, lambda e=e: self.status_text.insert(tk.END, f"❌ Error: {e}\n"))
            else:
                self.master.after(0, lambda: self.status_text.insert(tk.END, "❌ PDF document object is None.\n"))

        except Exception as e:
            self.master.after(0, 
            lambda e=e: messagebox.showerror("Error", f"An unexpected error occurred: {e}"))
            self.master.after(0, lambda e=e: self.status_text.insert(tk.END, f"❌ Unexpected error: {e}\n"))
        
        finally: 
            self.master.after(0, lambda: self.reopen_button.config(state=tk.NORMAL))

    def run(self):
        self.master.mainloop()

    def open_settings_popup(self):
        settings_popup.SettingsPopup(self.master, self).grab_set()
        
    def update_settings(self, new_temp_path, new_pdf_save_path, 
        new_model_name, new_model_list):
        self.temp_dir = new_temp_path
        self.pdf_save_dir = new_pdf_save_path
        self.model_name = new_model_name
        self.model_list = new_model_list
      
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.pdf_save_dir, exist_ok=True)
        
if __name__ == "__main__":
    root = tk.Tk()
    app = JSAInputGUI(root)
    app.run()
