from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
import pandas as pd
from dash.dependencies import Input, Output
import plotly.express as px
from geopy.geocoders import Nominatim # type: ignore
import plotly.graph_objects as go
import json
import os
from datetime import datetime

app = Dash(__name__)

# Load data
def get_available_files():
    data_dir = './data'
    # Get all CSV files in the data directory
    files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    return sorted(files, reverse=True)  # Most recent first


# Cache file path
CACHE_FILE = 'location_cache.json'

def load_cache():
    """Load cached location names"""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    """Save location names to cache"""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def get_location_name(lat, lon, cache):
    """Get location name from coordinates or cache"""
    cache_key = f"{lat:.4f},{lon:.4f}"
    
    # Return cached result if available
    if cache_key in cache:
        return cache[cache_key]
    
    # If not in cache, fetch from API
    geolocator = Nominatim(user_agent="road_condition_reporter")
    try:
        location = geolocator.reverse((lat, lon), language='en')
        if location and location.raw.get('address'):
            addr = location.raw['address']
            street = addr.get('road', addr.get('highway', ''))
            city = addr.get('city', addr.get('town', addr.get('village', '')))
            
            result = f"{street}, {city}" if street and city else f"({lat:.2f}, {lon:.2f})"
            cache[cache_key] = result
            return result
    except:
        result = f"({lat:.2f}, {lon:.2f})"
        cache[cache_key] = result
        return result

def prepare_data(data):
    df = pd.DataFrame(data)
    df['point_number'] = range(1, len(df) + 1)
    
    # Load cached locations
    cache = load_cache()
    print("Fetching location names...")
    
    # Get location names using cache
    df['location_name'] = df.apply(
        lambda row: get_location_name(row['latitude'], row['longitude'], cache), 
        axis=1
    )
    
    # Save updated cache
    save_cache(cache)
    return df

app.layout = html.Div([
    # Outer container to center everything
    html.Div([
        html.H1('Road Condition Reporter', className='text-center mb-4', style={'text-align': 'center'}),
        # File selection section
        html.Div([
            html.H5('Select Data File:', 
                   style={'margin-bottom': '10px'}),
            dcc.Dropdown(
                id='file-selector',
                options=[{'label': f, 'value': f} for f in get_available_files()],
                value=get_available_files()[0] if get_available_files() else None,
                style={'width': '100%', 'margin-bottom': '20px'}
            ),
            # File info display
            html.Div(id='file-info', style={'margin-bottom': '20px'})
        ], style={'margin-bottom': '30px'}),
        dcc.Store(id='store-data'),
        html.Div(
            style={
                'display': 'flex',
                'justifyContent': 'center',
                'alignItems': 'center',
                'flexDirection': 'column',
                'width': '100%'
            },
            children=[
                dcc.Graph(
                    id='line-graph',
                    style={'width': '100%', 'height': '700px'}
                ),
                dcc.Graph(
                    id='box-plot',
                    style={'width': '100%', 'height': '700px'}
                ),
                html.Div(
                    id='table',
                    style={'width': '100%', 'maxWidth': '1000px', 'margin': '0 auto'}
                )
            ]
        )    
    ], style={
        'width': '90%',
        'maxWidth': '1400px',
        'margin': '0 auto',
        'padding': '20px'
    })
], style={
    'display': 'flex',
    'justifyContent': 'center',
    'alignItems': 'center',
    'width': '100%',
})

@app.callback(
    [Output('store-data', 'data'),
     Output('file-info', 'children')],
    Input('file-selector', 'value')
)
def load_and_prepare_data(selected_file):
    if not selected_file:
        return None, "No file selected"
    
    try:
        # Load the data
        file_path = os.path.join('./data', selected_file)
        df = pd.read_csv(file_path)
        
        # Prepare the data
        prepared_df = prepare_data(df)
        
        # Get file information
        file_stats = os.stat(file_path)
        file_size = file_stats.st_size / 1024  # Convert to KB
        modified_time = datetime.fromtimestamp(file_stats.st_mtime)
        
        file_info = html.Div([
            html.P(f"File: {selected_file}"),
            html.P(f"Size: {file_size:.2f} KB"),
            html.P(f"Last Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}"),
            html.P(f"Number of Records: {len(df)}")
        ], style={'background': '#f8f9fa', 'padding': '10px', 'border-radius': '5px'})
        
        return prepared_df.to_dict('records'), file_info
        
    except Exception as e:
        return None, html.Div(f"Error loading file: {str(e)}", 
                            style={'color': 'red'})

