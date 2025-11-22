import os
import shutil
import streamlit as st
from datetime import datetime
import requests

# Optional Windows-only printing
try:
    import win32api
    import win32print
    WIN_PRINTERS_AVAILABLE = True
except Exception:
    WIN_PRINTERS_AVAILABLE = False

# ---------------- CONFIG ----------------
BASE_FOLDER = "Printed_Files"
os.makedirs(BASE_FOLDER, exist_ok=True)

ADMIN_ID = "Sabuj@"
ADMIN_PASS = "sabuj"

# WhatsApp Cloud API config (replace with your credentials)
WHATSAPP_TOKEN = "YOUR_WHATSAPP_TOKEN_HERE"
WHATSAPP_PHONE_NUMBER_ID = "YOUR_PHONE_NUMBER_ID_HERE"

# ----------------- HELPERS -----------------
def list_printers():
    if not WIN_PRINTERS_AVAILABLE:
        return ["(No local printers - win32 not available)"]
    return [p[2] for p in win32print.EnumPrinters(2)]


def try_print_pdf(filepath, printer_name):
    if not WIN_PRINTERS_AVAILABLE:
        return False, "Win32 printing not available on this environment."
    try:
        win32api.ShellExecute(0, "printto", filepath, f'"{printer_name}"', ".", 0)
        return True, None
    except Exception as e:
        return False, str(e)


def send_whatsapp(phone, message):
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        return False
    url = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message}
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        return r.status_code in (200, 201)
    except Exception:
        return False


# ----------------- STATE -----------------
if 'UPLOAD_QUEUE' not in st.session_state:
    st.session_state.UPLOAD_QUEUE = []
if 'serial_counter' not in st.session_state:
    st.session_state.serial_counter = 1


# ----------------- UI -----------------
st.set_page_config(page_title="PDF Upload & Print (Streamlit)", layout="wide")
st.title("DUSC printing system — Streamlit edition")

col1, col2 = st.columns([2, 1])

with col1:
    name = st.text_input("Name")
    phone = st.text_input("WhatsApp Phone (+CountryCodeNumber)")
    uploaded_file = st.file_uploader("Select PDF File", type=["pdf"])
    add_btn = st.button("Add to Queue")

    if add_btn:
        if not name or not phone or uploaded_file is None:
            st.warning("Please provide Name, Phone, and a PDF file.")
        else:
            serial = st.session_state.serial_counter
            folder_name = f"{serial}_{name.replace(' ', '')}"
            folder_path = os.path.join(BASE_FOLDER, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            filename = uploaded_file.name
            target_file = os.path.join(folder_path, filename)
            # write uploaded file to disk
            with open(target_file, "wb") as f:
                f.write(uploaded_file.getbuffer())

            item = {
                "serial": serial,
                "name": name,
                "phone": phone,
                "folder": folder_path,
                "file": target_file,
                "status": "queued",
                "added_at": datetime.now().isoformat()
            }
            st.session_state.UPLOAD_QUEUE.append(item)
            st.session_state.serial_counter += 1
            st.success(f"File queued (Serial: {serial})")

with col2:
    st.markdown("**Developer**")
    st.write("Md Shahriar Hasan Sabuj — AI can do anything")

st.markdown("---")

# Display queue
st.subheader("Current Queue")
if st.session_state.UPLOAD_QUEUE:
    display_rows = []
    for it in st.session_state.UPLOAD_QUEUE:
        status_text = "Queued" if it['status']=='queued' else "✅ Printed"
        display_rows.append({
            "Serial": it['serial'],
            "Name": it['name'],
            "File": os.path.basename(it['file']),
            "Phone": it['phone'],
            "Status": status_text,
            "Added At": it['added_at']
        })
    st.dataframe(display_rows)
else:
    st.info("Queue is empty.")

st.markdown("---")

# Admin panel
with st.expander("Admin Panel — Login required"):
    sid = st.text_input("Admin ID")
    spass = st.text_input("Password", type="password")
    login = st.button("Login as Admin")

    if login:
        if sid.strip() == ADMIN_ID and spass.strip() == ADMIN_PASS:
            st.success("Admin authenticated")

            printers = list_printers()
            selected_printer = st.selectbox("Select Printer", printers)

            serials = [str(x['serial']) for x in st.session_state.UPLOAD_QUEUE]
            chosen = st.multiselect("Select items to manage (by Serial)", serials)

            colp, cold = st.columns(2)
            with colp:
                if st.button("Print Selected"):
                    if not chosen:
                        st.warning("Select at least one serial to print.")
                    else:
                        for s in chosen:
                            item = next((x for x in st.session_state.UPLOAD_QUEUE if str(x['serial'])==s), None)
                            if item and item['status']=='queued':
                                success, err = try_print_pdf(item['file'], selected_printer)
                                if success:
                                    item['status'] = 'printed'
                                    send_whatsapp(item['phone'], f"Your document (Serial {item['serial']}) has been printed successfully.")
                                    try:
                                        if os.path.exists(item['folder']):
                                            shutil.rmtree(item['folder'])
                                    except Exception:
                                        pass
                        st.experimental_rerun()

            with cold:
                if st.button("Delete Selected"):
                    if not chosen:
                        st.warning("Select at least one serial to delete.")
                    else:
                        for s in chosen:
                            item = next((x for x in st.session_state.UPLOAD_QUEUE if str(x['serial'])==s), None)
                            if item:
                                try:
                                    if os.path.exists(item['folder']):
                                        shutil.rmtree(item['folder'])
                                except Exception:
                                    pass
                                st.session_state.UPLOAD_QUEUE.remove(item)
                        st.success("Selected items deleted")
                        st.experimental_rerun()

        else:
            st.error("Incorrect admin credentials.")

st.markdown("---")
st.caption("Note: Local Windows printing requires win32 api. WhatsApp notifications require a valid WhatsApp Cloud API token.")