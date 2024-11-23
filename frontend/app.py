from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
import pandas as pd
from dash.dependencies import Input, Output
import plotly.express as px
from geopy.geocoders import Nominatim  # type: ignore
import plotly.graph_objects as go
import json
import os
from datetime import datetime
from flask import request, jsonify

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    index_string='''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Road Condition Reporter</title>
        {%favicon%}
        {%css%}
        <script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyA4QiU6Fqw2zXBAeGJF2KPMM9xC0Fnug-Q&libraries=maps,marker&v=beta" defer></script>
        <script>
            let map;
            let markers = [];
            
            function getScoreColor(score) {
                if (score >= 80) return '#28a745';  // Green for very good
                if (score >= 60) return '#87cf3a';  // Light green for good
                if (score >= 40) return '#ffc107';  // Yellow for moderate
                if (score >= 20) return '#fd7e14';  // Orange for bad
                return '#dc3545';                   // Red for very bad
            }

            // Wait for the Google Maps API to load
            window.addEventListener('load', function() {
                // Initialize empty map
                map = new google.maps.Map(document.getElementById('map'), {
                    zoom: 2,
                    center: { lat: 0, lng: 0 },
                    mapId: 'DEMO_MAP_ID'
                });
            });
            
            function clearMarkers() {
                markers.forEach(marker => marker.setMap(null));
                markers = [];
            }
            
            window.dashExtensions = {
                updateMap: function(locationData) {
                    if (!map) return;
                    
                    clearMarkers();
                    const locations = JSON.parse(locationData);
                    
                    if (!locations || locations.length === 0) return;
                    
                    // Get the first location for initial center
                    const center = { 
                        lat: locations[0].lat, 
                        lng: locations[0].lng 
                    };
                    
                    map.setCenter(center);
                    
                    // Add markers for all locations
                    locations.forEach(loc => {
                        const markerColor = getScoreColor(loc.score);
                        
                        const marker = new google.maps.Marker({
                            position: { lat: loc.lat, lng: loc.lng },
                            map: map,
                            title: `Score: ${loc.score}`,
                            icon: {
                                path: google.maps.SymbolPath.CIRCLE,
                                fillColor: markerColor,
                                fillOpacity: 0.8,
                                strokeWeight: 2,
                                strokeColor: '#ffffff',
                                scale: 10
                            }
                        });
                        
                        // Add info window
                        const infowindow = new google.maps.InfoWindow({
                            content: `
                                <div style="padding: 10px;">
                                    <h3 style="margin: 0 0 10px 0;">Location Details</h3>
                                    <p><strong>Score:</strong> ${loc.score}</p>
                                    <p><strong>Time:</strong> ${loc.timestamp}</p>
                                    <p><strong>Coordinates:</strong> ${loc.lat.toFixed(4)}, ${loc.lng.toFixed(4)}</p>
                                </div>
                            `
                        });
                        
                        marker.addListener('click', () => {
                            infowindow.open(map, marker);
                        });
                        
                        markers.push(marker);
                    });
                    
                    // Fit bounds to show all markers
                    if (markers.length > 1) {
                        const bounds = new google.maps.LatLngBounds();
                        markers.forEach(marker => bounds.extend(marker.getPosition()));
                        map.fitBounds(bounds);
                    }
                }
            };
        </script>
        <style>
            .dashboard-container {
                display: flex;
                flex-direction: column;
                gap: 20px;
                padding: 20px;
                max-width: 1400px;
                margin: 0 auto;
            }
            
            .map-container {
                width: 100%;
                height: 600px;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .plots-container {
                display: flex;
                flex-direction: column;
                gap: 20px;
                width: 100%;
            }
            
            .plot {
                width: 100%;
                height: 700px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .stats-container {
                width: 100%;
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                padding: 20px;
            }
            
            .file-selector {
                width: 100%;
                margin-bottom: 20px;
                padding: 20px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            h1, h4 {
                text-align: center;
                color: #343a40;
                margin: 20px 0;
            }
            
            .table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            
            .table th, .table td {
                padding: 12px 15px;
                text-align: left;
                border: 1px solid #dee2e6;
            }
            
            .table th {
                background-color: #343a40;
                color: white;
            }
            
            .table tr:hover {
                background-color: #f8f9fa;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''
)



# Load data
def get_available_files():
    data_dir = './data'
    # Get all CSV files in the data directory
    files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    return sorted(files, reverse=True)  # Most recent first

# Global data store to hold incoming data
data_store = []

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

def prepare_data(df):
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



# Flask route to receive POST requests
@app.server.route('/data', methods=['POST'])
def receive_data():
    global data_store
    data = request.get_json()
    if data:
        # Expected data format: dictionary with keys 'latitude', 'longitude', 'timestamp', 'score'
        data_store.append(data)
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'No data received'}), 400





app.layout = html.Div([
    html.Div([
        html.H1('Road Condition Reporter'),
        html.Div([
            html.H5('Select Data File:'),
            dcc.Dropdown(
                id='file-selector',
                options=[{'label': f, 'value': f} for f in get_available_files()],
                value=get_available_files()[0] if get_available_files() else None,
            ),
            html.Div(id='file-info')
        ], className='file-selector'),
        
        html.Div(id='map', className='map-container'),
        
        dcc.Store(id='store-data'),
        dcc.Store(id='map-data'),
        
        html.Div([
            dcc.Interval(
                id='interval-component',
                interval=1000,
                n_intervals=0
            ),
            dcc.Graph(
                id='line-graph',
                className='plot'
            ),
            dcc.Graph(
                id='box-plot',
                className='plot'
            ),
            html.Div(
                id='table',
                className='stats-container'
            )
        ], className='plots-container')
        
    ], className='dashboard-container')
])

@app.callback(
    Output('map-data', 'data'),
    Input('store-data', 'data'),
)
def update_map_data(data):
    if not data:
        return '[]'
        
    df = pd.DataFrame(data)
    if df.empty:
        return '[]'
    
    # Prepare location data for the map
    locations = []
    for _, row in df.iterrows():
        locations.append({
            'lat': float(row['latitude']),
            'lng': float(row['longitude']),
            'score': float(row['score']),
            'timestamp': row['timestamp']
        })
    
    return json.dumps(locations)

# Add a clientside callback to update the map
app.clientside_callback(
    """
    function(locationData) {
        if (locationData) {
            window.dashExtensions.updateMap(locationData);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('map', 'children'),
    Input('map-data', 'data')
)

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
    Output('store-data', 'data'),
    Input('interval-component', 'n_intervals'),
    Input('file-selector', 'value')
)
def update_data(n_intervals, selected_file):
    # Load data from file if selected
    if selected_file:
        file_path = os.path.join('./data', selected_file)
        df_file = pd.read_csv(file_path)
        df_file_prepared = prepare_data(df_file)
    else:
        df_file_prepared = pd.DataFrame()

    # Prepare data from data_store
    if data_store:
        df_store = pd.DataFrame(data_store)
        df_store_prepared = prepare_data(df_store)
        # Combine file data and incoming data
        df_combined = pd.concat([df_file_prepared, df_store_prepared], ignore_index=True)
    else:
        df_combined = df_file_prepared

    return df_combined.to_dict('records')

# Adjusted callback to update file info only
@app.callback(
    Output('file-info', 'children'),
    Input('file-selector', 'value')
)
def load_file_info(selected_file):
    if not selected_file:
        return "No file selected"
    try:
        file_path = os.path.join('./data', selected_file)
        file_stats = os.stat(file_path)
        file_size = file_stats.st_size / 1024  # Convert to KB
        modified_time = datetime.fromtimestamp(file_stats.st_mtime)

        df = pd.read_csv(file_path)

        file_info = html.Div([
            html.P(f"File: {selected_file}"),
            html.P(f"Size: {file_size:.2f} KB"),
            html.P(f"Last Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}"),
            html.P(f"Number of Records: {len(df)}")
        ], style={'background': '#f8f9fa', 'padding': '10px', 'border-radius': '5px'})

        return file_info
    except Exception as e:
        return html.Div(f"Error loading file: {str(e)}", style={'color': 'red'})


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
def update_pie_chart(data):
    if not data:
        return go.Figure()
        
    df = pd.DataFrame(data)
    if df.empty:
        return go.Figure()
    
    # Define score ranges and colors
    ranges = [
        (0, 20, '#dc3545', 'Very Bad'),
        (20, 40, '#fd7e14', 'Bad'),
        (40, 60, '#ffc107', 'Moderate'),
        (60, 80, '#87cf3a', 'Good'),
        (80, 100, '#28a745', 'Very Good')
    ]
    
    # Calculate the count of scores in each range
    score_distribution = []
    labels = []
    colors = []
    for min_val, max_val, color, label in ranges:
        count = len(df[(df['score'] >= min_val) & (df['score'] < max_val)])
        if count > 0:  # Only add to pie chart if there are values in this range
            score_distribution.append(count)
            labels.append(f"{label} ({min_val}-{max_val})")
            colors.append(color)

    # Create pie chart
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=score_distribution,
        marker=dict(colors=colors),
        hovertemplate="<br>".join([
            "Category: %{label}",
            "Count: %{value}",
            "Percentage: %{percent}",
            "<extra></extra>"
        ]),
        textinfo='percent+label',
        hole=0.3  # Makes it a donut chart - remove this line or set to 0 for a regular pie chart
    )])

    fig.update_layout(
        title='Road Condition Scores Distribution',
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.0,
            xanchor='center',
            x=0.5
        ),
        margin=dict(t=50, l=20, r=20, b=20)
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

index_string = '''
<!DOCTYPE html>
<html>
    <head>
        <!-- Your existing head content -->
        <script>
            let map;
            let markers = [];

            function getScoreColor(score) {
                if (score >= 1) return '#28a745';  // Green for safe
                else return '#dc3545';              // Red for needs repair
            }

            // Your existing JavaScript code

                        let map;
            let markers = [];
            
            function getScoreColor(score) {
                if (score >= 80) return '#28a745';  // Green for very good
                if (score >= 60) return '#87cf3a';  // Light green for good
                if (score >= 40) return '#ffc107';  // Yellow for moderate
                if (score >= 20) return '#fd7e14';  // Orange for bad
                return '#dc3545';                   // Red for very bad
            }

            // Wait for the Google Maps API to load
            window.addEventListener('load', function() {
                // Initialize empty map
                map = new google.maps.Map(document.getElementById('map'), {
                    zoom: 2,
                    center: { lat: 0, lng: 0 },
                    mapId: 'DEMO_MAP_ID'
                });
            });
            
            function clearMarkers() {
                markers.forEach(marker => marker.setMap(null));
                markers = [];
            }
            
            window.dashExtensions = {
                updateMap: function(locationData) {
                    if (!map) return;
                    
                    clearMarkers();
                    const locations = JSON.parse(locationData);
                    
                    if (!locations || locations.length === 0) return;
                    
                    // Get the first location for initial center
                    const center = { 
                        lat: locations[0].lat, 
                        lng: locations[0].lng 
                    };
                    
                    map.setCenter(center);
                    
                    // Add markers for all locations
                    locations.forEach(loc => {
                        const markerColor = getScoreColor(loc.score);
                        
                        const marker = new google.maps.Marker({
                            position: { lat: loc.lat, lng: loc.lng },
                            map: map,
                            title: `Score: ${loc.score}`,
                            icon: {
                                path: google.maps.SymbolPath.CIRCLE,
                                fillColor: markerColor,
                                fillOpacity: 0.8,
                                strokeWeight: 2,
                                strokeColor: '#ffffff',
                                scale: 10
                            }
                        });
                        
                        // Add info window
                        const infowindow = new google.maps.InfoWindow({
                            content: `
                                <div style="padding: 10px;">
                                    <h3 style="margin: 0 0 10px 0;">Location Details</h3>
                                    <p><strong>Score:</strong> ${loc.score}</p>
                                    <p><strong>Time:</strong> ${loc.timestamp}</p>
                                    <p><strong>Coordinates:</strong> ${loc.lat.toFixed(4)}, ${loc.lng.toFixed(4)}</p>
                                </div>
                            `
                        });
                        
                        marker.addListener('click', () => {
                            infowindow.open(map, marker);
                        });
                        
                        markers.push(marker);
                    });
                    
                    // Fit bounds to show all markers
                    if (markers.length > 1) {
                        const bounds = new google.maps.LatLngBounds();
                        markers.forEach(marker => bounds.extend(marker.getPosition()));
                        map.fitBounds(bounds);
                    }
                }
            };
        </script>
        <style>
            .dashboard-container {
                display: flex;
                flex-direction: column;
                gap: 20px;
                padding: 20px;
                max-width: 1400px;
                margin: 0 auto;
            }
            
            .map-container {
                width: 100%;
                height: 600px;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .plots-container {
                display: flex;
                flex-direction: column;
                gap: 20px;
                width: 100%;
            }
            
            .plot {
                width: 100%;
                height: 700px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .stats-container {
                width: 100%;
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                padding: 20px;
            }
            
            .file-selector {
                width: 100%;
                margin-bottom: 20px;
                padding: 20px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            h1, h4 {
                text-align: center;
                color: #343a40;
                margin: 20px 0;
            }
            
            .table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            
            .table th, .table td {
                padding: 12px 15px;
                text-align: left;
                border: 1px solid #dee2e6;
            }
            
            .table th {
                background-color: #343a40;
                color: white;
            }
            
            .table tr:hover {
                background-color: #f8f9fa;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Update the app's index_string
app.index_string = index_string

if __name__ == '__main__':
    app.run(debug=True)