import cv2
import numpy as np

def compute_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)
    boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
    boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)
    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou

def assign_class_to_track(trk_box, det_boxes, det_classes, iou_thresh=0.3):
    best_iou = 0
    assigned_cls = -1
    for box, cls in zip(det_boxes, det_classes):
        iou = compute_iou(trk_box, box)
        if iou > best_iou and iou >= iou_thresh:
            best_iou = iou
            assigned_cls = cls
    return assigned_cls

def draw_annotations(frame, x1, y1, x2, y2, track_id, pred_x, pred_y, label_text):
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_color = (255, 255, 255)
    box_color = (0, 255, 0)  # Yeşil bounding box

    # Dikdörtgen ve etiket çizimi
    cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
    label_size = cv2.getTextSize(label_text, font, 0.4, 1)[0]
    label_width = label_size[0] + 10
    label_height = label_size[1] + 10
    cv2.rectangle(frame, (x1, y1 - label_height), (x1 + label_width, y1), box_color, -1)
    cv2.putText(frame, label_text, (x1 + 5, y1 - 5), font, 0.4, text_color, 1)

    # Balonun gerçek merkezi (bounding box merkezi) - KÜÇÜK YEŞİL NOKTA
    center_x = int((x1 + x2) / 2)
    center_y = int((y1 + y2) / 2)
    
    # Merkez nokta - küçük yeşil nokta
    cv2.circle(frame, (center_x, center_y), 3, (0, 255, 0), -1)  # Yeşil dolu daire (3 pixel)
    
    # Kalman prediction - HER ZAMAN SARI HALKA ÇİZ
    # Prediction konumu valid ise her zaman göster
    if 0 <= pred_x < frame.shape[1] and 0 <= pred_y < frame.shape[0]:
        # Tek halka yeterli - daha temiz görünüm
        cv2.circle(frame, (pred_x, pred_y), 10, (0, 255, 255), 2)  # Sarı halka (10 pixel, 2 kalınlık)
        # Eğer prediction merkez ile farklıysa merkez nokta da ekle
        if abs(pred_x - center_x) > 2 or abs(pred_y - center_y) > 2:
            cv2.circle(frame, (pred_x, pred_y), 2, (0, 255, 255), -1)  # Prediction merkezi (2 pixel dolu)

def draw_overlay_info(frame, fps, ms, object_count, algo_name="", id_switches=None, frame_number=None):
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.4  # Daha küçük font
    thickness = 1
    
    # Kompakt bilgiler - tek satırda
    info_text = f"FPS:{int(fps)} | {int(ms)}ms | Balon:{object_count}"
    
    # Metin boyutunu ölç
    text_size = cv2.getTextSize(info_text, font, font_scale, thickness)[0]
    
    # Küçük, yuvarlatılmış köşeli arkaplan
    padding = 8
    bg_width = text_size[0] + 2 * padding
    bg_height = text_size[1] + 2 * padding
    
    # Sol üst köşede minimal alan
    x_pos = 10
    y_pos = 10
    
    # Yarı şeffaf arkaplan - daha estetik
    overlay = frame.copy()
    cv2.rectangle(overlay, (x_pos, y_pos), (x_pos + bg_width, y_pos + bg_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    
    # İnce beyaz çerçeve
    cv2.rectangle(frame, (x_pos, y_pos), (x_pos + bg_width, y_pos + bg_height), (255, 255, 255), 1)
    
    # Metin - beyaz renk
    cv2.putText(frame, info_text, (x_pos + padding, y_pos + text_size[1] + padding - 2), 
                font, font_scale, (255, 255, 255), thickness)
    
    # İkinci satır - ByteTrack bilgisi (daha küçük)
    if algo_name:
        algo_text = algo_name.replace("ByteTrack+ (", "").replace(")", "")  # Sadece T:X L:Y kısmı
        algo_size = cv2.getTextSize(algo_text, font, 0.35, 1)[0]
        
        algo_y = y_pos + bg_height + 5
        cv2.rectangle(frame, (x_pos, algo_y), (x_pos + algo_size[0] + 12, algo_y + algo_size[1] + 8), (0, 0, 0), -1)
        cv2.putText(frame, algo_text, (x_pos + 6, algo_y + algo_size[1] + 4), 
                    font, 0.35, (100, 255, 100), 1)  # Açık yeşil

