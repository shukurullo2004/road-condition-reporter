import ultralytics
from ultralytics import YOLO
import cv2

# Load the YOLO model
model = YOLO("weights/best.pt") # Load the best model from drive

# Initialize webcam capture
cap = cv2.VideoCapture('videos/sample.mp4') # video path
frame_num = 0
while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture frame")
        break
    
    # get image shape
    area = frame.shape[0] * frame.shape[1]
    frame_num += 1
    # Run inference on the frame
    results = model(frame, conf=0.25, iou=0.5)  # Run the model

    # Extract bounding boxes and class information
    boxes_area = 0
    for result in results:
        boxes = result.boxes  # Use the boxes property
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())  # Bounding box coordinates
            w = x2 - x1
            h = y2 - y1
            boxes_area += w*h
            conf = box.conf[0].item()  # Confidence score
            cls = int(box.cls[0].item())  # Class ID

            # Draw the bounding box if confidence is above the threshold
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"Class: {cls}, Conf: {conf:.2f}", 
                        (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
    score = 1 - (boxes_area/area)
    cv2.putText(frame, f"Score: {score:.2f}", 
                            (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)
    

    cv2.imwrite(f'frames/frame_{frame_num}.jpg', frame)
    
    # Display the frame
    cv2.imshow("frame", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()