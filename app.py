import os
import math
import pickle
import pathlib
import warnings
warnings.filterwarnings('ignore')
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State, ClientsideFunction
import plotly.graph_objs as go
import plotly.express as px
import plotly.figure_factory as ff
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import datetime

# Get relative data folder
PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("data").resolve()

# Initialize app
app = dash.Dash(
    __name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}]
)
server = app.server

# Load full data
data = pd.read_csv(r'https://covid.ourworldindata.org/data/owid-covid-data.csv', parse_dates = ['date'],
                   usecols = ['iso_code','continent','location','date','total_cases','new_cases','total_deaths',
                              'new_deaths','icu_patients','hosp_patients','new_tests','total_tests'])
metadata = pd.read_csv(
    'https://github.com/owid/covid-19-data/blob/master/public/data/owid-covid-codebook.csv?raw=true'
)

# Select only a few columns
df1 = data.drop_duplicates().sort_values(['location','date']).reset_index(drop = True)

# Drop World and International rows
df2 = df1[~df1.location.isin(['World','International'])].copy().reset_index(drop = True)
# Remove negative daily increases
df2 = df2[~(df2['new_cases']<0)]
df2 = df2[~(df2['new_deaths']<0)]
df2 = df2[~(df2['new_tests']<0)]
df2 = df2[~(df2['hosp_patients']<0)]
df2 = df2.reset_index(drop = True)
# Add cumsum for hosp_patients and icu_patients
df2['total_hosp_patients'] = df2.groupby(['location'])['hosp_patients'].transform(pd.Series.cumsum)
df2['total_icu_patients'] = df2.groupby(['location'])['icu_patients'].transform(pd.Series.cumsum)

# Get list of unique countries for reference
df3 = df2[['iso_code','location']].drop_duplicates().sort_values(['location']).reset_index(drop = True)

# Generate options
country_options = sorted(df2['location'].unique().tolist())
continent_options = sorted(df2['continent'].unique().tolist())

# Helper functions
def human_format(num):
    if num == 0:
        return "0"

    magnitude = int(math.log(num, 1000))
    mantissa = str(int(num / (1000 ** magnitude)))
    return mantissa + ["", "K", "M", "G", "T", "P"][magnitude]

def flatten_list(l):
    return sorted([item for sublist in l for item in sublist])

def subset_data(continent, country_list, start_date, end_date):
    end_date = datetime.datetime.strptime(end_date.split('T')[0],'%Y-%m-%d').date()
    end_date = datetime.datetime.combine(end_date, datetime.time(23,59,59))
    start_date = datetime.datetime.strptime(start_date.split('T')[0],'%Y-%m-%d').date()
    start_date = datetime.datetime.combine(start_date, datetime.time(0,0,0))
    if country_list != None:
        country_list = flatten_list([country_list])
        df = df2[df2.location.isin(country_list)]
        df = df[((df.date >= start_date) & (df.date <= end_date))]
    else:
        if continent == 'All':
            df = df2[df2.date <= end_date]
        else:
            df = df2[df2.continent == continent]
            df = df[((df.date >= start_date) & (df.date <= end_date))]
    df = df.sort_values(['location','date']).reset_index(drop = True)
    return df

def get_total(input_df, metric = 'cases', level = 'country', sum = False):
    if level == 'country':
        df = input_df[['location','total_{}'.format(metric)]]
        df = df.groupby('location').max().reset_index()
        df = df.sort_values(['location']).reset_index(drop = True)
        df = pd.merge(df,df3,on='location',how='left')
    else:
        df = input_df[['continent','location','total_{}'.format(metric)]]
        df = df.groupby(['continent','location']).max().reset_index().drop(['location'], axis = 1)
        df = df.groupby(['continent']).sum().reset_index()
        df = df.sort_values(['continent']).reset_index(drop = True)
    if sum == True:
        output = df['total_{}'.format(metric)].sum()
        return output
    else:
        return df

