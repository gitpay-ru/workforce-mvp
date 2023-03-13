import streamlit as st
import plost
import pandas as pd

st.subheader('Daily demand')
st.write(
    """
    **Daily demand** shows corresponding values spreaded across the month. Mean values are aggregated into hours.
    """
)

json_file = st.sidebar.file_uploader("Upload statistics .json file")
if json_file is not None:
    # Can be used wherever a "file-like" object is accepted:
    df = pd.read_json(json_file)
    df['tc'] = pd.to_datetime(df['tc'])

    st.write(
        """
        Start analysis by selecting one of the metrics to show:
        """
    )

    tab1, tab2, tab3 = st.tabs(["Call volume", "Required Positions", "Scheduled Positions"])

    with tab1:
        plost.time_hist(
            data=df,
            date='tc',
            x_unit='hours',
            y_unit='date',
            color='call_volume',
            aggregate='mean',
        )

    with tab2:
        plost.time_hist(
            data=df,
            date='tc',
            x_unit='hours',
            y_unit='date',
            color='positions',
            aggregate='mean',
        )

    with tab3:
        plost.time_hist(
            data=df,
            date='tc',
            x_unit='hours',
            y_unit='date',
            color='scheduled_positions',
            aggregate='mean',
        )

