import re
import os
import csv
import socket
import base64
from datetime import datetime
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Molino 1 Filtering System", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS: WATERMARK ---
st.markdown(
    """
    <style>
    .watermark {
        position: fixed;
        bottom: 10px;
        right: 15px;
        font-size: 14px;
        color: rgba(150, 150, 150, 0.7);
        font-weight: bold;
        z-index: 9999;
    }
    </style>
    <div class="watermark">Made By China</div>
    """,
    unsafe_allow_html=True
)

# --- DISABLE 'CTRL + C' CLEAR CACHE POPUP ---
components.html(
    """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.key === 'c' || e.key === 'C') {
            e.stopPropagation();
        }
    }, true);
    </script>
    """,
    height=0,
    width=0,
)

# --- FILE PATHS ---
DATA_FILE = "molino1_saved_data.csv"
CONFIG_FILE = "molino1_config.txt"
LOGS_FILE = "system_logs.csv"

# --- AUTHENTICATION & LOGGING LOGIC ---
def get_local_ip():
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except:
        return "Unknown IP"

def log_system_access(name, role):
    ip_addr = get_local_ip()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_data = pd.DataFrame([{"Timestamp": timestamp, "Name": name, "Role": role, "IP Address": ip_addr}])
    
    if os.path.exists(LOGS_FILE):
        log_data.to_csv(LOGS_FILE, mode='a', header=False, index=False)
    else:
        log_data.to_csv(LOGS_FILE, index=False)

def is_fake_name(name):
    lower_name = name.lower().strip()
    forbidden_words = ["test", "admin123", "bot", "ai", "admin", "user", "guest"]
    
    # Check if exact forbidden word
    if lower_name in forbidden_words:
        return True
    # Check if it contains numbers
    if any(char.isdigit() for char in name):
        return True
    # Check length
    if len(lower_name) < 2:
        return True
        
    return False

# --- SMART LOGIN MODAL ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['role'] = None
    st.session_state['user_name'] = ""

if not st.session_state['logged_in']:
    # Adding some vertical space to center the "modal"
    st.write("<br><br><br>", unsafe_allow_html=True)
    
    # Using columns to create a centered "modal" card look
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h2 style='text-align: center;'>System Authentication</h2>", unsafe_allow_html=True)
        st.warning("⚠️ **NOTICE:** You must input your REAL NAME to access this system. Aliases, numbers, or fake names (e.g., 'test', 'bot') will be rejected and logged.")
        
        # Single Smart Input Box
        user_input = st.text_input("Enter your Name:")
        
        if st.button("Enter System", use_container_width=True, type="primary"):
            if not user_input:
                st.error("Please enter a value.")
            elif user_input == "091401":
                # Admin bypass
                st.session_state['logged_in'] = True
                st.session_state['role'] = "Admin"
                st.session_state['user_name'] = "Administrator"
                log_system_access("Administrator", "Admin")
                st.rerun()
            elif is_fake_name(user_input):
                # Fake name detection for Users
                st.error("Access Denied: Invalid or fake name detected. Please use your real full name (No numbers allowed).")
                log_system_access(f"FAILED LOGIN: {user_input}", "Rejected")
            else:
                # Valid User login
                st.session_state['logged_in'] = True
                st.session_state['role'] = "User"
                st.session_state['user_name'] = user_input.title()
                log_system_access(user_input.title(), "User")
                st.rerun()
                
    st.stop() # Stops the rest of the code from running until logged in

# --- AUTO-LOAD SAVED SESSION ON STARTUP ---
if 'processed_df' not in st.session_state and os.path.exists(DATA_FILE) and os.path.exists(CONFIG_FILE):
    try:
        st.session_state['processed_df'] = pd.read_csv(DATA_FILE)
        with open(CONFIG_FILE, "r") as f:
            st.session_state['address_col'] = f.read().strip()
    except Exception as e:
        st.error("Error loading saved session. The file might be corrupted.")