def get_new(input_df, metric = 'cases', level = 'country', sum = False):
    if level == 'country':
        try:
            df = input_df[['location','new_{}'.format(metric)]]
        except:
            df = input_df[['location',metric]]
        df = df.groupby('location').sum().reset_index()
        df = df.sort_values(['location']).reset_index(drop = True)
        df= pd.merge(df,df3,on='location',how='left')
    else:
        try:
            df = input_df[['continent','new_{}'.format(metric)]]
        except:
            df = input_df[['continent',metric]]
        df = df.groupby(['continent']).sum().reset_index()
        df = df.sort_values(['continent']).reset_index(drop = True)
    if sum == True:
        try:
            output = df['new_{}'.format(metric)].sum()
        except:
            output = df[metric].sum()
        return output
    else:
        return df

def get_average(input_df, metric = 'cases', level = 'country'):
    if level == 'country':
        try:
            df = input_df[['location','new_{}'.format(metric)]]
        except:
            df = input_df[['location',metric]]
        df = df.groupby('location').mean().reset_index()
        df = df.sort_values(['location']).reset_index(drop = True)
        df= pd.merge(df,df3,on='location',how='left')
    else:
        try:
            df = input_df[['continent','new_{}'.format(metric)]]
        except:
            df = input_df[['continent',metric]]
        df = df.groupby(['continent']).mean().reset_index()
        df = df.sort_values(['continent']).reset_index(drop = True)
    try:
        df = df.dropna(subset = [metric]).reset_index(drop = True)
    except:
        df = df.dropna(subset = ['new_{}'.format(metric)]).reset_index(drop = True)
    return df
        
########### Set up the charts
### Plot a map of country cases
map1_df = df2[['iso_code','location','total_cases']].copy()
map1_df = map1_df.dropna(subset = ['total_cases'], axis = 0)
map1_df = map1_df.groupby(['iso_code','location']).max().reset_index()
map1_df['total_cases'] = map1_df['total_cases'].astype(int)

map1 = px.choropleth(map1_df, locations="iso_code", #[map1_df.location.isin(['United States','Canada'])]
                    color = "total_cases", # lifeExp is a column of gapminder
                    hover_name = "location", # column to add to hover information
                    color_continuous_scale = px.colors.sequential.Blues,
                    title = "Map of COVID-19 Cases (all countries)",
                    labels={'iso_code':'ISO','total_cases':'Total cases','location':'Country'}
                    # projection = "natural earth"
                   )
map1.update_layout(
    margin={"r":0,"t":45,"l":0,"b":5},
    coloraxis_showscale=True,autosize=True,
    paper_bgcolor='rgb(249,249,249)',
    plot_bgcolor='rgb(249,249,249)',
    geo=dict(bgcolor= 'rgb(249,249,249)'))
map1.update_geos(fitbounds="locations", showcountries=True, countrycolor="Black", visible=False) #showsubunits=True, subunitcolor="Blue",

### Plot a graph showing daily new cases vs cumulative cases
line1_df1 = df2[['date','total_cases']].groupby('date').sum().reset_index()
line1_df2 = df2[['date','new_cases']].groupby('date').sum().reset_index()

line1 = make_subplots(specs=[[{"secondary_y": True}]], shared_xaxes=True)
line1.add_trace(
    go.Scatter(
        x=line1_df2['date'],
        y=line1_df2['new_cases'],
        mode='lines',
        name='New daily cases'
        ),
    secondary_y=False
)
line1.add_trace(
    go.Scatter(
        x=line1_df1['date'],
        y=line1_df1['total_cases'],
        mode='lines',
        name='Total cases'
        ),
    secondary_y=True
)
line1.update_layout(
    title = 'New daily cases vs Total cases over time (all countries)',
    plot_bgcolor='rgb(249,249,249)', paper_bgcolor='rgb(249,249,249)'
)
# Set y-axes titles
line1.update_yaxes(title_text="New cases", secondary_y=False)
line1.update_yaxes(title_text="Total cases", secondary_y=True)

### Plot a graph showing new cases per country
line2 = px.line(
    df2,
    x="date",
    y="total_cases",
    color='location',
    labels={
        "location": "Country",
        "date": "Date",
        "total_cases": "Total cases"
    }
)
line2.update_layout(
    title = 'Total cases over time across selected countries',
    plot_bgcolor='rgb(249,249,249)', paper_bgcolor='rgb(249,249,249)',
)
line2.update_xaxes(showgrid=False)
line2.update_yaxes(showgrid=False)

