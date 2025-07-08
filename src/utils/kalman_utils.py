import numpy as np
from filterpy.kalman import KalmanFilter

def create_kalman_filter(x, y):
    kf = KalmanFilter(dim_x=4, dim_z=2)
    kf.x = np.array([x, y, 0, 0])  # [x, y, vx, vy]
    kf.F = np.array([[1, 0, 1, 0],
                     [0, 1, 0, 1],
                     [0, 0, 1, 0],
                     [0, 0, 0, 1]])  # Sabit zaman aralığı (dt = 1)
    kf.H = np.array([[1, 0, 0, 0],
                     [0, 1, 0, 0]])  # Sadece x, y ölçülüyor
    kf.P *= 1000.
    kf.R = np.eye(2) * 10
    kf.Q = np.eye(4)
    return kf

def update_kalman(track_id, cx, cy, kalman_filters):
    if track_id not in kalman_filters:
        kalman_filters[track_id] = create_kalman_filter(cx, cy)

    kf = kalman_filters[track_id]
    kf.predict()
    kf.update(np.array([cx, cy]))

    # Tahmin edilen bir sonraki konumu (bir adım ileri) döndür
    predicted_next_state = np.dot(kf.F, kf.x)
    pred_x, pred_y = int(predicted_next_state[0]), int(predicted_next_state[1])
    return pred_x, pred_y
