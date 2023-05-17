from pathlib import Path
import sys
# this is a hack to make streamlit working with common 'modules'
# need to include in every streamlit page
sys.path.append(str(Path(__file__).resolve().parent))

import plotly.graph_objects as go
import streamlit as st

from utils.data_loaders import get_statistics_df


statistics_file = st.sidebar.file_uploader("Upload statistics .json file")
if statistics_file is not None:
    df_stats = get_statistics_df(statistics_file)

    st.subheader('Required positions vs Scheduled positions')

    st.write(
        """
        This graph compares **Required** positions and **Scheduled** positions by the model.
        It is expected that scheduled positions would be below the required positions line.
        If Scheduled positions are above the required line => this indicates non-optimal scheduling.
        
        You can use a full-screen view to investigate results in details.
        """
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['Required positions'], name='Required positions', fill='tozeroy'))
    fig.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['Scheduled positions'], name='Scheduled positions', fill='tozeroy'))
    fig.update_layout(legend=dict(orientation="h"))
    # fig.update_xaxes(rangeslider_visible=True)

    st.plotly_chart(fig, use_container_width=True, theme='streamlit')