### Plot a top N chart of average metric
bar1_df = get_average(df2)
bar1 = px.bar(bar1_df.sort_values(['new_cases'], ascending = True).tail(10),
             y = 'location',
             x = 'new_cases',
             title = "Top {} Countries worldwide in terms of Average daily COVID cases".format(len(bar1_df.sort_values(['new_cases'], ascending = True).tail(10))),
             labels = {'location':'Country','new_cases':'Average daily cases'},
             orientation='h')
bar1.update_layout(
    plot_bgcolor='rgb(249,249,249)', paper_bgcolor='rgb(249,249,249)',
)
bar1.update_traces(marker_color='#119DFF')
bar1.update_xaxes(showgrid=False)
bar1.update_yaxes(showgrid=False)

# Create global chart template
mapbox_access_token = open(r"assets/token.file").read()

layout = dict(
    autosize=True,
    automargin=True,
    margin=dict(l=30, r=30, b=20, t=40),
    hovermode="closest",
    plot_bgcolor="#F9F9F9",
    paper_bgcolor="#F9F9F9",
    legend=dict(font=dict(size=10), orientation="h"),
    title="Satellite Overview",
    mapbox=dict(
        accesstoken=mapbox_access_token,
        style="light",
        center=dict(lon=-78.05, lat=42.54),
        zoom=7,
    )
)

tabs_styles = {
    'height': '44px'
}
tab_style = {
    'borderBottom': '1px solid #d6d6d6',
    'padding': '6px',
    'fontWeight': 'bold'
}

tab_selected_style = {
    'borderTop': '1px solid #d6d6d6',
    'borderBottom': '1px solid #d6d6d6',
    'backgroundColor': '#119DFF',
    'color': 'white',
    'padding': '6px'
}

