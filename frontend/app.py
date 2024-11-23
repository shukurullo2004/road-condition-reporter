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
import websockets
import asyncio
from collections import deque
import threading
from dash.exceptions import PreventUpdate
from dash import callback_context

MAX_POINTS = 100
real_time_data = deque(maxlen=MAX_POINTS)

def find_free_port(start_port=8765, max_attempts=10):
    """Find a free port starting from start_port"""
    import socket
    
    for port in range(start_port, start_port + max_attempts):
        try:
            # Try to create a socket with the port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('localhost', port))
            sock.listen(1)
            sock.close()
            return port
        except OSError:
            continue
    raise RuntimeError("Could not find a free port")

# Find an available port
WEBSOCKET_PORT = find_free_port()

# WebSocket handler
async def websocket_handler(websocket, path):
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                if 'timestamp' not in data:
                    data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                real_time_data.append(data)
                print(f"Received data: {data}")
                await websocket.send(json.dumps({"status": "received"}))
                
            except json.JSONDecodeError:
                await websocket.send(json.dumps({"error": "Invalid JSON format"}))
    except websockets.exceptions.ConnectionClosedError:
        print("Client disconnected")

async def run_websocket_server():
    try:
        async with websockets.serve(websocket_handler, "localhost", WEBSOCKET_PORT):
            print(f"WebSocket server started on port {WEBSOCKET_PORT}")
            await asyncio.Future()
    except Exception as e:
        print(f"WebSocket server error: {e}")

def start_websocket_server():
    try:
        asyncio.run(run_websocket_server())
    except Exception as e:
        print(f"Failed to start WebSocket server: {e}")

# Start WebSocket server in a daemon thread
websocket_thread = threading.Thread(target=start_websocket_server, daemon=True)
websocket_thread.start()

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

# Modify the app layout to remove the duplicate map div since it's now in the index_string
# App Layout
app.layout = html.Div([
    html.Div([
        # Header with title
        html.H1('Road Condition Reporter', 
                className='text-center mb-4', 
                style={'text-align': 'center', 'color': '#343a40', 'padding': '20px 0'}),

        html.Div([
            html.P(f"WebSocket Server Port: {WEBSOCKET_PORT}",
                  style={'text-align': 'center', 'color': '#666'}),
            html.P(f"WebSocket URL: ws://localhost:{WEBSOCKET_PORT}",
                  style={'text-align': 'center', 'color': '#666'})
        ], style={
            'background': 'white',
            'padding': '10px',
            'border-radius': '8px',
            'margin-bottom': '20px'
        }),

        # File selection section
        html.Div([
            html.H5('Select Data Source:', 
                   style={'margin-bottom': '10px', 'color': '#495057'}),
            dcc.Dropdown(
                id='file-selector',
                options=[
                    {'label': 'Real-time Data', 'value': 'real-time'},
                    *[{'label': f, 'value': f} for f in get_available_files()]
                ],
                value='real-time',  # Default to real-time
                style={'width': '100%', 'margin-bottom': '20px'}
            ),
            # File info display
            html.Div(id='file-info', style={'margin-bottom': '20px'})
        ], style={
            'background': 'white',
            'padding': '20px',
            'border-radius': '8px',
            'box-shadow': '0 2px 4px rgba(0,0,0,0.1)',
            'margin-bottom': '20px'
        }),

        # Map section
        html.Div([
            html.H5('Location Map', 
                   style={'margin-bottom': '10px', 'color': '#495057', 'padding-left': '10px'}),
            html.Div(id='map', className='map-container')
        ], style={
            'background': 'white',
            'border-radius': '8px',
            'box-shadow': '0 2px 4px rgba(0,0,0,0.1)',
            'margin-bottom': '20px',
            'padding': '20px'
        }),

        # Stores and Interval
        dcc.Store(id='store-data'),
        dcc.Store(id='map-data'),
        dcc.Interval(
            id='interval-component',
            interval=1000,  # 1 second
            n_intervals=0
        ),

        # Visualizations Container
        html.Div([
            # Line Graph
            html.Div([
                html.H5('Road Condition Trend', 
                       style={'margin-bottom': '10px', 'color': '#495057', 'padding-left': '10px'}),
                dcc.Graph(
                    id='line-graph',
                    style={'height': '400px'}
                )
            ], style={
                'background': 'white',
                'border-radius': '8px',
                'box-shadow': '0 2px 4px rgba(0,0,0,0.1)',
                'margin-bottom': '20px',
                'padding': '20px'
            }),

            # Distribution Chart
            html.Div([
                html.H5('Score Distribution', 
                       style={'margin-bottom': '10px', 'color': '#495057', 'padding-left': '10px'}),
                dcc.Graph(
                    id='pie-chart',
                    style={'height': '400px'}
                )
            ], style={
                'background': 'white',
                'border-radius': '8px',
                'box-shadow': '0 2px 4px rgba(0,0,0,0.1)',
                'margin-bottom': '20px',
                'padding': '20px'
            }),

            # Statistics Table
            html.Div([
                html.H5('Statistics Summary', 
                       style={'margin-bottom': '10px', 'color': '#495057', 'padding-left': '10px'}),
                html.Div(
                    id='table',
                    style={'padding': '10px'}
                )
            ], style={
                'background': 'white',
                'border-radius': '8px',
                'box-shadow': '0 2px 4px rgba(0,0,0,0.1)',
                'margin-bottom': '20px',
                'padding': '10px'
            })

        ], className='plots-container')

    ], style={
        'width': '90%',
        'max-width': '1400px',
        'margin': '0 auto',
        'padding': '20px',
        'background': '#f8f9fa'
    })
], style={
    'min-height': '100vh',
    'background': '#f8f9fa',
    'padding': '20px 0'
})

