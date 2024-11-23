from predict import process_video

process_video("sample.mp4", model_path="weights/best.pt", output_frames_dir="frames", conf_thresh=0.25, iou_thresh=0.5)