# Create app layout
app.layout = html.Div(
    [
        dcc.Store(id="aggregate_data"),
        # empty Div to trigger javascript file for graph resizing
        html.Div(id="output-clientside"),
        html.Div(
            [
                html.Div(
                    [
                        html.Img(
                            src=app.get_asset_url("dash-logo.png"),
                            id="plotly-image",
                            style={
                                "height": "60px",
                                "width": "auto",
                                "margin-bottom": "25px",
                            },
                        )
                    ],
                    className="one-third column",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.H3(
                                    "World COVID-19 Cases",
                                    style={"margin-bottom": "0px"},
                                ),
                                html.H5(
                                    "Country Comparison", style={"margin-top": "0px"}
                                ),
                            ]
                        )
                    ],
                    className="one-half column",
                    id="title",
                ),
                html.Div(
                    [
                        html.A(
                            html.Button("Source code", id="learn-more-button"),
                            href='https://github.com/at-nl/dash-demo1',
                        )
                    ],
                    className="one-third column",
                    id="button",
                ),
            ],
            id="header",
            className="row flex-display",
            style={"margin-bottom": "25px"},
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.P(
                            [html.Strong("Filter by Date Range:")],
                            className="control_label",
                            title = metadata[metadata.column == 'date']['description'].tolist()[0]
                        ),
                        dcc.DatePickerRange(
                            id='date_range_picker',
                            min_date_allowed=df2.date.min(),
                            max_date_allowed=datetime.datetime.now().date(),
                            initial_visible_month=df2.date.min(),
                            start_date = df2.date.min(),
                            end_date = datetime.datetime.now().date(),
                            className = 'dcc_control'
                        ),
                        html.P(
                            [html.Strong("Filter by Continent:")],
                            className="control_label",
                            title = metadata[metadata.column == 'continent']['description'].tolist()[0]
                        ),
                        dcc.RadioItems(
                            id="continent_selector",
                            options=[
                                {"label": 'All', "value": 'All', 'disabled':False}
                            ] + [
                                {"label": c, "value": c, 'disabled':False} for c in continent_options
                            ],
                            value = 'All',
                            labelStyle={"display": 'block'},
                            className="dcc_control",
                        ),
                        html.P(
                            [html.Strong("Filter by Country:")],
                            className="control_label",
                            title = metadata[metadata.column == 'location']['description'].tolist()[0]
                        ),
                        dcc.Dropdown(
                            id = 'select_country',
                            multi = True,
                            clearable = True,
                            disabled = False,
                            style = {'display': True},
                            # value = 'United States',
                            placeholder = 'Select country',
                            options = [
                                {'label': c, 'value': c} for c in country_options
                            ],
                            className = 'dcc_control'
                        ),
                        html.P(
                            "The current selection contains {} countries.".format(len(country_options)),
                            className="control_label",
                            id='country-count'
                        )
                    ],
                    className="pretty_container four columns",
                    id="cross-filter-options",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [html.H6(children = human_format(df2[['location','total_cases']].groupby('location').max()['total_cases'].sum()),
                                             id="well_text"), html.P("Total cases")],
                                    id="wells",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(children = human_format(df2[['location','total_deaths']].groupby('location').max()['total_deaths'].sum()),
                                             id="gasText"), html.P("Total deaths")],
                                    id="gas",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(children = human_format(df2[['location','total_tests']].groupby('location').max()['total_tests'].sum()),
                                             id="oilText"), html.P("Total tests")],
                                    id="oil",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(children = human_format(df2['hosp_patients'].sum()),
                                             id="waterText"), html.P("Total hospital patients")],
                                    id="water",
                                    className="mini_container",
                                ),
                            ],
                            id="info-container",
                            className="row container-display",
                        ),
                        html.Div(
                            children = [
                                dcc.Tabs(
                                    id='tabs-1',
                                    value='total',
                                    children=[
                                        dcc.Tab(
                                            label='Up-to-date Total',
                                            value='total',
                                            style=tab_style,
                                            selected_style=tab_selected_style,
                                            id = 'total-tab'
                                        ),
                                        dcc.Tab(
                                            label='Daily change',
                                            value='new',
                                            style=tab_style,
                                            selected_style=tab_selected_style,
                                            id = 'new-tab'
                                        )
                                    ]
                                ),
                                dcc.Tabs(
                                    id='tabs-2',
                                    value='cases',
                                    children=[
                                        dcc.Tab(
                                            label='Cases',
                                            value='cases',
                                            style=tab_style,
                                            selected_style=tab_selected_style,
                                            id = 'cases-tab'
                                        ),
                                        dcc.Tab(
                                            label='Deaths',
                                            value='deaths',
                                            style=tab_style,
                                            selected_style=tab_selected_style,
                                            id = 'deaths-tab'
                                        ),
                                        dcc.Tab(
                                            label='Tests',
                                            value='tests',
                                            style=tab_style,
                                            selected_style=tab_selected_style,
                                            id = 'tests-tab'
                                        ),
                                        dcc.Tab(
                                            label='Hospital patients',
                                            value='hosp_patients',
                                            style=tab_style,
                                            selected_style=tab_selected_style,
                                            id = 'patients-tab'
                                        )
                                    ]
                                ),
                            ],
                            id="tabContainer",
                            className="pretty_container"
                        ),
                        
                        html.Div(
                            [
                                dcc.Graph(
                                    id="count_graph",
                                    figure = line2
                                )
                            ],
                            id="countGraphContainer",
                            className="pretty_container"
                        ),
                    ],
                    id="right-column",
                    className="eight columns",
                ),
            ],
            className="row flex-display",
        ),
        html.Div(
            [
                html.Div(
                    [
                        dcc.Graph(
                            id="main_graph",
                            figure = map1
                        )
                    ],
                    className="pretty_container seven columns",
                ),
                html.Div(
                    [
                        dcc.Graph(
                            id="individual_graph",
                            figure = bar1
                        )
                    ],
                    className="pretty_container five columns",
                ),
            ],
            className="row flex-display",
        ),
        # html.Div(
        #     [
        #         html.Div(
        #             [dcc.Graph(id="pie_graph")],
        #             className="pretty_container seven columns",
        #         ),
        #         html.Div(
        #             [dcc.Graph(id="aggregate_graph")],
        #             className="pretty_container five columns",
        #         ),
        #     ],
        #     className="row flex-display",
        # ),
    ],
    id="mainContainer",
    style={"display": "flex", "flex-direction": "column"},
)

