import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import base64
import wrangler
import updater_service
from dash.dependencies import Input, Output

#DATA ACQUISITION GOES HERE

external_stylesheets = [
        {
            "href": "https://fonts.googleapis.com/css2?"
            "family=Lato:wght@400;700&display=swap",
            "rel": "stylesheet",
            },
        ]


app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
app.title = "Cryptomining Statistics"

logo = "C:/Users/Michael Bodnar/hashtop-dashboard/assets/logo.svg"
encoded_logo = base64.b64encode(open(logo, 'rb').read())

app.layout = html.Div(
        children=[
            html.Div(
                children=[
                    html.Img(src="data:image/svg+xml;base64,{}".format(encoded_logo.decode()), className="header-logo"),
                    html.H1(children="HashTop Dash", className="header-title"),
                    html.P(
                        children="Statistics of your cryptocurrency miner, available anywhere at any time.",
                        className="header-description",
                        ),
                    ],
                className="header",
                ),
            html.Div(
                children=[
                    html.Div(
                        children=dcc.Graph(
                            id="hashrate",
                            config={"displayModeBar": False},
                            figure={
                                "data": [
                                    {
                                        "x": "placeholder",
                                        "y": "placeholder",
                                        "type": "lines",
                                        "hovertemplate": "$%{y:.2f}<extra></extra>",
                                        },
                                    ],
                                "layout": {
                                    "title": {
                                        "text": "Reported Hashrate Over Time",
                                        "x": 0.05,
                                        "xanchor": "left",
                                        },
                                    "xaxis": {"fixedrange": True},
                                    "yaxis": {
                                        "ticksuffix": " H/S",
                                        "fixedrange": True,
                                        },
                                    "colorway": ["#17B897"],
                                    },
                                },
                            ),
                        className="card",
                        ),
                    ],
                className="wrapper",
                ),
            ]
        )


if __name__ == "__main__":
    app.run_server(debug=True)