# --- SIDEBAR NAVIGATION ---
def display_circular_logo(image_path):
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            
        html_code = f"""
        <div style="display: flex; justify-content: center; margin-bottom: 20px;">
            <img src="data:image/jpeg;base64,{encoded_string}" 
                 style="width: 150px; height: 150px; border-radius: 50%; object-fit: cover; box-shadow: 0px 4px 6px rgba(0,0,0,0.3);">
        </div>
        """
        st.sidebar.markdown(html_code, unsafe_allow_html=True)
    except FileNotFoundError:
        pass

display_circular_logo("449958530_878918900941660_1079343009849520447_n (2).jpg")

st.sidebar.success(f"Logged in as: **{st.session_state['user_name']}** ({st.session_state['role']})")

# Dynamically build sidebar based on role
nav_pages = ["Home", "Dashboard", "Filtering"]
if st.session_state['role'] == "Admin":
    nav_pages.append("System Logs")

page = st.sidebar.radio("", nav_pages)

if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()

# --- FILTERING LOGIC ---
def identify_subdivision(addr_str):
    has_strike = "STRIKE" in addr_str
    has_explicit_bldg = re.search(r'\b(?:BLDG|BUILDING|BUILDUING|BULIDING|BLG|B)\.?[\s\-#]*\d+', addr_str)
    has_explicit_unit = re.search(r'\b(?:UNIT|U|ROOM|RM|MUNIT)[\s\-#]*[A-Z]*\d+', addr_str)
    
    if has_strike or (has_explicit_bldg and has_explicit_unit):
        return "CIUDAD DE STRIKE"
        
    mapping = {
        "CAMELLA LESSANDRA": [r"CAMELLALESSANDRA", r"CAMELLA", r"LESSANDRA"],
        "GREEN RIDGE": [r"GREENRIDGE", r"GREEN RIDGE", r"GREEN REDGIVILLAGE", r"GREENGRIDGE\s*VILLE", r"GREENRIDE"],
        "KRAUSE PARK": [r"KRAUSEPARK", r"KRAUSE PARK", r"KRAUS PARK"],
        "LUCKY VILLE": [r"LUCKYVILL", r"LUCKY VILLE", r"LUCKYVILLE", r"LUCKYVILE"], 
        "MASUERTE ST.": [r"MASUERTE", r"MASWERTE", r"DMASVERTE", r"MASUWERTE\s*VILL\.?"], 
        "NEW BETTER LANDSCAPE": [r"NEWBETTERLANDSCAPE", r"NEWBETTER LANDSCAPE", r"NEW BETTER LANDSCAPE", r"LANDSCAPE", r"NBLS", r"\bNBL\b", r"NEW BETTERLAND", r"NEW BETTER LAN\s*SCAPE", r"NEW BETTER LANDSSCAPE"],
        "ORIENT VILLE": [r"ORIENTVILLE", r"ORIENT VILLE", r"ORIENVILLE"],
        "PAULA HOMES": [r"PAULAHOMES", r"PAULA HOMES", r"PAULA HOME", r"PAULA HMES", r"PAULA HMS", r"\bHOMES\b"], 
        "PROGRESSIVE 17": [r"PROG\.?\s*17", r"PROGRESSIVE\s*17", r"PROGRESSIVE VILL\.?17"],
        "PROGRESSIVE 18": [r"PROG\.?\s*18", r"PROGRESSIVE\s*18", r"PROG\.?\s*VILLE\.?\s*18", r"PROG\.?VILLE\s*18", r"PROG\.?\s*VILLAGE 18", r"PROG\.?\s*VILLAG3 18", r"PROG\.?\s*VILLAGE #18", r"PRGRESSIVE VILLAGE 18"],
        "PROGRESSIVE 20-21": [r"PROG\.?\s*20-21", r"PROGESSIVE\s*20\s*21", r"PROGRESSIVE\s*20-21", r"PROG\.?\s*20\s*21", r"PROG\.?\s*VILL\.?#\s*20-21", r"PROG\.?\s*VILL\.?#\s*20", r"PROGRESSIVE\s*20\s*&\s*21", r"PROG\.?\s*21", r"PROG\.?\s*VILL\.?\s*20", r"PROG\.?\s*VILL\.?\s*20-21", r"PROGRESSIVE\s*21", r"PROGRESSIVE\s*2021", r"PROGRESSIVE VILLAGE 20-21"],
        "MOLINO ROAD": [r"MOLINO 1 ROAD", r"MOLINO I ROAD", r"\bROAD\b", r"\bBUROL\b", r"MOLINO 1 RD", r"MOLINO I RD", r"MOLINO RD", r"\bPROPER\b", r"IFUGAO\s*ST\.?"], 
        "VILLA FELICIA": [r"VILLAFELICIA", r"VILLA FELICIA", r"VILLA EFELICIA", r"VILLA FELCIA", r"V\.FELICIA", r"VILLA FELIOA", r"VILLA FELECIA"],
        "WOODESTATE": [r"WOODESTATE", r"WOOD ESTATE", r"WOODSTATE", r"WOOD STATE", r"WEV\s*[1I]?", r"\bWEV\b", r"WOODDESTAE", r"WOODESATE"] 
    }
    
    for sub_name, patterns in mapping.items():
        for pat in patterns:
            if re.search(pat, addr_str):
                return sub_name

    if re.search(r'\b(?:ST|STREET)\b', addr_str) and not re.search(r'\b(?:ROAD|RD|BUROL|PROPER|IFUGAO)\b', addr_str):
        return "UNKNOWN"

    if "MOLINO" in addr_str:
        nums = re.findall(r'\b\d+\b', addr_str)
        for n in nums:
            if 0 <= int(n) <= 1000:
                return "MOLINO ROAD"
                
    return "UNKNOWN"

