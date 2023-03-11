import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import datetime

verint_file = st.sidebar.file_uploader("Upload verint .xlsx file")
if verint_file is not None:
    st.subheader('Verint positions')

    df_verint = pd.read_excel(verint_file, names = [
        'verint_queue',
        'verint_date', 'verint_time', 'verint_interval',
        'verint_call_volume', 'verint_aht', 'verint_sl', 'verint_scheduled_positions', 'verint_positions'])
    df_verint['verint_tc'] = df_verint.apply(lambda x: datetime.datetime.combine(x['verint_date'].date(), x['verint_time']), axis=1)
    # df.set_index('tc', inplace=False)
    df_verint = df_verint.drop(columns=['verint_queue','verint_date', 'verint_time', 'verint_interval'])

    total_positions = sum(df_verint['verint_scheduled_positions'])
    st.metric("man/hours", total_positions / 4)

    # st.area_chart(
    #     data=df_verint,
    #     x="verint_tc",
    #     y=["verint_positions", "verint_scheduled_positions"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=df_verint['verint_tc'], y=df_verint['verint_positions'], name='Required positions', fill='tozeroy'))
    fig.add_trace(
        go.Scatter(x=df_verint['verint_tc'], y=df_verint['verint_scheduled_positions'], name='Verint scheduled positions', fill='tozeroy'))
    fig.update_layout(legend=dict(orientation="h"))
    # fig.update_xaxes(rangeslider_visible=True)

    st.plotly_chart(fig, use_container_width=True, theme='streamlit')

    with st.expander("Verint's data:"):
        st.write(df_verint)


statistics_file = st.sidebar.file_uploader("Upload statistics .json file")
if statistics_file is not None:
    st.subheader('wfm positions')

    df_stats = pd.read_json(statistics_file)
    df_stats['tc'] = pd.to_datetime(df_stats['tc'])

    total_positions = sum(df_stats['scheduled_positions'])
    st.metric("man/hours", total_positions / 4)

    # st.area_chart(
    #     data=df_stats,
    #     x="tc",
    #     y=["positions", "scheduled_positions"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=df_stats['tc'], y=df_stats['positions'], name='Required positions', fill='tozeroy'))
    fig.add_trace(
        go.Scatter(x=df_stats['tc'], y=df_stats['scheduled_positions'], name='Scheduled positions', fill='tozeroy'))
    fig.update_layout(legend=dict(orientation="h"))

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Statistics data:"):
        st.write(df_stats)

if verint_file is not None and statistics_file is not None:
    st.subheader('Required positions diff')

    df = pd.concat([df_verint, df_stats], axis=1, join='inner')

    st.subheader('Verint/wfm service levels')
    fig_sl = px.line(df,  x="tc", y=["verint_sl", "scheduled_service_level"])
    fig_sl.update_layout(legend=dict(orientation="h"))
    st.plotly_chart(fig_sl, use_container_width=True)

    st.subheader('Verint/wfm positions')

    fig_positions = go.Figure()
    fig_positions.add_trace(
        go.Scatter(x=df['tc'], y=df['verint_scheduled_positions'], name='Verint positions', fill='tozeroy'))
    fig_positions.add_trace(
        go.Scatter(x=df['tc'], y=df['scheduled_positions'], name='WFM positions', fill='tozeroy'))
    fig_positions.add_trace(
        go.Scatter(x=df['tc'], y=df['positions'], name='80% SL'))
    fig_positions.add_trace(
        go.Scatter(x=df['tc'], y=df['zero_level_positions'], name='0% SL'))
    fig_positions.update_layout(legend=dict(orientation="h"))
    # fig.update_xaxes(rangeslider_visible=True)

    st.plotly_chart(fig_positions, use_container_width=True, theme='streamlit')

