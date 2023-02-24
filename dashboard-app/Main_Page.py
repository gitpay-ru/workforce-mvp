import streamlit as st

st.set_page_config(
    page_title="WFM Dashboard",
    page_icon="📈",
)

# sidebar
st.sidebar.success("Start analysis by selecting subject above.")
# just for testing - how metric are looked like
m = st.sidebar.metric("Temperature", "70 °F", "1.2 °F")

# page

st.write("# Welcome to WFM Dashboard 📈")

col1, col2, col3 = st.columns(3)
col1.metric("Total Employees", "375")
col3.metric("Target SL", "80%", "4%")
col2.metric("Target ART", "9 sec", "-8%")

st.markdown(
    """
    Streamlit is an open-source app framework built specifically for
    Machine Learning and Data Science projects.

    **👈 Select a demo from the dropdown on the left** to see some examples
    of what Streamlit can do!

    ### Want to learn more?

    - Check out [streamlit.io](https://streamlit.io)
    - Jump into our [documentation](https://docs.streamlit.io)
    - Ask a question in our [community
      forums](https://discuss.streamlit.io)

    ### See more complex demos

    - Use a neural net to [analyze the Udacity Self-driving Car Image
      Dataset](https://github.com/streamlit/demo-self-driving)
    - Explore a [New York City rideshare dataset](https://github.com/streamlit/demo-uber-nyc-pickups)
"""
)
