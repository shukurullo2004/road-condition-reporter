import cv2


def capture_image():
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        image_path = ""
        cv2.imwrite(image_path, frame)s
        cap.release()
        return image_path
    else:
        cap.release()
        raise Exception("Failed to capture image")