@app.callback(
    [Output('store-data', 'data'),
     Output('map-data', 'data'),
     Output('file-info', 'children')],
    [Input('file-selector', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_all_data(selected_source, n_intervals):
    # Get the ID of the component that triggered the callback
    ctx = callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'file-selector'

    if trigger_id == 'interval-component' and selected_source == 'real-time':
        if not real_time_data:
            raise PreventUpdate
        
        # Handle real-time data
        df = pd.DataFrame(list(real_time_data))
        
        # Prepare map data
        locations = []
        for _, row in df.iterrows():
            locations.append({
                'lat': float(row['latitude']),
                'lng': float(row['longitude']),
                'score': float(row['score']),
                'timestamp': row['timestamp']
            })
        
        info = html.Div([
            html.P("Real-time Data Stream"),
            html.P(f"Number of Points: {len(df)}"),
            html.P(f"Last Update: {df['timestamp'].iloc[-1] if not df.empty else 'No data'}")
        ], style={'background': '#f8f9fa', 'padding': '10px', 'border-radius': '5px'})
        
        return df.to_dict('records'), json.dumps(locations), info
    
    elif trigger_id == 'file-selector' and selected_source != 'real-time':
        try:
            # Handle CSV file data
            file_path = os.path.join('./data', selected_source)
            df = pd.read_csv(file_path)
            prepared_df = prepare_data(df)
            
            # Prepare map data
            locations = []
            for _, row in prepared_df.iterrows():
                locations.append({
                    'lat': float(row['latitude']),
                    'lng': float(row['longitude']),
                    'score': float(row['score']),
                    'timestamp': row['timestamp']
                })
            
            file_stats = os.stat(file_path)
            file_size = file_stats.st_size / 1024
            modified_time = datetime.fromtimestamp(file_stats.st_mtime)
            
            file_info = html.Div([
                html.P(f"File: {selected_source}"),
                html.P(f"Size: {file_size:.2f} KB"),
                html.P(f"Last Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}"),
                html.P(f"Number of Records: {len(df)}")
            ], style={'background': '#f8f9fa', 'padding': '10px', 'border-radius': '5px'})
            
            return prepared_df.to_dict('records'), json.dumps(locations), file_info
            
        except Exception as e:
            error_info = html.Div(f"Error loading file: {str(e)}", 
                                style={'color': 'red', 'padding': '10px'})
            return None, '[]', error_info
    
    # If no relevant trigger or other conditions
    raise PreventUpdate


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
    Output('line-graph', 'figure'),
    [Input('store-data', 'data'),
     Input('file-selector', 'value')]
)
def update_graph(data, selected_source):
    if not data:
        return go.Figure()
        
    df = pd.DataFrame(data)
    if df.empty:
        return go.Figure()
    
    if selected_source == 'real-time':
        # Real-time data visualization
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['score'],
            mode='lines+markers',
            name='Score',
            line=dict(color='#17a2b8'),
            marker=dict(
                size=8,
                color=df['score'].apply(lambda x: {
                    x >= 80: '#28a745',
                    60 <= x < 80: '#87cf3a',
                    40 <= x < 60: '#ffc107',
                    20 <= x < 40: '#fd7e14'
                }.get(True, '#dc3545'))
            )
        ))
        
        fig.update_layout(
            title='Real-time Road Condition Scores',
            xaxis_title='Time',
            yaxis_title='Score',
            yaxis=dict(range=[0, 100]),
            hovermode='x unified'
        )
    else:
        # CSV data visualization
        fig = px.line(
            df,
            x='location_name',
            y='score',
            markers=True,
            custom_data=['latitude', 'longitude', 'timestamp', 'point_number']
        )
        
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
    Output('pie-chart', 'figure'),
    [Input('store-data', 'data'),
     Input('file-selector', 'value')]
)
def update_distribution_chart(data, selected_source):
    if not data:
        return go.Figure()
        
    df = pd.DataFrame(data)
    if df.empty:
        return go.Figure()
    
    # Define ranges and colors (same for both real-time and file data)
    ranges = [
        (0, 20, '#dc3545', 'Very Bad'),
        (20, 40, '#fd7e14', 'Bad'),
        (40, 60, '#ffc107', 'Moderate'),
        (60, 80, '#87cf3a', 'Good'),
        (80, 100, '#28a745', 'Very Good')
    ]
    
    # Calculate distribution
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
        hole=0.3,  # Makes it a donut chart
        hovertemplate="<br>".join([
            "Category: %{label}",
            "Count: %{value}",
            "Percentage: %{percent}",
            "<extra></extra>"
        ])
    )])

    # Update layout based on data source
    title = 'Real-time Score Distribution' if selected_source == 'real-time' else 'Historical Score Distribution'
    fig.update_layout(
        title=title,
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5
        ),
        annotations=[
            dict(
                text=f'Total Points: {len(df)}',
                x=0.5,
                y=-0.1,
                showarrow=False,
                font=dict(size=12)
            )
        ]
    )

    return fig

