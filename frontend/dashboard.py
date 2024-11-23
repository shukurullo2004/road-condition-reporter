from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
import pandas as pd
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
import os
import json
from datetime import datetime
from flask import request, jsonify

# Initialize the app
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
    window.addEventListener('load', function () {
        map = new google.maps.Map(document.getElementById('map'), {
            zoom: 2,
            center: { lat: 0, lng: 0 },
        });
    });

    function clearMarkers() {
        markers.forEach(marker => marker.setMap(null));
        markers = [];
    }

    window.dashExtensions = {
        updateMap: function (locationData) {
            if (!map) return;

            clearMarkers();
            const locations = JSON.parse(locationData);

            if (!locations || locations.length === 0) return;

            // Add markers for all locations
            locations.forEach(loc => {
                const markerColor = getScoreColor(loc.score);
                const lat = parseFloat(loc.latitude);  // Changed from loc.lat
                const lng = parseFloat(loc.longitude); // Changed from loc.lng

                const marker = new google.maps.Marker({
                    position: { lat: lat, lng: lng },
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

                // Add an info window for dynamic labels
                const infowindow = new google.maps.InfoWindow({
                    content: `
                        <div style="padding: 10px;">
                            <h3 style="margin: 0 0 10px 0;">Location Details</h3>
                            <p><strong>Score:</strong> ${loc.score}</p>
                            <p><strong>Time:</strong> ${loc.timestamp}</p>
                            <p><strong>Coordinates:</strong> ${lat.toFixed(4)}, ${lng.toFixed(4)}</p>
                        </div>
                    `
                });

                marker.addListener('click', () => {
                    infowindow.open(map, marker);
                });

                markers.push(marker);
            });

            // Center the map to the latest point
            if (locations.length > 0) {
                const lastLocation = locations[locations.length - 1];
                map.setCenter({ 
                    lat: parseFloat(lastLocation.latitude), 
                    lng: parseFloat(lastLocation.longitude) 
                });
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
            }
            .plot {
                width: 100%;
                height: 500px;
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

@app.callback(
    Output('store-data', 'data'),
    Input('interval-component', 'n_intervals')
)
def update_from_data_store(n_intervals):
    if data_store:
        return json.dumps(data_store)  # Changed to return JSON string directly
    return '[]'

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
    Input('store-data', 'data')
)

# Global variables
data_store = []  # Store incoming data

# Layout
app.layout = html.Div([
    html.Div([
        html.H1('Road Condition Reporter'),
        html.Div(id='map', className='map-container'),
        dcc.Interval(
            id='interval-component',
            interval=1000,  # Update every 1 second
            n_intervals=0
        ),
        dcc.Graph(id='line-graph', className='plot'),
        dcc.Graph(id='box-plot', className='plot'),
        dcc.Store(id='store-data')  # Store for real-time data
    ], className='dashboard-container')
])

# Flask route to receive real-time POST requests
@app.server.route('/add_point', methods=['POST'])
def add_point():
    global data_store
    data = request.get_json()
    if data:
        try:
            required_fields = {'latitude', 'longitude', 'timestamp', 'score'}
            if not required_fields.issubset(data.keys()):
                return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
            
            # Store the data as-is without converting to DataFrame
            data_store.append({
                'latitude': float(data['latitude']),
                'longitude': float(data['longitude']),
                'timestamp': data['timestamp'],
                'score': float(data['score'])
            })
            
            # Keep only the last 100 points to prevent memory issues
            if len(data_store) > 100:
                data_store.pop(0)
                
            return jsonify({'status': 'success', 'message': 'Data received'}), 200
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 400
    else:
        return jsonify({'status': 'error', 'message': 'Invalid JSON payload'}), 400

# Line graph callback
@app.callback(
    Output('line-graph', 'figure'),
    Input('store-data', 'data')
)
def update_line_graph(data):
    if not data:
        return go.Figure()
    
    df = pd.DataFrame(json.loads(data))  # Parse JSON string
    fig = px.line(
        df,
        x='timestamp',
        y='score',
        markers=True,
        title='Road Condition Scores Over Time'
    )
    fig.update_layout(xaxis_title='Timestamp', yaxis_title='Score')
    return fig

# Pie chart callback
@app.callback(
    Output('box-plot', 'figure'),
    Input('store-data', 'data')
)
def update_pie_chart(data):
    if not data:
        return go.Figure()
    
    df = pd.DataFrame(json.loads(data))  # Parse JSON string
    ranges = [
        (0, 20, '#dc3545', 'Very Bad'),
        (20, 40, '#fd7e14', 'Bad'),
        (40, 70, '#ffc107', 'Moderate'),
        (70, 80, '#87cf3a', 'Good'),
        (80, 100, '#28a745', 'Very Good')
    ]
    
    score_distribution = []
    labels = []
    colors = []
    for min_val, max_val, color, label in ranges:
        count = len(df[(df['score'] >= min_val) & (df['score'] < max_val)])
        if count > 0:
            score_distribution.append(count)
            labels.append(label)
            colors.append(color)

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=score_distribution,
        marker=dict(colors=colors),
        textinfo='percent+label'
    )])
    fig.update_layout(title='Road Condition Score Distribution')
    return fig

# Run the app
if __name__ == '__main__':
    app.run(debug=True)