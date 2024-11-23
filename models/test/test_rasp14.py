from picamera2 import Picamera2
from ultralytics import YOLO
import cv2
import numpy as np
import os

# Load the YOLO model
model = YOLO("weights/best.pt")  # Path to your trained YOLOv8 weights

# Initialize PiCamera2
picam = Picamera2()
camera_config = picam.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
picam.configure(camera_config)
picam.start()

# Ensure frames directory exists for saving processed frames
os.makedirs("frames", exist_ok=True)

frame_num = 0  # Frame counter
while True:
    # Capture frame from PiCamera2
    frame = picam.capture_array()

    # Get frame area
    area = frame.shape[0] * frame.shape[1]
    frame_num += 1

    # Run inference on the frame
    results = model(frame, conf=0.25, iou=0.5)  # Adjust confidence and IoU thresholds as needed

    # Extract bounding boxes and class information
    boxes_area = 0
    for result in results:
        boxes = result.boxes  # Use the boxes property
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())  # Bounding box coordinates
            w = x2 - x1
            h = y2 - y1
            boxes_area += w * h
            conf = box.conf[0].item()  # Confidence score
            cls = int(box.cls[0].item())  # Class ID

            # Draw the bounding box if confidence is above the threshold
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"Class: {cls}, Conf: {conf:.2f}",
                        (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Calculate the score for the frame
    score = 1 - (boxes_area / area)
    cv2.putText(frame, f"Score: {score:.2f}",
                (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)

    # Save processed frame to disk
    cv2.imwrite(f'frames/frame_{frame_num}.jpg', frame)

    # Display the frame (optional for debugging)
    cv2.imshow("YOLOv8 Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):  # Exit when 'q' is pressed
        break

# Release resources
picam.close()
cv2.destroyAllWindows()