def evaluate_strike_address(addr_str):
    explicit_phase = None
    ph1_match = re.search(r'\b(?:PHASE|PH|P)[\s\-]*1\b', addr_str)
    ph2_match = re.search(r'\b(?:PHASE|PH|P)[\s\-]*2\b', addr_str)
    
    if ph1_match and not ph2_match: 
        explicit_phase = 1
    elif ph2_match and not ph1_match: 
        explicit_phase = 2
    elif ph1_match and ph2_match:
        return None, "Needs Manual Review - Multiple Phases Detected"
        
    if re.search(r'\b(?:BLK|BLOCK|LOT|L)[\s\-]*\d+', addr_str):
        return None, "Needs Manual Review - Block/Lot Format Found"
        
    unit_str = None
    unit_match = re.search(r'\b(?:UNIT|U|ROOM|RM|MUNIT)[\s\-#]*[A-Z]*(\d+)\b', addr_str)
    
    if unit_match:
        unit_str = unit_match.group(1)
    else:
        bldg_dash_match = re.search(r'\b(?:BLDG|BUILDING|BUILDUING|BULIDING|BLG|B)\.?[\s#]*\d+[\s\-]+(\d+)\b', addr_str)
        if bldg_dash_match:
            unit_str = bldg_dash_match.group(1)
        else:
            hash_match = re.search(r'(?<!B)(?<!BLDG)(?<!BLG)(?<!BUILDING)(?<!BUILDUING)(?<!BULIDING)[\s\-]*#[\s\-]*[A-Z]*(\d+)\b', addr_str)
            if hash_match:
                unit_str = hash_match.group(1)
                
    if not unit_str:
        clean_addr = addr_str
        clean_addr = re.sub(r'\b(?:PHASE|PH|P)[\s\-]*[12I]+\b', '', clean_addr)
        clean_addr = re.sub(r'\b(?:BLDG|BUILDING|BUILDUING|BULIDING|BLG|B)\.?[\s\-#]*\d+\b', '', clean_addr)
        
        standalone_nums = re.findall(r'\b\d+\b', clean_addr)
        
        valid_unit_candidates = []
        for n in standalone_nums:
            num = int(n)
            if (1 <= num <= 72) or (101 <= num <= 324):
                valid_unit_candidates.append(n)
        
        if len(valid_unit_candidates) == 1:
            unit_str = valid_unit_candidates[0]
        elif len(valid_unit_candidates) > 1:
            return None, "Needs Manual Review - Multiple Number Candidates"
        else:
            return None, "Needs Manual Review - No Valid Unit Number Found"
            
    unit_num = int(unit_str)
    calc_phase = None
    if 1 <= unit_num <= 72:
        calc_phase = 1
    elif 101 <= unit_num <= 324:
        calc_phase = 2
        
    if not calc_phase:
        return unit_str, "Needs Manual Review - Unit Out of Range"
        
    if explicit_phase is not None and explicit_phase != calc_phase:
        return unit_str, f"Needs Manual Review - Mismatch (Says PH {explicit_phase}, Unit {unit_num} is PH {calc_phase})"
        
    return unit_str, f"PH {calc_phase}"

