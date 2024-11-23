from ultralytics import YOLO
import cv2
import requests
from datetime import datetime
import numpy as np
from datetime import timedelta

DASHBOARD_URL = "http://127.0.0.1:8050/add_point"

# Mock GPS locations and timestamps
start_lat, start_lon = 37.453277, 126.657042
end_lat, end_lon = 37.453638, 126.658605
start_time = datetime(2024, 11, 23, 16, 30, 3)
end_time = datetime(2024, 11, 23, 16, 31, 4)
total_duration = (end_time - start_time).total_seconds()
fps = 30
num_frames = int(total_duration * fps)

latitudes = np.linspace(start_lat, end_lat, num_frames)
longitudes = np.linspace(start_lon, end_lon, num_frames)
timestamps = [start_time + timedelta(seconds=i / fps) for i in range(num_frames)]

def get_mock_location(frame_index):
    return latitudes[frame_index], longitudes[frame_index], timestamps[frame_index].strftime("%Y-%m-%d %H:%M:%S")

def process_video(video_path, output_dir="output.avi", conf_thresh=0.25, iou_thresh=0.5, score_thresh=0.7, save=False):
    """
    Process a video file using a YOLO model to perform object detection and save results.

    Parameters:
        video_path (str): Path to the input video file.
        output_dir (str): Directory to save processed video.
        conf_thresh (float): Confidence threshold for detection.
        iou_thresh (float): IoU threshold for detection.
        score_thresh (float): Score threshold to trigger warnings.
        save (bool): Whether to save the processed video.
    """
    # Load the YOLO model
    model = YOLO("backend/raspberry_pi/weights/best.pt")
    
    # Initialize video capture
    cap = cv2.VideoCapture(video_path)
    
    # Save the video
    fps = cap.get(cv2.CAP_PROP_FPS)
    if save:
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))                                                 
        out = cv2.VideoWriter(output_dir, fourcc, fps, (width, height))
    
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return
    
    frame_num = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            print("End of video or failed to capture frame.")
            break
        
        # Get mock location and timestamp
        lat, lng, timestamp = get_mock_location(frame_num)
        frame_num += 1

        # Run inference on the frame
        results = model(frame, conf=conf_thresh, iou=iou_thresh)
        
        # Initialize total boxes area
        boxes_area = 0
        area = frame.shape[0] * frame.shape[1]
        
        for result in results:
            boxes = result.boxes  # Use the boxes property
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())  # Bounding box coordinates
                w = x2 - x1
                h = y2 - y1
                boxes_area += w * h
                conf = box.conf[0].item()  # Confidence score
                cls = int(box.cls[0].item())  # Class ID

                # Draw the bounding box and label
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"Class: {cls}, Conf: {conf:.2f}",
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Calculate and display the score
        score = 1 - (boxes_area / area)
        if score < score_thresh:
            cv2.putText(frame, "Warning: Low Score Detected. Road needs to be fixed",
                        (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 2)
        cv2.putText(frame, f"Score: {score:.2f}",
                    (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)
        cv2.putText(frame, f"Latitude: {lat}",
                    (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Longitude: {lng}",
                    (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Timestamp: {timestamp}",
                    (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Save the processed frame
        if save:
            out.write(frame)
        
        # Make payload and send to dashboard
        payload = {
            "longitude": lng,
            "latitude": lat,
            "timestamp": timestamp,
            "score": score*100
        }
        
        requests.post(DASHBOARD_URL, json=payload)
        
        cv2.imshow("frame", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release resources
    cap.release()
    if save:
        out.release()
    cv2.destroyAllWindows()
    print(f"Processed {frame_num} frames. Saved results in {output_dir}.")
