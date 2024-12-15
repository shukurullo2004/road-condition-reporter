To send WebSocket messages from a TurtleBot or any other ROS-based device, you can use either Python or ROS nodes. Here are both approaches:

1. Using Python with `roslibpy` (Recommended for TurtleBot):
```python
import websockets
import asyncio
import json
import rospy
from geometry_msgs.msg import Point
from std_msgs.msg import Float32

async def send_to_websocket(websocket, latitude, longitude, score):
    try:
        data = {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "score": float(score)
        }
        await websocket.send(json.dumps(data))
        response = await websocket.recv()
        rospy.loginfo(f"Data sent: {data}")
        rospy.loginfo(f"Response: {response}")
    except Exception as e:
        rospy.logerr(f"Error sending data: {e}")

class WebSocketROSBridge:
    def __init__(self):
        rospy.init_node('websocket_bridge', anonymous=True)
        
        # Get parameters
        self.websocket_url = rospy.get_param('~websocket_url', 'ws://192.168.0.100:8766')  # Replace with your PC's IP
        self.location_topic = rospy.get_param('~location_topic', '/gps/location')
        self.score_topic = rospy.get_param('~score_topic', '/road_condition/score')
        
        # Initialize variables
        self.latest_location = None
        self.latest_score = None
        
        # Create subscribers
        rospy.Subscriber(self.location_topic, Point, self.location_callback)
        rospy.Subscriber(self.score_topic, Float32, self.score_callback)
        
        # Start WebSocket connection
        self.start_websocket()

    def location_callback(self, msg):
        self.latest_location = (msg.x, msg.y)  # Assuming x is latitude and y is longitude
        self.try_send_data()

    def score_callback(self, msg):
        self.latest_score = msg.data
        self.try_send_data()

    def try_send_data(self):
        if self.latest_location and self.latest_score is not None:
            asyncio.run(self.send_data())

    async def send_data(self):
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                await send_to_websocket(
                    websocket,
                    self.latest_location[0],
                    self.latest_location[1],
                    self.latest_score
                )
        except Exception as e:
            rospy.logerr(f"WebSocket connection error: {e}")

    def start_websocket(self):
        rospy.loginfo(f"Starting WebSocket bridge to {self.websocket_url}")
        while not rospy.is_shutdown():
            rospy.sleep(0.1)  # Adjust rate as needed

if __name__ == '__main__':
    try:
        bridge = WebSocketROSBridge()
    except rospy.ROSInterruptException:
        pass
```

2. Create a ROS launch file (`websocket_bridge.launch`):
```xml
<launch>
  <node name="websocket_bridge" pkg="your_package_name" type="websocket_bridge.py" output="screen">
    <param name="websocket_url" value="ws://192.168.0.100:8766" />
    <param name="location_topic" value="/gps/location" />
    <param name="score_topic" value="/road_condition/score" />
  </node>
</launch>
```

3. To run on the TurtleBot:
```bash
# First, make sure both devices are on the same network
# On your PC (where Dash is running), get the IP address:
ip addr show

# On TurtleBot, modify the websocket_url in the launch file with your PC's IP
# Then run:
roslaunch your_package_name websocket_bridge.launch
```

4. For testing without ROS, you can use this simplified version:
```python
import websockets
import asyncio
import json
import time

async def send_data():
    uri = "ws://192.168.0.100:8766"  # Replace with your PC's IP
    try:
        async with websockets.connect(uri) as websocket:
            while True:
                data = {
                    "latitude": 37.452590,
                    "longitude": 126.657975,
                    "score": 85
                }
                await websocket.send(json.dumps(data))
                response = await websocket.recv()
                print(f"Sent data: {data}")
                print(f"Received: {response}")
                time.sleep(1)
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(send_data())
```

Key points to remember:
1. Replace `192.168.0.100` with your PC's actual IP address
2. Make sure both devices are on the same network
3. Ensure the firewall allows connections on port 8766
4. Adjust the data sending rate as needed
5. Handle network interruptions gracefully

To set up on TurtleBot:
1. Copy the script to the TurtleBot
2. Install required packages:
```bash
pip install websockets asyncio
```
3. Make the script executable:
```bash
chmod +x websocket_bridge.py
```
4. Run the script:
```bash
python websocket_bridge.py
```

Would you like me to provide more details about any part of this setup?