import os
import sys
import json
import fitz
from tkinter import messagebox
import re

def get_file_paths(script_dir, company_name):
    jsa_pdf_path = os.path.join(script_dir, "docs", f"{company_name}.pdf")
    template_json_path = os.path.join(script_dir, "docs", f"{company_name}.json")
    return jsa_pdf_path, template_json_path

def draw_rect_on_pdf(page_obj, coords, scale):
    scaled_rect = fitz.Rect(
        coords["x0"] * scale,
        coords["y0"] * scale,
        coords["x1"] * scale,
        coords["y1"] * scale
    )
    page_obj.draw_rect(scaled_rect, color=(0, 0, 0), width=1)

def insert_to_pdf(
    master, 
    script_dir, 
    jsa_json, 
    creation_date, 
    start_date, 
    end_date, 
    company, 
    building, 
    floor, 
    subcontractor_full, 
    responsible_name, 
    responsible_phone, 
    fire_alarm_status, 
    permits, 
    jsa_pdf_path, 
    template_json_path
):
    try:
        def _parse_person_display(s: str):
            comp, name, phone = "", "", ""
            if not s:
                return comp, name, phone
            m_phone = re.search(r"\(([^)]*)\)\s*$", s)
            if m_phone:
                phone = m_phone.group(1).strip()
                s = s[:m_phone.start()].strip()
            if " - " in s:
                comp, name = s.split(" - ", 1)
                comp, name = comp.strip(), name.strip()
            else:
                name = s.strip()
            return comp, name, phone

        sub_comp, sub_person, sub_phone = _parse_person_display(subcontractor_full)

        with open(template_json_path, "r", encoding="utf-8") as f:
            template = json.load(f)

        doc = fitz.open()
        resource_dir = os.path.join(script_dir, "docs")

        for i in range(1, 7):
            img_name = f"SK_BM-{i}.png"
            img_path = os.path.join(resource_dir, img_name)
            if os.path.exists(img_path):
                img_doc = fitz.open(img_path)
                rect = img_doc[0].rect
                page = doc.new_page(width=rect.width, height=rect.height)
                page.insert_image(rect, filename=img_path)
                img_doc.close()

        font_path = os.path.join(script_dir, "fonts", "DejaVuSans.ttf")
        times_font_path = os.path.join(script_dir, "fonts", "times.ttf")
        font_file = os.path.join(script_dir, "fonts", "NanumGothic.ttf")

        if os.path.exists(font_file):
            doc.insert_font(fontfile=font_file, fontname="NanumGothic")

        if os.path.exists(font_path):
            for page in doc:
                page.insert_font(fontname="DejaVuSans", fontfile=font_path)

        if os.path.exists(times_font_path):
            for page in doc:
                page.insert_font(fontname="times", fontfile=times_font_path)

        default_font = "DejaVuSans"
        default_font_size = 5
        times_font = "times"
        times_font_size = 12

        fields_by_page = template["fields"]
        scale = 1 / 5

        hazard_types_str = jsa_json.get("HAZARD TYPES", "")
        ppe_str = jsa_json.get("PPE", "")

        hazard_list = [h.strip() for h in hazard_types_str.split(',')] if hazard_types_str else []
        ppe_list = [p.strip() for p in ppe_str.split(',')] if ppe_str else []

        status_check = fire_alarm_status

        for page_num_str, page_fields in fields_by_page.items():
            page_num = int(page_num_str) - 1
            if page_num < len(doc):
                page_obj = doc[page_num]

                if page_num in [3, 4]:
                    page_default_font = times_font
                    page_default_font_size = times_font_size
                else:
                    page_default_font = default_font
                    page_default_font_size = default_font_size

                for field_name, coords_data in page_fields.items():
                    current_font = page_default_font
                    current_font_size = page_default_font_size
                    text_to_insert = ""
                    text_align = 1

                    if field_name.startswith(("A","B","C","D","E","F","G","H","I","J","K")) and field_name[1:].isdigit():
                        text_to_insert = jsa_json.get(field_name, "")
                        if field_name.startswith(("A","D","E","F","G","I","J","K")):
                            current_font_size = 5
                        elif field_name.startswith(("B","C","H")):
                            current_font_size = 4

                    elif page_num in [0,3] and field_name == "work details":
                        en = jsa_json.get("WORK DETAILS EN", "")
                        hu = jsa_json.get("WORK DETAILS HU", "")
                        if en and hu:
                            text_to_insert = f"{en}\n{hu}"
                        else:
                            text_to_insert = en or hu

                    elif field_name == "work details en" and page_num == 1:
                        text_to_insert = jsa_json.get("WORK DETAILS EN", "")
                    elif field_name == "work details hu" and page_num == 2:
                        text_to_insert = jsa_json.get("WORK DETAILS HU", "")
                    elif field_name == "work name en":
                        text_to_insert = jsa_json.get("WORK NAME EN", "")
                    elif field_name == "work name hu":
                        text_to_insert = jsa_json.get("WORK NAME HU", "")
                    elif field_name == "place":
                        text_to_insert = f"{company}  {building}  {floor}"
                    elif field_name == "creation date":
                        text_to_insert = creation_date
                    elif field_name == "work expiration time":
                        text_to_insert = end_date
                    elif field_name == "work date":
                        text_to_insert = start_date if start_date == end_date else f"{start_date}\n~ {end_date}"
                    elif page_num == 3 and field_name == "start_end":
                        text_to_insert = start_date if start_date == end_date else f"{start_date} - {end_date}"
                    elif field_name == "start":
                        text_to_insert = start_date
                    elif field_name == "end":
                        text_to_insert = end_date
                    elif field_name == "building":
                        text_to_insert = building
                        if page_num == 3:
                            text_align = 0
                    elif field_name == "floor":
                        text_to_insert = floor
                        if page_num == 3:
                            text_align = 0
                    elif field_name == "YEAR" and page_num == 3:
                        text_to_insert = creation_date[:4] if creation_date and len(creation_date) >= 4 else ""
                        text_align = 0
                        current_font_size = 10
                    elif field_name in hazard_list or field_name in ppe_list:
                        text_to_insert = "▣"
                    elif (page_num == 0 and field_name == "subcontractor") or page_num in [1,2,3,4]:
                        text_align = 0
                        if field_name == "subcontractor" and page_num == 0:
                            text_to_insert = sub_person
                        elif field_name == "name":
                            text_to_insert = sub_person
                        elif field_name == "phone":
                            text_to_insert = sub_phone
                        elif field_name == "company":
                            text_to_insert = sub_comp
                        elif field_name == "responsible_name":
                            text_to_insert = responsible_name
                        elif field_name == "responsible_phone":
                            text_to_insert = responsible_phone

                    coords_list = coords_data if isinstance(coords_data, list) else [coords_data]

                    for coords in coords_list:
                        is_asd_field = (
                            (field_name == "asd_yes" and status_check == "YES") or
                            (field_name == "asd_no" and status_check == "NO")
                        )
                        if is_asd_field:
                            if page_num == 3:
                                draw_rect_on_pdf(page_obj, coords, scale)
                            continue

                        if text_to_insert:
                            scaled_rect = fitz.Rect(
                                coords["x0"] * scale,
                                coords["y0"] * scale,
                                coords["x1"] * scale,
                                coords["y1"] * scale
                            )
                            page_obj.insert_textbox(
                                scaled_rect,
                                text_to_insert,
                                fontname=current_font,
                                fontsize=current_font_size,
                                align=text_align
                            )

        if permits:
            permit_pages_map = {
                "fire": (1, 2),
                "enclosed": (3, 4),
                "heavy_machinery": (5, 6),
                "electrical": (7, 8),
                "high_place": (9, 10),
                "hazardous_material": (11, 12)
            }

            for permit_type, page_range in permit_pages_map.items():
                if permits.get(permit_type, False):
                    for p_num in range(page_range[0], page_range[1] + 1):
                        img_name = f"addition-{p_num:02d}.png"
                        img_path = os.path.join(resource_dir, img_name)
                        if os.path.exists(img_path):
                            img_doc = fitz.open(img_path)
                            rect = img_doc[0].rect
                            page = doc.new_page(width=rect.width, height=rect.height)
                            page.insert_image(rect, filename=img_path)
                            img_doc.close()

        return doc

    except Exception as e:
        master.after(0, lambda: messagebox.showerror("PDF Error", f"Error while processing PDF: {e}"))
        return None
