from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
import pandas as pd
from dash.dependencies import Input, Output
import plotly.express as px
from geopy.geocoders import Nominatim
import plotly.graph_objects as go
import json
import os

app = Dash(__name__)

# Load data
data = pd.read_csv('./data/data.csv')

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

# Rest of your code remains the same...
# Prepare initial data
prepared_data = prepare_data(data)

app.layout = html.Div([
    # Outer container to center everything
    html.Div([
        html.H1('Road Condition Reporter', className='text-center mb-4', style={'text-align': 'center'}),
        dcc.Store(id='store-data', data=prepared_data.to_dict('records')),
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
                    style={'width': '100%', 'height': '700px'}  # Increased height for rotated labels
                ),
                dcc.Graph(
                    id='box-plot',
                    style={'width': '100%', 'height': '700px'}  # Increased height for rotated labels
                ),
                html.Div(
                    id='table',
                    style={'width': '100%', 'maxWidth': '1000px', 'margin': '0 auto'}
                )
            ]
        )    
    ], style={
        'width': '90%',  # Increased width for better label visibility
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
    Output('line-graph', 'figure'),
    Input('store-data', 'data')
)
def update_graph(data):
    df = pd.DataFrame(data)
    
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
        # Configure x-axis for rotated labels
        xaxis=dict(
            tickangle=45,  # Rotate labels 45 degrees
            tickmode='array',
            ticktext=df['location_name'],
            tickvals=df['location_name'],
            tickfont=dict(size=10),  # Smaller font size
        ),
        yaxis=dict(
            gridcolor='LightGrey',
            showgrid=True,
            range=[0, 100]
        ),
        # Add more margin at bottom for rotated labels
        margin=dict(b=150)
    )
    
    # Customize hover template
    fig.update_traces(
        hovertemplate="<br>".join([
            "<b>Location Point %{customdata[3]}</b>",
            "%{x}",  # Location name
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
    df = pd.DataFrame(data)
    
    # Create separate violin plots for each score range
    fig = go.Figure()

    # Define the ranges and their colors
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
        
        if len(subset) > 0:  # Only add if there are points in this range
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
                    "<b>%{customdata[4]}</b>",
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
        showlegend=True,  # Show legend for different categories outside the plot
        legend=dict(
            title='Score Range',
            orientation='h',  # Horizontal legend
            y=0.93,  # Position it just above the plot
            x=0.3,
            xanchor='center',
            yanchor='bottom'
        ),
        violinmode='overlay',  # Overlay the violin plots
        margin=dict(r=50, t=50)
    )

    return fig

@app.callback(
    Output('table', 'children'),
    Input('store-data', 'data')
)
def update_table(data):
    df = pd.DataFrame(data)
    
    # Calculate statistics
    stats = {
        'Minimum Score': df['score'].min(),
        'Maximum Score': df['score'].max(),
        'Mean Score': df['score'].mean(),
        'Standard Deviation': df['score'].std(),
        'Median Score': df['score'].median()
    }

    # Create table headers with styling
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

    # Create table rows with styling
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

    # Create table with bootstrap styling
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
    
    # Wrap table in a container with title
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