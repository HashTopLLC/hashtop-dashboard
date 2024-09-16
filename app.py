import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from scipy import signal
import pandas as pd
import base64
from dash.dependencies import Input, Output
from utils import round_down_to_odd, moving_average, json_to_df, random_color, sav_filter
# DATA ACQUISITION GOES HERE
from dash.exceptions import PreventUpdate
from dash_datetimepicker import DashDatetimepicker
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
    value='US/Eastern',
    className='dropdown'
)

stats_type_dropdown = dcc.Dropdown(
    id='stats_type_dropdown',
    options=[
        {
            'label': 'Temperature',
            'value': 'temperature'
        },
        {
            'label': 'Hashrate',
            'value': 'hashrate'
        },
        {
            'label': 'Fan Speed',
            'value': 'fan_speed'
        },
        {
            'label': 'Power',
            'value': 'power'
        },
        {
            'label': 'Core clock',
            'value': 'core_clock'
        },
        {
            'label': 'Memory clock',
            'value': 'mem_clock'
        },
    ],
    value='temperature',
    className='dropdown'
)
combined_graph = html.Div(
    id='combined_graph',
    style={'padding': 10}
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
        dbc.Row([
                dbc.Col([
                    dbc.Row(
                        dbc.Col(
                            html.Div(tz_dropdown),
                        )
                    ),
                    dbc.Row(
                        dbc.Col(
                            html.Div(DashDatetimepicker(id='date_picker_range')),
                        )
                    )
                ], width='auto'),
                    dcc.Loading(dbc.Col(html.Div(user_dropdown), width='auto'), type='circle', color="#8a51ffff"),
                    dcc.Loading(dbc.Col(html.Div(miner_dropdown), width='auto'), type='circle', color="#8a51ffff"),
                    dbc.Col(html.Div(stats_type_dropdown), width='auto'),
                ],
            justify='center'
        ),
        dbc.Row(
            dbc.Col([
                dcc.Loading([
                    dbc.Col(dcc.Store(id="miner_shares_data"), width='auto'),
                    dbc.Col(dcc.Store(id="miner_healths_data"), width='auto'),
                ],
                    type="default",
                    color="#8a51ffff"
                )],
                className="mt-4"
            )
        ),
        dbc.Row(
            dbc.Col(
                dcc.Loading(id="combined_graph_spinner",
                            children=[combined_graph],
                            type="default",
                            color="#8a51ffff"),
                className="mt-4"
            ),
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
    Output('miner_shares_data', 'data'),
    [Input('miner_dropdown', 'value'),
     Input('date_picker_range', 'startDate'),
     Input('date_picker_range', 'endDate')
     ])
def update_miner_shares(miner_id, start_date, end_date):

    if not miner_id:
        raise PreventUpdate
    shares_frame = query_service.get_miner_shares(miner_id, start_date, end_date)
    if shares_frame.empty:
        return html.Div(
            dbc.Alert("No share data to display for the selected timeframe", color='danger')
        )

    return shares_frame.to_json(orient='records', date_format='iso')


@app.callback(
    Output('miner_healths_data', 'data'),
    [Input('miner_dropdown', 'value'),
     Input('date_picker_range', 'startDate'),
     Input('date_picker_range', 'endDate')
     ])
def update_miner_healths(miner_id, start_date, end_date):

    if not miner_id:
        raise PreventUpdate
    healths_frame = query_service.get_miner_healths(miner_id, start_date, end_date)
    if healths_frame.empty:
        return html.Div(
            dbc.Alert("No health data to display for the selected timeframe", color='danger')
        )

    return healths_frame.to_json(orient='records', date_format='iso')


@app.callback(
    Output('graphs', 'children'),
    [Input('miner_shares_data', 'data'),
     Input('miner_healths_data', 'data'),
     Input('tz_dropdown', 'value')])
def update_shares_graph(shares_data, healths_data, timezone):
    if not shares_data or not healths_data:
        raise PreventUpdate

    healths_frame = json_to_df(healths_data, timezone)
    shares_frame = json_to_df(shares_data, timezone)

    # get the total valid shares per time period
    valid_sum = shares_frame.drop(columns=['duration', 'gpu_no']) \
        .groupby('start')['valid'] \
        .sum() \
        .reset_index(name='total_valid')
    window_length = shares_frame.groupby('start').ngroups
    valid = go.Bar(x=valid_sum['start'], y=valid_sum['total_valid'], name='Valid shares',
                   marker={'color': 'mediumpurple'})
    valid_avg_ys = sav_filter(valid_sum['total_valid'], window_length)
    valid_smoothed_line = go.Line(x=valid_sum['start'],
                                  y=valid_avg_ys,
                                  name='Avg valid shares',
                                  line=dict(color="57CC99", width=2.5, shape='spline', smoothing=10))

    invalid_sum = shares_frame.drop(columns=['duration', 'gpu_no']) \
        .groupby('start')['invalid'] \
        .sum() \
        .reset_index(name='total_invalid')
    invalid = go.Bar(x=invalid_sum['start'], y=invalid_sum['total_invalid'], name='Invalid shares',
                     marker={'color': 'indianred'})

    invalid_avg_ys = sav_filter(invalid_sum['total_invalid'], window_length)
    invalid_smoothed_line = go.Line(x=invalid_sum['start'],
                                    y=invalid_avg_ys,
                                    name='Avg invalid shares',
                                    line=dict(color="orange", width=2.5, shape='spline', smoothing=10))

    # create graphs for each gpu showing their invalid vs valid percent
    gpu_graphs = []
    merged = pd.merge(shares_frame, healths_frame, on=["start", "gpu_no"])
    for gpu_no, data in merged.groupby('gpu_no'):
        gpu_graphs.append(make_gpu_shares_graph(gpu_no, data))

    return html.Div(
        children=[
            dcc.Graph(
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


@app.callback(
    Output('combined_graph', 'children'),
    [Input('miner_healths_data', 'data'),
     Input('stats_type_dropdown', 'value'),
     Input('tz_dropdown', 'value')])
def update_combined_graph(healths_data, stat, timezone):
    if not healths_data:
        raise PreventUpdate

    healths_frame = json_to_df(healths_data, timezone)

    if stat == 'power':
        return make_power_graph(healths_frame)

    window_length = healths_frame.groupby('start').ngroups + 2
    fig = make_subplots(rows=1, cols=1)

    for gpu_no, data in healths_frame.groupby('gpu_no'):
        # calculate a moving average of the y values to smooth them out
        avg_ys = moving_average(data[stat], int(window_length / 10))
        fig.add_trace(
            go.Scatter(x=data['start'], y=avg_ys,
                       name=data['gpu_name'].iloc[0],
                       mode='lines'
                       ),
            row=1,
            col=1,
        )

    if stat == 'temperature':
        fig.update_yaxes(title=dict(text='Temperature (°C)'), hoverformat='.0f')
    elif stat == 'fan_speed':
        fig.update_yaxes(title=dict(text='Fan speed (%)'), tickformat='%f')
    elif stat == 'hashrate':
        fig.update_yaxes(title=dict(text='Hashrate (MH/s)'), tickformat='.2f')
    elif stat == 'mem_clock' or stat == 'core_clock':
        fig.update_yaxes(title=dict(text='Clock (Mhz)'))

    fig.update_xaxes(title=dict(text='Time'))
    fig.update_xaxes(rangeslider_visible=True)

    return dcc.Graph(id=f'combined', figure=fig)


def make_power_graph(data):
    fig = make_subplots(rows=1, cols=1)
    window_length = max(int(data.groupby('start').ngroups / 100), 1)
    total_gpus = data['gpu_no'].max()

    for gpu_no, data in data.groupby('gpu_no'):
        print(data['power_draw'])
        # generate a color for the pair of power use/limit for this gpu
        color = random_color()
        # calculate a moving average of the y values to smooth them out
        avg_power_draw = moving_average(data['power_draw'], window_length)

        gpu_name = data['gpu_name'].iloc[0]
        fig.add_trace(
            go.Scatter(x=data['start'], y=avg_power_draw,
                       name=f'{gpu_name} Power used',
                       mode='lines',
                       legendgroup=f'gpu_{gpu_no}',
                       line=dict(color=color)
                       ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=data['start'], y=data['power_limit'],
                       name=f'{gpu_name} Power limit',
                       mode='lines',
                       legendgroup=f'gpu_{gpu_no}',
                       line=dict(dash='dot', color=color),
                       ),
            row=1,
            col=1,
        )
    fig.update_yaxes(title=dict(text='Power in watts'), hoverformat='.0f')
    fig.update_xaxes(title=dict(text='Time'))

    return dcc.Graph(id=f'combined', figure=fig)


def make_gpu_shares_graph(gpu_no, data):
    total_shares = data['valid'].sum() + data['invalid'].sum()
    valid_pct = data['valid'].sum() / total_shares
    invalid_pct = data['invalid'].sum() / total_shares

    # Create figure with secondary y-axis
    fig = make_subplots(rows=2, cols=1)

    # Add traces
    fig.add_trace(
        go.Bar(x=[valid_pct, invalid_pct], y=['Valid', 'Invalid'], orientation='h', name='Shares distribution'),
        row=1,
        col=1
    )

    fig.add_trace(
        go.Scatter(x=data['start'], y=data['fan_speed'],
                   name='Fan speed',
                   mode='lines'
                   ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(x=data['start'], y=data['temperature'],
                   name='Temperature',
                   mode='lines'
                   ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(x=data['start'], y=data['hashrate'],
                   name='Hashrate',
                   mode='lines'
                   ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(x=data['start'], y=data['power_draw'],
                   name='Power draw',
                   mode='lines',
                   line=dict(color='MediumVioletRed', dash='dot')
                   ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(x=data['start'], y=data['power_limit'],
                   name='Power limit',
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


if __name__ == "__main__":
    app.run_server(debug=True)
