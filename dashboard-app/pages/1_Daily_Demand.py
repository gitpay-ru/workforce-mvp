import streamlit as st
import plost
import pandas as pd

csv_file = st.sidebar.file_uploader("Upload input .csv file")
if csv_file is not None:
    # Can be used wherever a "file-like" object is accepted:
    df = pd.read_csv(csv_file)
    df['tc'] = pd.to_datetime(df['tc'])

    plost.time_hist(
        data=df,
        date='tc',
        x_unit='hours',
        y_unit='date',
        color='call_volume',
        aggregate='mean',
    )