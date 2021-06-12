from datetime import time

import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import numpy as np
import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from scipy import signal
import pandas as pd
import pytz
import base64
from dash.dependencies import Input, Output

# DATA ACQUISITION GOES HERE
from dash.exceptions import PreventUpdate

import query_service

external_stylesheets = [
    {
        "href": "https://fonts.googleapis.com/css2?"
                "family=Lato:wght@400;700&display=swap",
        "rel": "stylesheet",
    },
    dbc.themes.BOOTSTRAP
]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
app.title = "Cryptomining Statistics"

encoded_logo = base64.b64encode(open("assets/logo.svg", 'rb').read())

user_dropdown = dcc.Dropdown(
    id='user_dropdown',
    options=query_service.get_users(),
    value=None,
    className='dropdown'
)

miner_dropdown = dcc.Dropdown(
    id='miner_dropdown',
    value=None,
    className='dropdown'
)

tz_dropdown = dcc.Dropdown(
    id='tz_dropdown',
    options=[
        {
            'label': 'Eastern Time',
            'value': 'US/Eastern'
        },
        {
            'label': 'Pacific Time',
            'value': 'US/Pacific'
        },
        {
            'label': 'Central Time',
            'value': 'US/Central'
        }
    ],
    value=None,
    className='dropdown'
)

graphs = html.Div(
    id='graphs',
    style={'padding': 10}
)

app.layout = html.Div(
    children=[
        html.Div(
            children=[
                html.Img(src=f"data:image/svg+xml;base64,{encoded_logo.decode()}", className="header-logo",
                         style={'padding': 10}),
                html.H1(children="HashDash", className="header-title"),
                html.P(
                    children="24/7 statistics of your fully managed cryptominer",
                    className="header-description",
                ),
            ],
            className="header",
        ),
        dbc.Row(
            [
                dbc.Col(html.Div(tz_dropdown), width='auto'),
                dcc.Loading(dbc.Col(html.Div(user_dropdown), width='auto'), type='circle', color="#8a51ffff"),
                dcc.Loading(dbc.Col(html.Div(miner_dropdown), width='auto'), type='circle', color="#8a51ffff")
            ],
            justify='center'
        ),
        dbc.Row(
            dbc.Col(
                dcc.Loading(id="graphs_spinner",
                            children=[graphs],
                            type="default",
                            color="#8a51ffff"),
                className="mt-4"
            ),
            justify='center'
        )
    ]
)


@app.callback(
    Output('miner_dropdown', 'options'),
    [Input('user_dropdown', 'value')])
def update_miners_dropdown(user_id):
    if not user_id:
        raise PreventUpdate
    miners = query_service.get_miners(user_id)
    return miners


@app.callback(
    Output('graphs', 'children'),
    [Input('miner_dropdown', 'value'),
     Input('tz_dropdown', 'value')])
def update_shares_graph(miner_id, timezone):
    if not miner_id:
        raise PreventUpdate
    shares_frame = query_service.get_miner_shares(miner_id)
    health_frame = query_service.get_miner_healths(miner_id)
    if shares_frame.empty or health_frame.empty:
        return html.Div(
            dbc.Alert("No share_data to display for the selected timeframe", color='danger')
        )

    # localize for the tz the user selects
    shares_frame['start'] = shares_frame['start'].dt.tz_convert(pytz.timezone(timezone))
    health_frame['start'] = health_frame['start'].dt.tz_convert(pytz.timezone(timezone))

    # get the total valid shares per time period
    valid_sum = shares_frame.drop(columns=['duration', 'gpu_no']) \
        .groupby('start')['valid'] \
        .sum() \
        .reset_index(name='total_valid')
    window_length = round_down_to_odd(shares_frame.groupby('start').ngroups)
    valid = go.Bar(x=valid_sum['start'], y=valid_sum['total_valid'], name='Valid shares',
                   marker={'color': 'mediumpurple'})
    valid_smoothed_line = go.Line(x=valid_sum['start'],
                                  y=signal.savgol_filter(valid_sum['total_valid'], window_length,
                                                         round_down_to_odd(window_length / 35)),
                                  name='Avg valid shares',
                                  line=dict(color="57CC99", width=2.5, shape='spline', smoothing=10))

    invalid_sum = shares_frame.drop(columns=['duration', 'gpu_no']) \
        .groupby('start')['invalid'] \
        .sum() \
        .reset_index(name='total_invalid')
    invalid = go.Bar(x=invalid_sum['start'], y=invalid_sum['total_invalid'], name='Invalid shares',
                     marker={'color': 'indianred'})
    invalid_smoothed_line = go.Line(x=invalid_sum['start'],
                                    y=signal.savgol_filter(invalid_sum['total_invalid'], window_length,
                                                           round_down_to_odd(window_length / 35)),
                                    name='Avg invalid shares',
                                    line=dict(color="orange", width=2.5, shape='spline', smoothing=10))

    # create graphs for each gpu showing their invalid vs valid percent

    gpu_graphs = []
    merged = pd.merge(shares_frame, health_frame, on=["start", "gpu_no"])
    for gpu_no, data in merged.groupby('gpu_no'):
        gpu_graphs.append(make_gpu_shares_graph(gpu_no, data))

    return html.Div(
        children=[dcc.Graph(
            id="shares",
            figure={
                'data': [valid, valid_smoothed_line, invalid, invalid_smoothed_line],
                'layout':
                    go.Layout(title='Valid/invalid shares past 12 hours', barmode='stack')
            }),
            *gpu_graphs
        ],
        className="card"
    )



def make_gpu_shares_graph(gpu_no, data):
    total_shares = data['valid'].sum() + data['invalid'].sum()
    valid_pct = data['valid'].sum() / total_shares
    invalid_pct = data['invalid'].sum() / total_shares

    # Create figure with secondary y-axis
    fig = make_subplots(rows=2, cols=1)

    # Add traces
    fig.add_trace(
        go.Bar(x=[valid_pct, invalid_pct], y=['Valid', 'Invalid'], orientation='h'),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(x=data['start'], y=data['fan_speed'],
                   name='fan speed',
                   mode='lines'
                   ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(x=data['start'], y=data['temperature'],
                   name='temperature',
                   mode='lines'
                   ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(x=data['start'], y=data['power_draw'],
                   name='power draw',
                   mode='lines',
                   line=dict(color='MediumVioletRed', dash='dot')
                   ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(x=data['start'], y=data['power_limit'],
                   name='power limit',
                   mode='lines',
                   line=dict(color='MediumVioletRed')
                   ),
        row=2,
        col=1,
    )

    # Add figure title
    fig.update_layout(
        title_text=f'Share status for GPU {gpu_no}',
    )

    # Set x-axis title
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_xaxes(row=1, col=1, tickformat='.2%')


    return dcc.Graph(id=f'gpu{gpu_no}', figure=fig)


def round_down_to_odd(f):
    return max(int(np.ceil(f) // 2 * 2 + 1) - 2, 1)


if __name__ == "__main__":
    app.run_server(debug=True)
