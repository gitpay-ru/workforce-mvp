import json
import plotly.graph_objects as go

import streamlit as st
import plost
import pandas as pd

statistics_file = st.sidebar.file_uploader("Upload statistics .json file")
if statistics_file is not None:
    df_stats = pd.read_json(statistics_file)

    df_stats['tc'] = pd.to_datetime(df_stats['tc'])
    df_stats.set_index('tc', inplace=False)

    # for better printing in the legend on graph
    df_stats = df_stats.rename(columns={
        'positions': 'Required positions',
        'scheduled_positions': 'Scheduled positions'}
    )

    st.subheader('Required positions vs Scheduled positions')

    st.write(
        """
        This graph compares **Required** positions and **Scheduled** positions by the model.
        It is expected that scheduled positions would be below the required positions line.
        If Scheduled positions are above the required line => this indicates non-optimal scheduling.
        
        You can use a full-screen view to investigate results in details.
        """
    )

    # wrong Y axis - replace it with plotly graphs, because area chart shows propotion by default
    # st.area_chart(
    #     data = df_stats,
    #     x = "tc",
    #     y = ["positions", "scheduled_positions"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['Required positions'], name='Required positions', fill='tozeroy'))
    fig.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['Scheduled positions'], name='Scheduled positions', fill='tozeroy'))
    fig.update_layout(legend=dict(orientation="h"))
    # fig.update_xaxes(rangeslider_visible=True)

    st.plotly_chart(fig, use_container_width=True, theme='streamlit')