def parse_address(address):
    if pd.isna(address):
        return pd.Series([False, None, "NONE", "Excluded - Missing Address"])
    
    addr_str = str(address).upper()
    addr_str = addr_str.replace("=", " ").replace("_", " ")
    
    subdivision = identify_subdivision(addr_str)
    
    if subdivision == "UNKNOWN":
        return pd.Series([False, None, "UNKNOWN", "Needs Manual Review - Unknown Subdivision / Street"])
        
    if subdivision != "CIUDAD DE STRIKE":
        return pd.Series([True, None, subdivision, subdivision])
        
    unit_str, category = evaluate_strike_address(addr_str)
    return pd.Series([True, unit_str, subdivision, category])


# --- PAGE: HOME ---
if page == "Home":
    st.title("Molino 1 Master Filtering System")
    st.write("Welcome to the automated categorization system for COMELEC addresses in Barangay Molino 1.")
    
    st.info("📖 **[Click here to view the Official System Guidelines & Documentation](https://docs.google.com/document/d/1dJ_UXOew4EFtwTX6FqOZnj_98x6DweSlJLoO2Iwi8Io/edit?usp=sharing)**")
    
    if 'processed_df' in st.session_state:
        st.success("📁 **A saved session is currently active.** Your previous manual review progress has been loaded automatically! You can safely go to the Dashboard or Filtering tabs to continue.")
        
        if st.button("🗑️ Start New Session (Clear Saved Data)", type="secondary"):
            if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
            if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
            del st.session_state['processed_df']
            st.rerun()
            
        st.divider()
        st.write("Or upload a new file below to overwrite the current session:")
    else:
        st.write("Upload your master list below to standardize addresses, detect typos, and securely map voters to their respective subdivisions.")
    
    uploaded_file = st.file_uploader("Upload Excel / CSV File", type=["xlsx", "xls", "csv"])
    
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        address_col = st.selectbox("Select the Address Column from your file:", df.columns)
        
        if st.button("Run Initial Filter", type="primary"):
            df[['Is_Valid_Molino_1', 'Strike_Evaluated_Unit', 'Standardized_Subdivision', 'Category']] = df[address_col].apply(parse_address)
            
            st.session_state['processed_df'] = df
            st.session_state['address_col'] = address_col
            
            df.to_csv(DATA_FILE, index=False)
            with open(CONFIG_FILE, "w") as f:
                f.write(address_col)
                
            st.success("File processed and saved securely to the system! Navigate to 'Dashboard' or 'Filtering' in the sidebar.")