############ CREATE CALLBACKS ############

# Update country selection from continent filter
@app.callback(
    Output('select_country', 'value'),
    [
        Input('continent_selector', 'value')
    ],
)
def update_countries(continent):
    if continent == 'All':
        countries = country_options
    else:
        countries = sorted(df2[df2.continent==continent].location.unique().tolist())
    return countries

# Update 4 cards
@app.callback(
    [
        Output('well_text','children'),
        Output('gasText','children'),
        Output('oilText','children'),
        Output('waterText','children')
    ],
    [
        Input('continent_selector', 'value'),
        Input('select_country', 'value'),
        Input('date_range_picker', 'start_date'),
        Input('date_range_picker', 'end_date')
    ]
)
def update_cards(continent, country_list, start_date, end_date):
    df = subset_data(continent, country_list, start_date, end_date)
    cases = get_total(df, sum = True)
    deaths = get_total(df, metric = 'deaths', sum = True)
    tests = get_total(df, metric = 'tests', sum = True)
    hosp_patients = get_new(df, metric = 'hosp_patients', sum = True)
    return human_format(cases), human_format(deaths), human_format(tests), human_format(hosp_patients)

# Update line graph
@app.callback(
    Output('count_graph', 'figure'),
    [
        Input('continent_selector', 'value'),
        Input('select_country', 'value'),
        Input('date_range_picker', 'start_date'),
        Input('date_range_picker', 'end_date'),
        Input('tabs-1', 'value'),
        Input('tabs-2', 'value')
    ]
)
def update_line_graph1(continent, country_list, start_date, end_date, tab1, tab2):
    df = subset_data(continent, country_list, start_date, end_date)
    if tab1 == 'total':
        line = px.line(
            df,
            x="date",
            y="total_{}".format(tab2),
            color='location',
            labels={
                "location": "Country",
                "date": "Date",
                "total_{}".format(tab2): "Total {}".format(tab2.replace('hosp','hospital').replace('_',' ').title())
            }
        )
        line.update_layout(
            title = 'Total {} over time across selected countries'.format(tab2.replace('hosp','hospital').replace('_',' ')),
            plot_bgcolor='rgb(249,249,249)', paper_bgcolor='rgb(249,249,249)'
        )
    else:
        try:
            line = px.line(
                df,
                x="date",
                y="new_{}".format(tab2),
                color='location',
                labels={
                    "location": "Country",
                    "date": "Date",
                    "new_{}".format(tab2): "New {}".format(tab2.replace('hosp','hospital').replace('_',' ').title())
                }
            )
        except:
            line = px.line(
                df,
                x="date",
                y=tab2,
                color='location',
                labels={
                    "location": "Country",
                    "date": "Date",
                    tab2: "New {}".format(tab2.replace('hosp','hospital').replace('_',' ').title())
                }
            )
        line.update_layout(
            title = 'New {} over time across selected countries'.format(tab2.replace('hosp','hospital').replace('_',' ')),
            plot_bgcolor='rgb(249,249,249)', paper_bgcolor='rgb(249,249,249)'
        )
    line.update_xaxes(showgrid=False)
    line.update_yaxes(showgrid=False)
    return line

