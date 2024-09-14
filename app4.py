import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_plotly_events import plotly_events
import matplotlib.pyplot as plt
from pypalettes import load_cmap
import seaborn as sns

st.set_page_config(
    page_title="Dr.Ilan's Dashboard",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="auto",
)
st.markdown(
    "<style>div.block-container{padding-top:1rem;}</style>", unsafe_allow_html=True
)
cmap = load_cmap("Abbott")

hide_st_style = """
                <style>
                MainMenu {visibility: hidden;}
                footer {visibility: hidden;}
                header {visibility: hidden;}
                """
st.markdown(hide_st_style, unsafe_allow_html=True)
st.markdown(
    """
    <style>
    .sidebar .sidebar-content {
        background-color: #ffffff;
        color: white;
    }
    .main {
        background-color: #ffffff;
        color: black;
    }
    .title {
        color: #1C445F;
        text-align: center;
    }
    .scrollable-graph {
        overflow-x: auto;
        overflow-y: hidden;
        max-width: 100%;
        white-space: nowrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache_data
def load_data(api_url):
    try:
        df = pd.read_json(api_url)
        df["billDate"] = pd.to_datetime(df["billDate"], format="%d-%m-%Y", errors='coerce')
        return df
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

def filter_data(df, start_date, end_date, departments, doctors):
    if df.empty:
        return df
    
    start_date = pd.to_datetime(start_date).normalize()
    end_date = pd.to_datetime(end_date).normalize() + pd.DateOffset(days=1)  
    
    df['billDate'] = pd.to_datetime(df['billDate']).dt.normalize()

    excluded_departments = ["HPB Surgery, Liver And Kidney Transplantation","HPB Surgery And Liver Transplantation", "Hepatology"]
    df = df[~df['orderDepartment'].isin(excluded_departments)]

    filtered_df = df[(df['billDate'] >= start_date) & (df['billDate'] < end_date)]
    
    if departments:
        filtered_df = filtered_df[filtered_df['orderDepartment'].isin(departments)]
    if doctors:
        filtered_df = filtered_df[filtered_df['orderDoctor'].isin(doctors)]
    
    return filtered_df

def get_kpi_metrics(df):
    if df.empty:
        return {"FTD": 0, "MTD": 0, "LYSMTD": 0, "YTD": 0, "LYTD": 0}
    
    current_date = pd.to_datetime(datetime.now().date())
    current_month = current_date.to_period("M")
    current_year = current_date.year
    last_year = current_year - 1

    ftd_df = df[df["billDate"] == current_date]
    mtd_df = df[df["billDate"].dt.to_period("M") == current_month]
    lysmtd_df = df[(df["billDate"].dt.year == last_year) & (df["billDate"].dt.month == current_date.month)]
    ytd_df = df[df["billDate"].dt.year == current_year]
    lytd_df = df[df["billDate"].dt.year == last_year]

    return {
        "FTD": ftd_df["net"].sum(),
        "MTD": mtd_df["net"].sum(),
        "LYSMTD": lysmtd_df["net"].sum(),
        "YTD": ytd_df["net"].sum(),
        "LYTD": lytd_df["net"].sum(),
    }


def main():
    today = datetime.today().date()

    if 'api_url' not in st.session_state:
        st.session_state.api_url = f"http://192.168.15.3/NewHIS/api/his/OPIPREVENUE_Date?FromDate={today}&ToDate={today}&Pattype=ALL&IVF_flg=0"

    if 'from_date' not in st.session_state:
        st.session_state.from_date = today  # Default to today

    if 'to_date' not in st.session_state:
        st.session_state.to_date = today  # Default to today

       # st.write(f"Current API URL: {st.session_state.api_url}")

    # Header and search input
    left, right = st.columns([1, 2])
    with left:
        st.header("Dr. Ilan's CEO Dashboard")
    with right:
        search_term = st.text_input("Search")

    # Create 4 columns for date, department, and doctor selection
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        from_date = st.date_input("From Date", value=st.session_state.from_date)
    with col2:
        to_date = st.date_input("To Date", value=st.session_state.to_date)

    # Update session state and API URL if dates have changed
    if from_date != st.session_state.from_date or to_date != st.session_state.to_date:
        st.session_state.from_date = from_date
        st.session_state.to_date = to_date
        st.session_state.api_url = f"http://192.168.15.3/NewHIS/api/his/Revenu_dashboard?FromDate={from_date}&ToDate={to_date}"
        #st.write(f"Current API URL: {st.session_state.api_url}")
        # Reload data after updating the URL
        df = load_data(st.session_state.api_url)
    else:
        # Load data only if URL has not been updated (e.g., on initial load)
        df = load_data(st.session_state.api_url)

    # Check if data is being loaded correctly
    if df.empty:
        st.error("No data available for the selected criteria.")
        return

    # Apply initial filters
    filtered_df = filter_data(df, st.session_state.from_date, st.session_state.to_date, [], [])

    # Apply search filter if a search term is provided
    if search_term:
        filtered_df = filtered_df[
            filtered_df.apply(
                lambda row: search_term.lower() in row.astype(str).str.lower().to_string(),
                axis=1,
            )
        ]

    # Department and doctor selection in the same row
    with col3:
        available_departments = [dept for dept in df["orderDepartment"].unique() if dept not in ["HPB Surgery, Liver And Kidney Transplantation", "HPB Surgery And Liver Transplantation", "Hepatology"]]
        selected_department = st.selectbox("Select Department", ["All"] + available_departments)

    with col4:
        if selected_department == "All":
            doctors = st.multiselect("Select Doctors", df["orderDoctor"].unique())
        else:
            doctors = st.multiselect(
                "Select Doctors",
                df[df["orderDepartment"] == selected_department]["orderDoctor"].unique(),
            )

    # Filter data based on department and doctor selection

    filtered_df = filter_data(
        filtered_df,
        st.session_state.from_date,
        st.session_state.to_date,
        [selected_department] if selected_department != "All" else [],
        doctors
    )
    
    # Calculate KPIs
    kpi_metrics = get_kpi_metrics(filtered_df)

    # Calculate the difference between the selected dates
    date_diff = (st.session_state.to_date - st.session_state.from_date).days

    # Plot based on selected frequency
    if "freq" not in st.session_state:
        st.session_state.freq = "D"

    # Frequency selection columns
    col5, col6, col7 = st.columns(3)
    with col5:
        if date_diff > 31:
            st.button("Day", disabled=True)
        else:
            if st.button("Day"):
                st.session_state.freq = "D"

    with col6:
        if date_diff < 31:
            st.button("Month", disabled=True)
        else:
            if st.button("Month"):
                st.session_state.freq = "M"

    with col7:
        if st.button("Year"):
            st.session_state.freq = "Y"

    # Ensure freq is still valid when certain buttons are disabled
    if date_diff > 31 and st.session_state.freq == "D":
        st.session_state.freq = "M"
    elif date_diff < 31 and st.session_state.freq == "M":
        st.session_state.freq = "D"

    # Creating left (graph) and right (KPI) columns
    left, right = st.columns([2, 1])

    # Display the KPIs in the right column
    with right:
        st.markdown(
            """
            <style>
            .kpi-container {
                padding: 20px;
                border-radius: 10px;
            }
            .kpi-metric {
                color: #000000;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
                margin-bottom: 10px;
                border-left: 5px solid;
            }
            .ftd { border-left-color: #ff4d4f; } /* Red */
            .mtd { border-left-color: #40a9ff; } /* Blue */
            .lysmtd { border-left-color: #73d13d; } /* Green */
            .ytd { border-left-color: #faad14; } /* Yellow */
            .lytd { border-left-color: #9254de; } /* Purple */
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### KPIs Overview")
        st.markdown(f'<div class="kpi-metric ftd">FTD: ₹{kpi_metrics["FTD"] / 1e7:.2f} Cr</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-metric mtd">MTD: ₹{kpi_metrics["MTD"] / 1e7:.2f} Cr</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-metric ytd">YTD: ₹{kpi_metrics["YTD"] / 1e7:.2f} Cr</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-metric lytd">LYTD: ₹{kpi_metrics["LYTD"] / 1e7:.2f} Cr</div>', unsafe_allow_html=True)

    # Handle frequency-based resampling and plotting in the left column
    with left:
        freq = st.session_state.freq
        if freq == "D":
            #st.write("Viewing daily revenue data.")
            df_resampled = filtered_df.resample('D', on="billDate").sum().reset_index()
            fig = px.line(
                df_resampled,
                x="billDate",
                y="net",
                title="Revenue (Daily)",
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Plotly,
            )

        elif freq == "M":
            df_resampled = filtered_df.resample('M', on="billDate").sum().reset_index()
            fig = px.bar(
                df_resampled,
                x="billDate",
                y="net",
                title="Revenue (Monthly)",
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Plotly,
                
            )


        elif freq == "Y":
            st.write("Viewing yearly revenue data.")
            df_resampled = filtered_df.resample('Y', on="billDate").sum().reset_index()
            fig = px.area(
                df_resampled,
                x="billDate",
                y="net",
                title="Revenue (Yearly)",
                template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Plotly,
            )

        # Check if the resampled data is not empty
        if not df_resampled.empty:
            from_date = df_resampled["billDate"].min().strftime("%Y-%m-%d")
            to_date = df_resampled["billDate"].max().strftime("%Y-%m-%d")
            #st.write(f"Data range: {from_date} to {to_date}")

        # Display the chart
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
        )

        # Ensure the chart is scrollable
        st.markdown('<div class="scrollable-graph">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Initialize session state for selected department (if not already set)
    if 'selected_department_name' not in st.session_state:
        st.session_state.selected_department_name = None


    # Department wise revenue
    col10, col11 = st.columns(2)
    with col10:
        st.subheader("Department wise Revenue  ")
        department_revenue = (
            filtered_df.groupby("orderDepartment")["net"]
            .sum()
            .reset_index()
            .sort_values(by="net")
        )
        fig1 = px.bar(
            department_revenue,
            x="orderDepartment",
            y="net",
            orientation="v",
           
            color_discrete_sequence=["#0083B8"] * len(department_revenue),
            template="plotly_white",
        )
        fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False))

        # Capture department selection
        selected_points = plotly_events(fig1)
        if selected_points:
            st.session_state.selected_department_name = selected_points[0]["x"]


    # Doctor wise revenue
    with col11:
        
        st.subheader("Doctor wise Revenue")
        st.write(f"Selected Department: {st.session_state.selected_department_name}")
        if st.session_state.selected_department_name:
            filtered_doctor_df = filtered_df[
                (filtered_df["orderDepartment"] == st.session_state.selected_department_name)
            ]
            doctor_revenue = (
                filtered_doctor_df.groupby("orderDoctor")["net"]
                .sum()
                .reset_index()
                .sort_values(by="net")
            )
            fig2 = px.line(
                doctor_revenue,
                x="orderDoctor",
                y="net",
                orientation="v",        
                color_discrete_sequence=["#0083B8"] * len(doctor_revenue),
                template="plotly_white",
            )
            fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(showgrid=False))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Please Click a department bar to view doctor-wise revenue.")
  
    # service wise revenue
    st.subheader("Service-Wise Revenue Summary")
    service_summary = (
        filtered_df.groupby("serviceName")
        .agg({"uhid": "nunique", "net": "sum"})
        .reset_index()
        .rename(columns={"uhid": "Volume"})
    )
    fig5 = px.treemap(
        service_summary,
        path=["serviceName"],
        values="net",
        hover_data=["serviceName"],
        color="serviceName",
       
    )
    st.plotly_chart(fig5, use_container_width=True)
 
if __name__ == "__main__":
    main()