@app.callback(
    Output('table', 'children'),
    [Input('store-data', 'data'),
     Input('file-selector', 'value')]
)
def update_table(data, selected_source):
    if not data:
        return html.Div("Waiting for data...")
        
    df = pd.DataFrame(data)
    if df.empty:
        return html.Div("No data available")
    
    if selected_source == 'real-time':
        # Real-time statistics
        stats = {
            'Latest Score': df['score'].iloc[-1],
            'Average Score': df['score'].mean(),
            'Minimum Score': df['score'].min(),
            'Maximum Score': df['score'].max(),
            'Points in Last 5 Minutes': len(df[df['timestamp'] >= (pd.Timestamp.now() - pd.Timedelta(minutes=5))]),
            'Total Points': len(df)
        }
    else:
        # CSV file statistics
        stats = {
            'Minimum Score': df['score'].min(),
            'Maximum Score': df['score'].max(),
            'Mean Score': df['score'].mean(),
            'Standard Deviation': df['score'].std(),
            'Median Score': df['score'].median(),
            'Total Locations': len(df)
        }

    rows = []
    for stat, value in stats.items():
        row = html.Tr([
            html.Td(stat, style={'padding': '10px', 'font-weight': 'bold'}),
            html.Td(
                f'{value:.2f}' if isinstance(value, float) else str(value), 
                style={'padding': '10px', 'text-align': 'right'}
            )
        ])
        rows.append(row)

    return html.Div([
        html.H4(
            'Real-time Statistics' if selected_source == 'real-time' else 'Historical Statistics',
            style={'text-align': 'center', 'margin-bottom': '20px'}
        ),
        dbc.Table(
            [html.Tbody(rows)],
            bordered=True,
            hover=True,
            style={'margin': 'auto'}
        )
    ])

if __name__ == '__main__':
    app.run(debug=True)