# Update map graph
@app.callback(
    Output('main_graph', 'figure'),
    [
        Input('continent_selector', 'value'),
        Input('select_country', 'value'),
        Input('date_range_picker', 'start_date'),
        Input('date_range_picker', 'end_date')
    ]
)
def update_map1(continent, country_list, start_date, end_date):
    df = subset_data(continent, country_list, start_date, end_date)
    df = get_total(df)
    if len(df['location'].unique()) < len(country_options):
        output_map = px.choropleth(
            df, locations="iso_code",
            color = "total_cases", 
            hover_name = "location", # column to add to hover information
            color_continuous_scale = px.colors.sequential.Purples,
            title = "Map of COVID-19 Cases (selected countries)",
            labels={'iso_code':'ISO','total_cases':'Total cases','location':'Country'}
            # projection = "natural earth"
            )
    else:
        output_map = px.choropleth(
            df, locations="iso_code",
            color = "total_cases",
            hover_name = "location", # column to add to hover information
            color_continuous_scale = px.colors.sequential.Blues,
            title = "Map of COVID-19 Cases (selected countries)",
            labels={'iso_code':'ISO','total_cases':'Total cases','location':'Country'}
            # projection = "natural earth"
            )
    output_map.update_layout(
        margin={"r":0,"t":45,"l":0,"b":5},
        coloraxis_showscale=True,
        autosize=True,
        paper_bgcolor='rgb(249,249,249)',
        plot_bgcolor='rgb(249,249,249)',
        geo=dict(bgcolor= 'rgb(249,249,249)'))
    output_map.update_geos(fitbounds="locations", showcountries=True, countrycolor="Black", visible=False) #showsubunits=True, subunitcolor="Blue",
    return output_map

# Update bar1
@app.callback(
    Output('individual_graph', 'figure'),
    [
        Input('continent_selector', 'value'),
        Input('select_country', 'value'),
        Input('date_range_picker', 'start_date'),
        Input('date_range_picker', 'end_date'),
        Input('tabs-2', 'value')
    ]
)
def update_top_n_bar(continent, country_list, start_date, end_date, tab2):
    df = subset_data(continent, country_list, start_date, end_date)
    df = get_average(df, metric = tab2)
    # end_date = datetime.datetime.strptime(end_date.split('T')[0],'%Y-%m-%d').date()
    if tab2 != 'hosp_patients':
        bar = px.bar(
            df.sort_values(['new_{}'.format(tab2)], ascending = True).tail(10),
            y = 'location',
            x = 'new_{}'.format(tab2),
            title = "Top {} Countries in terms of Average daily COVID {}".format(
                len(df.sort_values(['new_{}'.format(tab2)], ascending = True).tail(10)),
                tab2
                ),
            labels = {'location':'Country','new_{}'.format(tab2):'Average daily {}'.format(tab2)},
            orientation='h',
            # color_discrete_sequence =['#119DFF']*3
            )
    else:
        bar = px.bar(
            df.sort_values([tab2], ascending = True).tail(10),
            y = 'location',
            x = tab2,
            title = "Top {} Countries in terms of Average daily COVID {}".format(
                len(df.sort_values([tab2], ascending = True).tail(10)),
                tab2.replace('hosp','hospital').replace('_',' ')
                ),
            labels = {'location':'Country','new_cases':'Average daily {}'.format(tab2.replace('hosp','hospital').replace('_',' '))},
            orientation='h'
                )
    bar.update_layout(
        plot_bgcolor='rgb(249,249,249)', paper_bgcolor='rgb(249,249,249)',
    )
    if len(df['location'].unique()) == len(country_options):
        if tab2 != 'hosp_patients':
            bar.update_layout(
                title = "Top {} Countries worldwide in terms of Average daily COVID {}".format(
                    len(df.sort_values([tab2], ascending = True).tail(10)),
                    tab2.replace('hosp','hospital').replace('_',' ')
                ),
            )
        else:
            bar.update_layout(
                title = "Top {} Countries worldwide in terms of Average daily COVID {}".format(
                    len(df.sort_values(['new_{}'.format(tab2)], ascending = True).tail(10)),
                    tab2.replace('hosp','hospital').replace('_',' ')
                ),
            )
    bar.update_traces(marker_color='#119DFF')
    bar.update_xaxes(showgrid=False)
    bar.update_yaxes(showgrid=False)
    return bar

@app.callback(
    Output('country-count','children'),
    Input('select_country','value')
)
def update_country_count(country_list):
    if country_list == None:
        return "The current selection contains 0 country."
    else:
        if len(flatten_list([country_list])) > 1:
            return "The current selection contains {} countries.".format(
                len(flatten_list([country_list]))
            )
        else:
            return "The current selection contains 1 country."
##########################################

if __name__ == '__main__':
    app.run_server()