@app.callback(
    Output('line-graph', 'figure'),
    Input('store-data', 'data')
)
def update_graph(data):
    if not data:
        return go.Figure()
        
    df = pd.DataFrame(data)
    if df.empty:
        return go.Figure()
    
    # Create the figure
    fig = px.line(
        df,
        x='location_name',
        y='score',
        markers=True,
        custom_data=['latitude', 'longitude', 'timestamp', 'point_number']
    )
    
    # Update layout
    fig.update_layout(
        title='Road Condition Scores by Location',
        xaxis_title='Location',
        yaxis_title='Condition Score',
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
        ),
        xaxis=dict(
            tickangle=45,
            tickmode='array',
            ticktext=df['location_name'],
            tickvals=df['location_name'],
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            gridcolor='LightGrey',
            showgrid=True,
            range=[0, 100]
        ),
        margin=dict(b=150)
    )
    
    # Customize hover template
    fig.update_traces(
        hovertemplate="<br>".join([
            "<b>Location Point %{customdata[3]}</b>",
            "%{x}",
            "Score: %{y}",
            "Coordinates: (%{customdata[0]:.2f}, %{customdata[1]:.2f})",
            "Time: %{customdata[2]}",
            "<extra></extra>"
        ])
    )
    
    return fig

@app.callback(
    Output('box-plot', 'figure'),
    Input('store-data', 'data')
)
def update_box_plot(data):
    if not data:
        return go.Figure()
        
    df = pd.DataFrame(data)
    if df.empty:
        return go.Figure()
    
    # Create separate violin plots for each score range
    fig = go.Figure()

    ranges = [
        (0, 20, 'red', 'Very Bad'),
        (20, 40, 'orange', 'Bad'),
        (40, 60, 'yellow', 'Moderate'),
        (60, 80, 'lightgreen', 'Good'),
        (80, 100, 'green', 'Very Good')
    ]

    for min_val, max_val, color, label in ranges:
        mask = (df['score'] >= min_val) & (df['score'] < max_val)
        subset = df[mask]
        
        if len(subset) > 0:
            fig.add_trace(go.Violin(
                y=subset['score'],
                name=label,
                box_visible=True,
                meanline_visible=True,
                points='all',
                line_color=color,
                fillcolor=color,
                opacity=0.6,
                marker=dict(
                    size=8,
                    color=color
                ),
                customdata=subset[['location_name', 'latitude', 'longitude', 'timestamp', 'point_number']].values,
                hovertemplate="<br>".join([
                    "<b>Point %{customdata[4]}</b>",
                    "Location: %{customdata[0]}",
                    "Score: %{y}",
                    "Coordinates: (%{customdata[1]:.2f}, %{customdata[2]:.2f})",
                    "Time: %{customdata[3]}",
                    "<extra></extra>"
                ])
            ))

    fig.update_layout(
        title='Road Condition Scores Distribution',
        yaxis_title='Condition Score',
        yaxis=dict(
            gridcolor='LightGrey',
            showgrid=True,
            range=[0, 100]
        ),
        hovermode='closest',
        hoverlabel=dict(
            bgcolor="white",
            font_size=12
        ),
        showlegend=True,
        legend=dict(
            title='Score Range',
            orientation='h',
            y=0.93,
            x=0.3,
            xanchor='center',
            yanchor='bottom'
        ),
        violinmode='overlay',
        margin=dict(r=50, t=50)
    )

    return fig

@app.callback(
    Output('table', 'children'),
    Input('store-data', 'data')
)
def update_table(data):
    if not data:
        return html.Div("No data available")
        
    df = pd.DataFrame(data)
    if df.empty:
        return html.Div("No data available")
    
    stats = {
        'Minimum Score': df['score'].min(),
        'Maximum Score': df['score'].max(),
        'Mean Score': df['score'].mean(),
        'Standard Deviation': df['score'].std(),
        'Median Score': df['score'].median()
    }

    headers = html.Thead(
        html.Tr([
            html.Th('Statistic', style={
                'background-color': '#343a40',
                'color': 'white',
                'padding': '12px 15px',
                'text-align': 'left',
                'font-weight': 'bold',
                'border': '1px solid #454d55'
            }),
            html.Th('Value', style={
                'background-color': '#343a40',
                'color': 'white',
                'padding': '12px 15px',
                'text-align': 'center',
                'font-weight': 'bold',
                'border': '1px solid #454d55'
            })
        ])
    )

    rows = []
    for stat, value in stats.items():
        row = html.Tr([
            html.Td(stat, style={
                'padding': '10px 15px',
                'border': '1px solid #dee2e6',
                'font-weight': '500'
            }),
            html.Td(
                f'{value:.2f}', 
                style={
                    'padding': '10px 15px',
                    'border': '1px solid #dee2e6',
                    'text-align': 'center'
                }
            )
        ])
        rows.append(row)

    table = dbc.Table(
        [headers, html.Tbody(rows)],
        bordered=True,
        hover=True,
        responsive=True,
        style={
            'margin': '20px auto',
            'width': '80%',
            'max-width': '600px',
            'box-shadow': '0 2px 4px rgba(0,0,0,0.1)',
            'border-radius': '5px',
            'overflow': 'hidden',
            'background-color': 'white'
        }
    )
    
    return html.Div([
        html.H4(
            'Road Condition Score Statistics',
            style={
                'text-align': 'center',
                'margin': '20px 0 10px 0',
                'color': '#343a40',
                'font-weight': 'bold'
            }
        ),
        table
    ])

if __name__ == '__main__':
    app.run(debug=True)