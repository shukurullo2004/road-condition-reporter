from ultralytics import YOLO
import cv2
import os

def process_video(video_path, model_path="weights/best.pt", output_dir="output.avi", conf_thresh=0.25, iou_thresh=0.5, save=False):
    """
    Process a video file using a YOLO model to perform object detection and save results.

    Parameters:
        video_path (str): Path to the input video file.
        model_path (str): Path to the YOLO model weights file.
        output_frames_dir (str): Directory to save processed frames.
        conf_thresh (float): Confidence threshold for detection.
        iou_thresh (float): IoU threshold for detection.
    """
    # Load the YOLO model
    model = YOLO(model_path)
    
    # Initialize video capture
    cap = cv2.VideoCapture(video_path)
    
    # save the video
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
        
        # Get frame dimensions and area
        area = frame.shape[0] * frame.shape[1]
        frame_num += 1

        # Run inference on the frame
        results = model(frame, conf=conf_thresh, iou=iou_thresh)
        
        # Initialize total boxes area
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

                # Draw the bounding box and label
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"Class: {cls}, Conf: {conf:.2f}",
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Calculate and display the score
        score = 1 - (boxes_area / area)
        cv2.putText(frame, f"Score: {score:.2f}",
                    (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)
        # fps
        # cv2.putText(frame, f"FPS: {fps:.2f}",
        #            (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)
        
        
        # Save the processed frame
        # cv2.imwrite(os.path.join(output_frames_dir, f"frame_{frame_num}.jpg"), frame)
        if save:
            out.write(frame)
        
        
        # Display the frame
        cv2.imshow("frame", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release resources
    cap.release()
    cv2.destroyAllWindows()
    print(f"Processed {frame_num} frames. Saved results in {output_dir}.")
