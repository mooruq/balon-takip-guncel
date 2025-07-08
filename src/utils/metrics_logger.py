import os
import json

def save_metrics_log(video_path, algorithm_name, avg_fps, num_frames, total_objects,
                     avg_frame_time_ms=None, unique_objects=None,
                     avg_track_persistence=None, fragmentation_score=None):
    
    os.makedirs("tracking_metrics", exist_ok=True)
    video_name = os.path.splitext(os.path.basename(str(video_path)))[0]
    log_path = f"tracking_metrics/{video_name}_{algorithm_name.lower()}.json"

    avg_objects_per_frame = total_objects / num_frames if num_frames else 0

    log_data = {
        "video": video_name,
        "algorithm": algorithm_name,
        "average_fps": round(avg_fps, 2),
        "avg_frame_time_ms": round(avg_frame_time_ms, 2) if avg_frame_time_ms is not None else None,
        "total_frames": num_frames,
        "total_objects": total_objects,
        "avg_objects_per_frame": round(avg_objects_per_frame, 2),
        "unique_objects": unique_objects,
        "avg_track_persistence": round(avg_track_persistence, 2) if avg_track_persistence is not None else None,
        "fragmentation_score": round(fragmentation_score, 2) if fragmentation_score is not None else None
    }

    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2)
