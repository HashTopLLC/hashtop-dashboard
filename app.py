from datetime import time

import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import plotly.express as px
import pandas as pd
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

user_list_dropdown = dcc.Dropdown(
    id='user_list_dropdown',
    options=query_service.get_users(),
    value=None,
    className='dropdown'
)

miner_list_dropdown = dcc.Dropdown(
    id='miner_list_dropdown',
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
                dcc.Loading(dbc.Col(html.Div(user_list_dropdown), width='auto'), type='circle', color="#8a51ffff"),
                dcc.Loading(dbc.Col(html.Div(miner_list_dropdown), width='auto'), type='circle', color="#8a51ffff")
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
    Output('miner_list_dropdown', 'options'),
    [Input('user_list_dropdown', 'value')])
def update_miners_dropdown(user_id):
    if not user_id:
        raise PreventUpdate
    miners = query_service.get_miners(user_id)
    return miners


@app.callback(
    Output('graphs', 'children'),
    [Input('miner_list_dropdown', 'value')])
def update_shares_graph(miner_id):
    if not miner_id:
        raise PreventUpdate
    share_data = query_service.get_miner_shares(miner_id)
    if not share_data:
        return html.Div(
            dbc.Alert("One of the hamsters running our server died, please try again", color='danger')
        )
    frame = pd.json_normalize(share_data)

    multi = frame.set_index(['gpu_no', 'type']).sort_index()

    share_counts = frame.groupby(['gpu_no', 'type']).size().reset_index(name='count')

    print("FRAME")
    print(frame)
    fig = px.bar(share_counts, x='gpu_no', y='count', color="type", title="Shares by GPU")
    return html.Div(
        dcc.Graph(
            id="shares",
            figure=fig,
            className="card"
        )
    )


if __name__ == "__main__":
    app.run_server(debug=True)
