import dash
from dash import dcc, dash_table, html, ctx #to be consolidated
import plotly.express as px
import pandas as pd
import requests
from datetime import date
import hashlib
import dash_bootstrap_components as dbc
import datetime
from dash.dependencies import Output, Input, State

#Firstly, Data frame to hold the data we will sjopw and in the url.
#We don't import pathlib because we are going to call data from the pre-built API(s) for the URL

vis = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])#, suppress_callback_exceptions=True)
server = vis.server

def get_energy_data():#the specific url
    return pd.DataFrame({"Date": pd.date_range(start='2022-01-01', end='2022-01-31').to_list(),
                       "Price": list(range(1, 32))})

def get_personal_details_html():
    return html.Div([html.H1("Personal Details")])

def get_energy_display_html(logged_in):

    energy_children = []
    date_picker = dcc.DatePickerRange(     #reference
        id='my-date-picker-range',
        min_date_allowed=date(2018, 8, 5),
        max_date_allowed=date(2020, 9, 30),
        initial_visible_month=date(2020, 9, 1),
        start_date=date(2020, 6, 1),
        end_date=date(2020, 9, 30),
        style = {"padding-left": "50px"}
    )

    graph_df = get_energy_data() #We can refine get_energy_data and do so in isolation, because we have defined the graph_df

    graph = px.line(graph_df, x="Date", y="Price") #I have the dataframe defined, so I can just use the name of the columnsn

    bar_graph = px.bar(graph_df, x="Date", y="Price")

    series_checklist = dcc.Checklist(
        ['Oil', 'Gas', 'MA90', 'Forecast'] if logged_in else ['Oil', 'Gas'],
        ['Gas'],
        inline=True,
        id="checklist"
    )

    energy_children.extend([date_picker,
                            html.Div(id="date_picker"),
                            html.Div(id="line_graph", children=dcc.Graph(figure=graph)),
                            html.Div(id="features", children=series_checklist, style={"padding-left":"50px"}),
                            html.Br(),
                            html.Div(id="bar_graph", children=dcc.Graph(figure=bar_graph))
                            ])

    return html.Div(children=energy_children)

logged_in = False

#The callback SECTION

@vis.callback(dash.dependencies.Output("features", "children"),
              dash.dependencies.Input("loggedin", "value"))

def update_callback(loggedin):
    extra_features = loggedin == "True"
    series_checklist = dcc.Checklist(
            ['Oil', 'Gas', 'MA90', 'Forecast'] if extra_features else ['Oil', 'Gas'],
            ['Gas'],
            inline=True,
            id="checklist"
    )
    return series_checklist

@vis.callback([dash.dependencies.Output('line_graph', 'children'),
               dash.dependencies.Output('bar_graph', 'children')],
              [dash.dependencies.Input('checklist', 'value'),
               dash.dependencies.Input('my-date-picker-range', 'start_date'),
               dash.dependencies.Input('my-date-picker-range', 'end_date')])

def update_line_graph(checked_series, start_date, end_date):
    show_MA90 = "MA90" in checked_series
    show_Forecast = "Forecast" in checked_series
    df = pd.DataFrame()
    series_names = ""
    if "Oil" in checked_series:
        Oil_df = get_fuel_df("127.0.0.1:5000", "Oil", start_date, end_date, show_MA90, show_Forecast)
        df = pd.concat([df, Oil_df])
        series_names = series_names + "Oil"
    if "Gas" in checked_series:
        Gas_df = get_fuel_df("127.0.0.1:5000", "Gas", start_date, end_date, show_MA90, show_Forecast)
        df = pd.concat([df, Gas_df])
        series_names = series_names + "Gas" if len(series_names) == 0 else series_names + " & Gas"
    if len(df)>0:
        graph = px.line(df, x="Date", y="Price", color="Series")
        graph.update_layout(title_text="Timeline for " + series_names, title_x=0.5)
        changes_df = get_daily_fuel_changes_df(df[(df["Series"] == "Oil") | (df["Series"] == "Gas")])
        bar_graph = px.bar(changes_df, x="Date", y="Change", color="Series")
        bar_graph.update_layout(title_text="Percentage daily change " + series_names, title_x=0.5)
        return dcc.Graph(figure=graph), dcc.Graph(figure=bar_graph)
    else:
        return html.H1("Please select a series to display"), html.H1("Please select a series to desplay")


