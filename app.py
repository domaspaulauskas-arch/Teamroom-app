import streamlit as st
from st_gsheets connection import GSheetsConnection
import pandas as pd
import plotly.express as px
from fpdf import FPDF
from datetime import date, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Elite Team Monitor", layout="wide")

# Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# --- STYLING FUNCTIONS ---
def color_coding(val):
    if val == "Match Day": return 'background-color: #28a745; color: white' # Green
    elif val == "Training": return 'background-color: #ffc107; color: black' # Yellow
    elif val == "Rest Day": return 'background-color: #17a2b8; color: white' # Blue
    return ''

def create_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, txt="WEEKLY TEAM WELLNESS REPORT", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    # Table Header
    pdf.cell(30, 8, "Date", 1)
    pdf.cell(50, 8, "Name", 1)
    pdf.cell(25, 8, "Fatigue", 1)
    pdf.cell(25, 8, "Sleep", 1)
    pdf.cell(60, 8, "Soreness", 1)
    pdf.ln()
    # Data Rows
    for _, row in df.iterrows():
        pdf.cell(30, 8, str(row['Date']), 1)
        pdf.cell(50, 8, str(row['Name']), 1)
        pdf.cell(25, 8, str(row['Fatigue']), 1)
        pdf.cell(25, 8, str(row['Sleep']), 1)
        pdf.cell(60, 8, str(row['Soreness']), 1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("⚽ Pro Team Hub")
menu = st.sidebar.radio("Navigate to:", ["Player Entry", "Coach Dashboard"])

# --- PAGE 1: PLAYER ENTRY ---
if menu == "Player Entry":
    st.title("Player Wellness Tracking")
    st.write("Welcome to our Team Hub! Your honesty helps us optimize performance and prevent injuries.")
    
    # Instructions Expander
    with st.expander("ℹ️ Instructions for Players"):
        st.write("""
        - **Fatigue:** 1 (Fresh/Ready) to 5 (Exhausted).
        - **Sleep:** Total hours slept last night.
        - **Soreness:** Report any sharp pain or injury immediately.
        - **Cycle:** Important for ACL injury prevention.
        """)

    # Schedule Display (Upcoming 14 Days)
    st.subheader("📅 Upcoming 14-Day Schedule")
    try:
        schedule_df = conn.read(worksheet="Schedule")
        schedule_df['Date'] = pd.to_datetime(schedule_df['Date']).dt.date
        today = date.today()
        two_weeks = schedule_df[(schedule_df['Date'] >= today) & 
                                (schedule_df['Date'] <= today + timedelta(days=14))]
        st.dataframe(two_weeks.style.applymap(color_coding, subset=['Activity']), 
                     use_container_width=True, hide_index=True)
    except:
        st.info("The coach hasn't updated the 'Schedule' sheet yet.")

    st.divider()

    # Survey Form
    with st.form(key="wellness_form", clear_on_submit=True):
        name = st.text_input("Full Name*")
        col1, col2 = st.columns(2)
        with col1:
            fatigue = st.select_slider("Fatigue Level (1-5)", options=[1, 2, 3, 4, 5], value=2)
            sleep_hours = st.number_input("Sleep Duration (hours)", 0.0, 15.0, 8.0, 0.5)
            weight = st.number_input("Current Weight (kg)", 40.0, 120.0, 60.0)
        with col2:
            soreness = st.selectbox("Soreness/Injuries", ["None", "Muscle Ache", "Joint Pain", "Injury"])
            cycle = st.selectbox("Cycle Phase", ["N/A", "Menstruation", "Follicular", "Ovulation", "Luteal"])
            vitamins = st.toggle("Supplements/Vitamins taken?")
        
        notes = st.text_area("Notes for the coach (Nutrition, specific pains, etc.)")
        submit = st.form_submit_button("Submit Daily Entry")

    if submit:
        if name:
            new_data = pd.DataFrame([{
                "Date": date.today().strftime("%Y-%m-%d"),
                "Name": name,
                "Fatigue": fatigue,
                "Sleep": sleep_hours,
                "Soreness": soreness,
                "Weight": weight,
                "Cycle": cycle,
                "Vitamins": vitamins,
                "Notes": notes
            }])
            # Append data to Google Sheets
            existing_data = conn.read(worksheet="Sheet1")
            updated_df = pd.concat([existing_data, new_data], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            
            if fatigue >= 4 or soreness != "None":
                st.error(f"⚠️ Warning sent to coach. Take care of yourself, {name}!")
            else:
                st.success(f"Thank you, {name}! Your data has been recorded.")
            st.balloons()
        else:
            st.warning("Please enter your name.")

# --- PAGE 2: COACH DASHBOARD ---
elif menu == "Coach Dashboard":
    st.title("📊 Coach's Analysis Dashboard")
    
    # Load data
    df = conn.read(worksheet="Sheet1")
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    
    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Today's Entries", len(df[df['Date'] == date.today()]))
    c2.metric("Avg Fatigue (Week)", round(df[df['Date'] >= (date.today() - timedelta(days=7))]['Fatigue'].mean(), 1))
    c3.metric("Avg Sleep (Week)", f"{round(df[df['Date'] >= (date.today() - timedelta(days=7))]['Sleep'].mean(), 1)}h")

    # 1. Critical Alerts
    st.subheader("🚩 Today's Flags")
    flags = df[(df['Date'] == date.today()) & ((df['Fatigue'] >= 4) | (df['Soreness'] != "None"))]
    if not flags.empty:
        st.warning("The following players need attention:")
        st.dataframe(flags[['Name', 'Fatigue', 'Sleep', 'Soreness', 'Notes']], use_container_width=True)
    else:
        st.success("No critical alerts for today.")

    # 2. Charts
    st.subheader("📈 Team Trends (Last 14 Days)")
    trend_data = df[df['Date'] >= (date.today() - timedelta(days=14))].groupby('Date')[['Fatigue', 'Sleep']].mean().reset_index()
    
    fig_fatigue = px.line(trend_data, x='Date', y='Fatigue', title="Average Fatigue Trend", markers=True)
    fig_fatigue.update_yaxes(range=[1, 5])
    st.plotly_chart(fig_fatigue, use_container_width=True)

    # 3. Export & Data
    st.subheader("📥 Data Export")
    if st.button("Generate Weekly PDF Report"):
        weekly_df = df[df['Date'] >= (date.today() - timedelta(days=7))]
        pdf_bytes = create_pdf(weekly_df)
        st.download_button("Download PDF", data=pdf_bytes, file_name=f"Report_{date.today()}.pdf", mime="application/pdf")

    with st.expander("View Raw Database"):
        st.dataframe(df.sort_values(by='Date', ascending=False), use_container_width=True)
