import streamlit as st

st.set_page_config(
    page_title="WFM Reports",
    page_icon="📈",
    layout="wide"
)

st.sidebar.success("Start analysis by selecting report above.")
# just for testing - how metric are looked like
# m = st.sidebar.metric("Temperature", "70 °F", "1.2 °F")

st.write("# Welcome to WFM Reports 📈")

# col1, col2, col3 = st.columns(3)
# col1.metric("Total Employees", "375")
# col2.metric("Target SL", "80%", "4%")
# col3.metric("Target ART", "9 sec", "-8%")

st.markdown(
    """
    Reporting app is based on a Streamlit -- an open-source app framework built specifically for
    Machine Learning and Data Science projects.

    **👈 Select a report from the left** to see some nice visualizations
"""
)