def get_daily_fuel_changes_df(df):
    Oil_df = df[df["Series"] == "Oil"]
    Gas_df = df[df["Series"] == "Gas"]
    change_df = pd.DataFrame()
    if len(Oil_df)>0:
        Oil_df["Change"] = Oil_df["Price"].pct_change()
        change_df = pd.concat([change_df, Oil_df[["Date", "Change", "Series"]]])

    if len(Gas_df)>0:
        Gas_df["Change"] = Gas_df["Price"].pct_change()
        change_df = pd.concat([change_df, Gas_df[["Date", "Change", "Series"]]])
    return change_df


def get_fuel_df(host_name, fuel, start_date, end_date, show_MA90, show_Forecast):
    has_start_date = start_date != None
    has_end_date = end_date != None
    url = f"http://{host_name}/fuelprice?series={fuel}Price"
    if has_start_date:
        url += "&from_date="+start_date
    if has_end_date:
        url += "&to_date="+end_date
    if show_MA90:
        url += "&MA90=True"
    if show_Forecast:
        url += "&Forecast=10"
    response = requests.get(url)
    df = pd.DataFrame.from_dict(response.json()["Prices"])
    df_fuel = df[["Date", "Price"]]
    df_fuel["Series"] = fuel
    if show_MA90:
        df_MA90 = df[["Date", "MA90"]]
        df_MA90 = df_MA90.dropna()
        df_MA90 = df_MA90.rename(columns={"MA90":"Price"})
        df_MA90["Series"] = f"{fuel}_MA90"
        df_fuel = pd.concat([df_fuel, df_MA90])
    if show_Forecast:
        df_Forecast = pd.DataFrame.from_dict(response.json()["Forecast"])
        df_Forecast["Series"] = f"{fuel} Forecast"
        df_fuel = pd.concat([df_fuel, df_Forecast])
    return df_fuel

@vis.callback(dash.dependencies.Output('page_header', 'children'),
              [dash.dependencies.Input('submit_login', 'n_clicks'),
              dash.dependencies.State('username', 'value'),
              dash.dependencies.State('password', 'value')])

def do_login(button_id, username, password):
    if ctx.triggered_id == "submit_login":
        if username != None:
            login_success = api_login(username, password)
            if login_success:
                return get_page_header_html(username)
    return get_page_header_html(None)

def api_login(username, password):
    if username == None or password == None:
        return False
    if len(username) == 0 or len(password) == 0:
        return False
    hash_password = hashlib.md5(password.encode()).hexdigest()
    print(hash_password)
    url = f"http://127.0.0.1:5000/login?Username={username}&P_Hash={hash_password}"
    response = requests.get(url)
    if response.json()["status"] == "OK":
        return True
    return False

def display_page(pathname):
    if logged_in:

        if pathname == '/energy_display':
            return get_energy_display_html()
        elif pathname == '/personal_details':
            return get_personal_details_html()

    #else:
        #get_login_html
    # check if the person is logged in,
    # go to energy price display

    #return get_login_html()

def get_page_header_html(username):
    controls = []
    if username == None:
        controls.extend([html.Li(children=dbc.Input(id="username", type="text", placeholder="Enter Username")),
                         html.Li(children=dbc.Input(id="password", type="password", placeholder="Enter Password")),
                         dcc.Input(id="loggedin", type="hidden", value="False"),
                         html.Li(children=dbc.Button("Log in", id="submit_login")),
                         html.Li(children=dbc.Button("Sign up", id="submit_sign_up"))])

    else:
        controls.extend([html.H2("Hello " + username, id="username", style={"padding-right": "50px"}),
                        dcc.Input(id="password", type="hidden", value=""),
                         dcc.Input(id="loggedin", type="hidden", value="True"),
                        dbc.DropdownMenu(
                        label="My Account",
                        children=[
                        dbc.DropdownMenuItem("Personal Details"),  # email, phine numbver etc
                        dbc.DropdownMenuItem("My Energy Usage"),  # email, phine numbver etc
                        dbc.DropdownMenuItem("Log out", id="submit_login", n_clicks=0)]
                        )])
    logformatting = [
        html.Div(id="title", className="navbar-header",
                 children=html.A("Energy Price Display", className="navbar-brand", style={'font-family': 'Barcode',
                                                                                          'font-size': '86px'})),
        html.Ul(className="nav navbar-nav navbar-right float-right", children=controls)
    ]

    login_div = html.Div([
        html.Nav(id="navbar", className="navbar navbar-expand-lg navbar-light bg-light",
                 children=html.Div(className="container-fluid", children=logformatting))])
    return login_div

if __name__ == "__main__":
    vis.layout = html.Div([
        dcc.Location(id='url', refresh=False),
        html.Div(id='page_header', children=get_page_header_html(None)),
        html.Div(id='page_content', children=get_energy_display_html(True))
    ])
    vis.run_server(debug=True)

