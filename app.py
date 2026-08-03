import re
import os
import base64
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Molino 1 Filtering System", layout="wide", initial_sidebar_state="expanded")

# --- FILE PATHS FOR AUTO-SAVING PROGRESS ---
DATA_FILE = "molino1_saved_data.csv"
CONFIG_FILE = "molino1_config.txt"

# --- AUTO-LOAD SAVED SESSION ON STARTUP ---
if 'processed_df' not in st.session_state and os.path.exists(DATA_FILE) and os.path.exists(CONFIG_FILE):
    try:
        st.session_state['processed_df'] = pd.read_csv(DATA_FILE)
        with open(CONFIG_FILE, "r") as f:
            st.session_state['address_col'] = f.read().strip()
    except Exception as e:
        st.error("Error loading saved session. The file might be corrupted.")

# --- SIDEBAR NAVIGATION WITH CIRCULAR LOGO ---
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
        st.sidebar.warning("Logo image file not found. Please ensure the file name matches.")

display_circular_logo("449958530_878918900941660_1079343009849520447_n (2).jpg")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Home", "Dashboard", "Filtering"])

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
        
    unit_str = None
    clean_unit_str = None
    category = "Needs Manual Review - No Number Found" 
        
    unit_match = re.search(r'\b(?:UNIT|U|ROOM|RM|MUNIT)[\s\-#]*[A-Z]*(\d+(?:-\d+)?)', addr_str)
    if unit_match:
        unit_str = unit_match.group(1)
    else:
        bldg_dash_match = re.search(r'\b(?:BLDG|BUILDING|BUILDUING|BULIDING|BLG|B)\.?[\s#]*\d+[\s\-]+(\d+(?:-\d+)?)', addr_str)
        if bldg_dash_match:
            unit_str = bldg_dash_match.group(1)
        else:
            hash_match = re.search(r'(?<!B)(?<!BLDG)(?<!BLG)(?<!BUILDING)(?<!BUILDUING)(?<!BULIDING)[\s\-]*#[\s\-]*[A-Z]*(\d+(?:-\d+)?)', addr_str)
            if hash_match:
                unit_str = hash_match.group(1)
            
    if not unit_str:
        leading_match = re.search(r'\b(\d+(?:-\d+)?)[\s\-]*(?:(?:PHASE|PH|P)[\s\-]*[12I]+[\s\-]*)?(?:B|BLDG|BLG|BUILDING|BUILDUING|BULIDING)\.?', addr_str)
        if leading_match:
            unit_str = leading_match.group(1)

    if not unit_str:
        clean_addr = re.sub(r'\b(?:PHASE|PH|P)[\s\-]*[12I]+\b', '', addr_str)
        clean_addr = re.sub(r'\b(?:BLDG|BUILDING|BUILDUING|BULIDING|BLG|B)\.?[\s\-#]*\d+\b', '', clean_addr)
        standalone_nums = re.findall(r'\b\d+\b', clean_addr)
        for num_str in standalone_nums:
            num = int(num_str)
            if 1 <= num <= 72 or 101 <= num <= 324:
                unit_str = num_str
                break

    if unit_str:
        clean_unit_str = unit_str.replace("-", "")
        unit_num = int(clean_unit_str)
        
        if 1 <= unit_num <= 72:
            category = "PH 1"
        elif 101 <= unit_num <= 324:
            category = "PH 2"
        else:
            category = "Needs Manual Review - Out of Range"
    else:
        if re.search(r'\b(?:LOT|L|BLOCK|BLK)\b', addr_str):
            category = "Needs Manual Review - Block/Lot Format"
        elif re.search(r'\b(?:BLDG|BUILDING|BUILDUING|BULIDING|BLG|B)\.?[\s\-#]*\d+', addr_str):
            category = "Needs Manual Review - Only Bldg Number Found"
                
    return pd.Series([True, clean_unit_str, subdivision, category])


# --- PAGE: HOME ---
if page == "Home":
    st.title("Molino 1 Master Filtering System")
    st.write("Welcome to the automated categorization system for COMELEC addresses in Barangay Molino 1.")
    
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

if page in ["Dashboard", "Filtering"] and 'processed_df' not in st.session_state:
    st.warning("Please upload and process a file on the 'Home' page first.")

# --- PAGE: DASHBOARD ---
elif page == "Dashboard" and 'processed_df' in st.session_state:
    st.title("System Dashboard")
    st.write("Visual breakdown of the processed COMELEC data.")
    
    df = st.session_state['processed_df']
    
    st.subheader("Global Metrics")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Records Uploaded", len(df))
    m2.metric("Successfully Categorized", len(df[~df['Category'].str.startswith('Needs Manual') & ~df['Category'].str.startswith('Excluded')]))
    m3.metric("Pending Manual Review", len(df[df['Category'].str.startswith('Needs Manual')]))
    
    st.divider()
    
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
        st.write("**Visual Breakdown: All Molino 1 Subdivisions**")
        st.line_chart(view_df['Standardized_Subdivision'].value_counts())
    elif selected_filter == "PHASE 1 ONLY (Strike)":
        view_df = df[df['Category'] == 'PH 1']
        st.line_chart(view_df['Category'].value_counts())
    elif selected_filter == "PHASE 2 ONLY (Strike)":
        view_df = df[df['Category'] == 'PH 2']
        st.line_chart(view_df['Category'].value_counts())
    elif selected_filter == "CIUDAD DE STRIKE (All Valid)":
        view_df = df[df['Category'].isin(['PH 1', 'PH 2'])]
        st.line_chart(view_df['Category'].value_counts())
    elif selected_filter == "Needs Manual Review":
        view_df = df[df['Category'].str.startswith('Needs Manual Review')]
        st.line_chart(view_df['Category'].value_counts())
    elif selected_filter == "Excluded":
        view_df = df[df['Category'].str.startswith('Excluded')]
    else:
        view_df = df[df['Standardized_Subdivision'] == selected_filter]
        st.line_chart(view_df['Category'].value_counts())

# --- PAGE: FILTERING ---
elif page == "Filtering" and 'processed_df' in st.session_state:
    st.title("Data Filtering & Override")
    st.write("Use the dropdown to fix multiple addresses at once, then click 'Save & Apply All Changes' to re-route them and automatically save your progress to the hard drive.")
    
    df = st.session_state['processed_df']
    address_col = st.session_state['address_col']
    
    # ADDED: Explicit Force Phase 1 and Phase 2 overrides
    subdivision_options = [
        "UNKNOWN", "CIUDAD DE STRIKE", "CIUDAD DE STRIKE (Force PH 1)", "CIUDAD DE STRIKE (Force PH 2)",
        "CAMELLA LESSANDRA", "GREEN RIDGE", "KRAUSE PARK", "LUCKY VILLE", "MASUERTE ST.", 
        "NEW BETTER LANDSCAPE", "ORIENT VILLE", "PAULA HOMES", "PROGRESSIVE 17", "PROGRESSIVE 18",
        "PROGRESSIVE 20-21", "MOLINO ROAD", "VILLA FELICIA", "WOODESTATE"
    ]
    
    # ADDED: Proper Phase filtering views
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
                    
                # ADDED: Manual Phase override handling
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
    csv = view_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"Export Data to CSV",
        data=csv,
        file_name=f"Molino1_{selected_filter.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '')}.csv",
        mime="text/csv"
    )
