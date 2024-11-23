from predict import process_video

process_video('sample.mp4', model_path="./models/weights/best.pt", conf_thresh=0.25, iou_thresh=0.5, save=False)