# --- PAGE: DASHBOARD ---
elif page == "Dashboard":
    if 'processed_df' not in st.session_state:
        st.warning("Please upload and process a file on the 'Home' page first.")
    else:
        st.title("System Dashboard")
        st.write("Visual breakdown of the processed COMELEC data.")
        
        df = st.session_state['processed_df']
        
        st.subheader("Subdivision Insights")
        filter_options = [
            "All Records (Entire Molino 1)", "PHASE 1 ONLY (Strike)", "PHASE 2 ONLY (Strike)",
            "CIUDAD DE STRIKE (All Valid)", "CAMELLA LESSANDRA", "GREEN RIDGE", "KRAUSE PARK", 
            "LUCKY VILLE", "MASUERTE ST.", "NEW BETTER LANDSCAPE", "ORIENT VILLE", "PAULA HOMES",
            "PROGRESSIVE 17", "PROGRESSIVE 18", "PROGRESSIVE 20-21", "MOLINO ROAD", 
            "VILLA FELICIA", "WOODESTATE", "Needs Manual Review", "Excluded"
        ]
        
        selected_filter = st.selectbox("Select Subdivision or Category View:", filter_options)
        
        if selected_filter == "All Records (Entire Molino 1)":
            view_df = df
        elif selected_filter == "PHASE 1 ONLY (Strike)":
            view_df = df[df['Category'] == 'PH 1']
        elif selected_filter == "PHASE 2 ONLY (Strike)":
            view_df = df[df['Category'] == 'PH 2']
        elif selected_filter == "CIUDAD DE STRIKE (All Valid)":
            view_df = df[df['Category'].isin(['PH 1', 'PH 2'])]
        elif selected_filter == "Needs Manual Review":
            view_df = df[df['Category'].str.startswith('Needs Manual Review')]
        elif selected_filter == "Excluded":
            view_df = df[df['Category'].str.startswith('Excluded')]
        else:
            view_df = df[df['Standardized_Subdivision'] == selected_filter]
            
        st.divider()
    
        st.subheader("Current View Metrics")
        m1, m2, m3 = st.columns(3)
        
        m1.metric(f"Total in {selected_filter[:15]}...", len(view_df))
        valid_count_in_view = len(view_df[~view_df['Category'].str.startswith('Needs Manual') & ~view_df['Category'].str.startswith('Excluded')])
        m2.metric("Categorized in View", valid_count_in_view)
        global_pending = len(df[df['Category'].str.startswith('Needs Manual')])
        m3.metric("Global Pending Review", global_pending)
        
        st.divider()
        
        if selected_filter == "All Records (Entire Molino 1)":
            st.write("**Visual Breakdown: All Molino 1 Subdivisions**")
            st.line_chart(view_df['Standardized_Subdivision'].value_counts())
        else:
            st.write(f"**Visual Breakdown: {selected_filter}**")
            st.line_chart(view_df['Category'].value_counts())

# --- PAGE: FILTERING ---
elif page == "Filtering":
    if 'processed_df' not in st.session_state:
        st.warning("Please upload and process a file on the 'Home' page first.")
    else:
        st.title("Data Filtering & Override")
        st.write("Use the dropdown to fix multiple addresses at once, then click 'Save & Apply All Changes' to re-route them and automatically save your progress to the hard drive.")
        
        df = st.session_state['processed_df']
        address_col = st.session_state['address_col']
        
        subdivision_options = [
            "UNKNOWN", "CIUDAD DE STRIKE", "CIUDAD DE STRIKE (Force PH 1)", "CIUDAD DE STRIKE (Force PH 2)",
            "CAMELLA LESSANDRA", "GREEN RIDGE", "KRAUSE PARK", "LUCKY VILLE", "MASUERTE ST.", 
            "NEW BETTER LANDSCAPE", "ORIENT VILLE", "PAULA HOMES", "PROGRESSIVE 17", "PROGRESSIVE 18",
            "PROGRESSIVE 20-21", "MOLINO ROAD", "VILLA FELICIA", "WOODESTATE"
        ]
        
        filter_options = [
            "Needs Manual Review", "All Records (Entire Molino 1)", "PHASE 1 ONLY (Strike)", "PHASE 2 ONLY (Strike)",
            "CIUDAD DE STRIKE (All Valid)", "CAMELLA LESSANDRA", "GREEN RIDGE", "KRAUSE PARK", 
            "LUCKY VILLE", "MASUERTE ST.", "NEW BETTER LANDSCAPE", "ORIENT VILLE", "PAULA HOMES",
            "PROGRESSIVE 17", "PROGRESSIVE 18", "PROGRESSIVE 20-21", "MOLINO ROAD", 
            "VILLA FELICIA", "WOODESTATE", "Excluded"
        ]
        
        selected_filter = st.selectbox("**Select Data View to Edit:**", filter_options)
        
        if selected_filter == "All Records (Entire Molino 1)":
            view_df = df
        elif selected_filter == "PHASE 1 ONLY (Strike)":
            view_df = df[df['Category'] == 'PH 1']
        elif selected_filter == "PHASE 2 ONLY (Strike)":
            view_df = df[df['Category'] == 'PH 2']
        elif selected_filter == "CIUDAD DE STRIKE (All Valid)":
            view_df = df[df['Category'].isin(['PH 1', 'PH 2'])]
        elif selected_filter == "Needs Manual Review":
            view_df = df[df['Category'].str.startswith('Needs Manual Review')]
        elif selected_filter == "Excluded":
            view_df = df[df['Category'].str.startswith('Excluded')]
        else:
            view_df = df[df['Standardized_Subdivision'] == selected_filter]
        
        if st.button("🔄 Save & Apply All Changes", type="primary"):
            if 'edited_df_state' in st.session_state:
                edited_df_current = st.session_state['edited_df_state']
                changed_indices = edited_df_current[edited_df_current['Standardized_Subdivision'] != view_df['Standardized_Subdivision']].index
                
                for idx in changed_indices:
                    new_sub = edited_df_current.at[idx, 'Standardized_Subdivision']
                    
                    if new_sub == "UNKNOWN":
                        df.at[idx, 'Standardized_Subdivision'] = "UNKNOWN"
                        df.at[idx, 'Category'] = "Needs Manual Review - Unknown Subdivision / Street"
                    
                    elif new_sub == "CIUDAD DE STRIKE":
                        df.at[idx, 'Standardized_Subdivision'] = "CIUDAD DE STRIKE"
                        parsed = parse_address(df.at[idx, address_col])
                        df.at[idx, 'Strike_Evaluated_Unit'] = parsed.iloc[1]
                        df.at[idx, 'Category'] = parsed.iloc[3]
                        df.at[idx, 'Is_Valid_Molino_1'] = True
                        
                    elif new_sub == "CIUDAD DE STRIKE (Force PH 1)":
                        df.at[idx, 'Standardized_Subdivision'] = "CIUDAD DE STRIKE"
                        df.at[idx, 'Category'] = "PH 1"
                        df.at[idx, 'Is_Valid_Molino_1'] = True
                        df.at[idx, 'Strike_Evaluated_Unit'] = None
                        
                    elif new_sub == "CIUDAD DE STRIKE (Force PH 2)":
                        df.at[idx, 'Standardized_Subdivision'] = "CIUDAD DE STRIKE"
                        df.at[idx, 'Category'] = "PH 2"
                        df.at[idx, 'Is_Valid_Molino_1'] = True
                        df.at[idx, 'Strike_Evaluated_Unit'] = None
                        
                    else:
                        df.at[idx, 'Standardized_Subdivision'] = new_sub
                        df.at[idx, 'Category'] = new_sub
                        df.at[idx, 'Is_Valid_Molino_1'] = True
                        df.at[idx, 'Strike_Evaluated_Unit'] = None
                
                df.to_csv(DATA_FILE, index=False)
                
                st.session_state['processed_df'] = df
                st.success("Progress saved successfully to the system!")
                st.rerun()
    
        disabled_cols = [address_col, 'Is_Valid_Molino_1', 'Strike_Evaluated_Unit', 'Category']
        
        st.session_state['edited_df_state'] = st.data_editor(
            view_df, 
            use_container_width=True, 
            disabled=disabled_cols,
            column_config={
                "Standardized_Subdivision": st.column_config.SelectboxColumn(
                    "Standardized_Subdivision",
                    help="Select to automatically move the address to the correct subdivision",
                    options=subdivision_options,
                    required=True
                )
            }
        )
        
        st.divider()
        csv_file = view_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"Export Data to CSV",
            data=csv_file,
            file_name=f"Molino1_{selected_filter.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '')}.csv",
            mime="text/csv"
        )

# --- PAGE: SYSTEM LOGS (ADMIN ONLY) ---
elif page == "System Logs":
    st.title("System Access Logs")
    st.write("Complete audit trail of everyone who has logged into the Master Filtering System.")
    
    if os.path.exists(LOGS_FILE):
        logs_df = pd.read_csv(LOGS_FILE)
        
        # Reverse to show newest logins first
        logs_df = logs_df.iloc[::-1].reset_index(drop=True)
        
        st.dataframe(logs_df, use_container_width=True)
        
        st.divider()
        csv_logs = logs_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Complete Security Log",
            data=csv_logs,
            file_name="Molino1_System_Logs.csv",
            mime="text/csv"
        )
    else:
        st.info("No system logs found yet. The file will be created automatically when someone logs in.")
