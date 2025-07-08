import cv2
import time
import torch
import threading
import numpy as np
from PyQt5.QtCore import QThread
import os
import sys

# Config ve logger imports
from src.utils.config import config
from src.utils.logger import logger

# Kamera kalibrasyonu import
try:
    from src.utils.camera_calibration_service import CameraCalibrationService, find_latest_calibration_file
    CALIBRATION_AVAILABLE = True
except ImportError:
    CALIBRATION_AVAILABLE = False
    logger.warning("⚠️ Kamera kalibrasyon servisi bulunamadı, lens distorsiyonu düzeltilmeyecek")

# ByteTrack import kontrolü
try:
    # ByteTrack gerçek implementasyonu için path ekleme
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'OC_SORT'))
    from OC_SORT.trackers.byte_tracker.byte_tracker import BYTETracker, STrack
    from OC_SORT.trackers.byte_tracker.basetrack import TrackState
except ImportError as e:
    try:
        # Alternatif olarak OC_SORT direkten import et
        from OC_SORT.trackers.byte_tracker.byte_tracker_public import BYTETracker, STrack
        from OC_SORT.trackers.byte_tracker.basetrack import TrackState
    except ImportError as e2:
        raise ImportError("ByteTracker import edilemedi. Lütfen OC_SORT kurulumunu kontrol edin.")

from ultralytics import YOLO
from src.utils.visuals import draw_annotations, assign_class_to_track, draw_overlay_info

# ByteTracker parametreleri için arguments class
class Args:
    def __init__(self):
        # Config'den parametreleri al
        self.track_thresh = config.track_thresh  # High confidence threshold
        self.track_buffer = config.track_buffer  # Buffer size
        self.match_thresh = config.match_thresh  # Association threshold
        self.mot20 = False       # MOT20 dataset flag
        
        # Performans için optimize edilmiş parametreler
        self.min_box_area = 100  # Minimum detection area
        self.aspect_ratio_thresh = 1.6  # Aspect ratio threshold
        
        logger.debug(f"ByteTracker Args: thresh={self.track_thresh}, buffer={self.track_buffer}, match={self.match_thresh}")

stop_event = threading.Event()

def stop_bytetrack_tracking():
    stop_event.set()

def reset_bytetrack_tracking():
    stop_event.clear()

def run_bytetrack_tracking(source, model_path, video_display, confidence_threshold=0.3):
    """Original tracking function - model dosyasından yükleyerek"""
    reset_bytetrack_tracking()
    
    logger.info(f"🔄 ByteTracker başlatılıyor - Model: {model_path}")
    model = YOLO(model_path)
    _run_bytetrack_with_loaded_model(source, model, video_display, confidence_threshold)


def run_bytetrack_with_model(source, loaded_model, video_display, confidence_threshold=0.3, motor_controller=None):
    """Preloaded model ile hızlı başlatma - model yükleme süresini atlar"""
    reset_bytetrack_tracking()
    
    logger.info(f"⚡ ByteTracker hızlı başlatma - Kamera: {source}, Confidence: {confidence_threshold}")
    _run_bytetrack_with_loaded_model(source, loaded_model, video_display, confidence_threshold, motor_controller)


def _run_bytetrack_with_loaded_model(source, model, video_display, confidence_threshold=0.3, motor_controller=None):
    """Ortak tracking fonksiyonu - loaded model ile çalışır"""
    labels = model.names
    logger.info(f"📹 Kamera bağlantısı açılıyor: {source}")
    
    # Kamera kalibrasyonu setup
    calibration_service = None
    if CALIBRATION_AVAILABLE:
        calibration_service = CameraCalibrationService()
        # En son kalibrasyon dosyasını otomatik bul ve yükle - önce data klasöründe ara
        calibration_file = find_latest_calibration_file("data") or find_latest_calibration_file(".")
        if calibration_file:
            if calibration_service.load_calibration(calibration_file):
                cal_info = calibration_service.get_calibration_info()
                if cal_info:
                    logger.info(f"📷 Kamera kalibrasyonu yüklendi - Error: {cal_info['calibration_error']:.3f}px")
                    logger.info(f"📷 Kalibrasyon dosyası: {calibration_file}")
                else:
                    logger.warning("⚠️ Kalibrasyon bilgisi alınamadı")
                    calibration_service = None
            else:
                logger.warning("⚠️ Kalibrasyon dosyası yüklenemedi")
                calibration_service = None
        else:
            logger.info("ℹ️ Kalibrasyon dosyası bulunamadı - ham kamera görüntüsü kullanılacak")
            calibration_service = None
    
    # Kamera açma - backend config'e göre
    if config.use_directshow_backend and isinstance(source, int):
        cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        logger.warning(f"⚠️ DSHOW backend başarısız, alternatif denenecek: {source}")
        # DSHOW başarısızsa alternatif dene
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            logger.error(f"❌ Kamera açılamadı: {source}")
            return

    video_fps = cap.get(cv2.CAP_PROP_FPS) or config.camera_fps
    logger.info(f"✅ Kamera başarıyla açıldı - FPS: {video_fps}")
    frame_count = 0
    
    # ByteTracker initialize
    args = Args()
    args.track_thresh = confidence_threshold
    byte_tracker = BYTETracker(args, frame_rate=int(video_fps))
    
    # Frame skipping ve buffering için
    frame_skip = max(1, int(video_fps / 30))  # 30 FPS'e normalize et
    
    # Tracking history for smoothing
    track_history = {}
    max_history = 10
    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        
        # Frame skipping - hızlı hareketlerde daha sık işle
        if frame_count % frame_skip != 0:
            continue

        start = time.time()
        
        # Kamera kalibrasyonu uygulanması (lens distorsiyonu düzeltme)
        original_frame = frame.copy()  # Orijinal frame'i sakla
        if calibration_service and calibration_service.is_calibrated():
            frame = calibration_service.undistort_frame(frame)
        
        # YOLO detection (tracking olmadan, sadece detection)
        results = model(
            source=frame,
            verbose=False,
            conf=confidence_threshold,
            save=False,
            stream=False
        )[0]

        # YOLO sonuçlarını ByteTracker formatına çevir
        detections = []
        if results.boxes is not None:
            boxes = results.boxes.xyxy.cpu().numpy()  # x1, y1, x2, y2
            scores = results.boxes.conf.cpu().numpy()
            
            # Filtreleme: minimum area ve aspect ratio
            for i, (box, score) in enumerate(zip(boxes, scores)):
                x1, y1, x2, y2 = box
                w, h = x2 - x1, y2 - y1
                
                # Minimum alan kontrolü
                if w * h < byte_tracker.args.min_box_area:
                    continue
                    
                # Aspect ratio kontrolü (çok uzun/ince olmayan nesneler)
                aspect_ratio = max(w/h, h/w) if min(w, h) > 0 else float('inf')
                if aspect_ratio > byte_tracker.args.aspect_ratio_thresh:
                    continue
                
                detections.append([x1, y1, x2, y2, score])

        # ByteTracker update - koordinat problemi çözümü
        if len(detections) > 0:
            detections = np.array(detections)
            # ByteTracker için doğru format: img_info = (height, width), img_size = (target_width, target_height)
            # Scaling'i devre dışı bırakmak için img_size = frame boyutu yapalım
            img_info = (frame.shape[0], frame.shape[1])  # height, width (orijinal)
            img_size = (frame.shape[1], frame.shape[0])  # width, height (aynı boyut = scale 1.0)
            
            online_targets = byte_tracker.update(detections, img_info, img_size)
        else:
            # Boş detection durumunda da tracker'ı güncelle
            online_targets = byte_tracker.update(np.empty((0, 5)), 
                                               (frame.shape[0], frame.shape[1]),
                                               (frame.shape[1], frame.shape[0]))

        # Tracking sonuçlarını çiz ve motor kontrolü için detection listesi hazırla
        object_count = 0
        detection_list = []
        
        for track in online_targets:
            track_id = track.track_id
            
            # ByteTracker koordinatlarını debug et
            tlbr_coords = track.tlbr.astype(int)
            x1, y1, x2, y2 = tlbr_coords
            
            # Koordinatları kontrol et ve düzelt
            x1 = max(0, min(x1, frame.shape[1]))
            y1 = max(0, min(y1, frame.shape[0]))
            x2 = max(0, min(x2, frame.shape[1]))
            y2 = max(0, min(y2, frame.shape[0]))
            
            # Geçersiz koordinatları atla
            if x2 <= x1 or y2 <= y1:
                continue
            
            # Balonun mevcut merkezi
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            # Tracking history güncelle
            if track_id not in track_history:
                track_history[track_id] = []
            track_history[track_id].append((center_x, center_y))
            
            # History boyutunu sınırla
            if len(track_history[track_id]) > max_history:
                track_history[track_id] = track_history[track_id][-max_history:]

            
            # Kalman filter FUTURE prediction - velocity kullanarak gelecek tahmini
            pred_x, pred_y = center_x, center_y  # Varsayılan olarak mevcut merkez
            
            if hasattr(track, 'mean') and track.mean is not None and len(track.mean) >= 6:
                # Kalman state: [center_x, center_y, aspect_ratio, height, vx, vy, va, vh]
                current_x = track.mean[0]  # Mevcut x
                current_y = track.mean[1]  # Mevcut y
                velocity_x = track.mean[4] if len(track.mean) > 4 else 0  # x hızı
                velocity_y = track.mean[5] if len(track.mean) > 5 else 0  # y hızı
                
                # FUTURE prediction = mevcut konum + velocity * 2 (2 frame ahead için daha yakın tahmin)
                prediction_frames = 2  # 2 frame ileri tahmin
                future_x = int(current_x + velocity_x * prediction_frames)
                future_y = int(current_y + velocity_y * prediction_frames)
                
                # Future prediction'ı makul sınırlar içindeyse kullan
                if (0 <= future_x < frame.shape[1] and 
                    0 <= future_y < frame.shape[0]):
                    pred_x, pred_y = future_x, future_y
                else:
                    # Sınır dışındaysa daha kısa prediction yaparak hesapla
                    pred_x = int(current_x + velocity_x * 1.0)  # 1.0 frame ahead
                    pred_y = int(current_y + velocity_y * 1.0)  # 1.0 frame ahead
                    pred_x = max(0, min(pred_x, frame.shape[1] - 1))
                    pred_y = max(0, min(pred_y, frame.shape[0] - 1))
            
            # Kalite skoru göster
            score_text = f"S:{track.score:.2f}" if hasattr(track, 'score') else ""
            label_text = f"ID:{track_id} {score_text}"
            
            draw_annotations(frame, x1, y1, x2, y2, track_id, pred_x, pred_y, label_text)
            object_count += 1
            
            # Motor kontrol sistemi için detection ekle
            detection_list.append([x1, y1, x2 - x1, y2 - y1, track.score if hasattr(track, 'score') else 0.8, 
                                 pred_x, pred_y, track_id])
            
            # Trajectory çiz (son 5 point) - daha ince çizgi
            if len(track_history[track_id]) > 1:
                points = track_history[track_id][-5:]
                for i in range(1, len(points)):
                    cv2.line(frame, points[i-1], points[i], (0, 200, 0), 1)  # Daha ince (1 pixel) ve daha koyu yeşil

        end = time.time()
        frame_time = end - start
        fps = 1 / frame_time if frame_time > 0 else 0

        # Tracking bilgileri
        tracked_count = len([t for t in byte_tracker.tracked_stracks if t.is_activated])
        lost_count = len(byte_tracker.lost_stracks)
        
        # Kalibrasyon durumu için algo_name'e ekle
        algo_name = f"ByteTrack+ (T:{tracked_count} L:{lost_count})"
        if calibration_service and calibration_service.is_calibrated():
            cal_error = calibration_service.calibration_error
            algo_name += f" [CAL:{cal_error:.2f}px]"
        else:
            algo_name += " [RAW]"
        
        draw_overlay_info(
            frame, fps, frame_time * 1000, object_count,
            algo_name=algo_name,
            frame_number=frame_count
        )
        
        # Motor kontrol sistemi güncelleme
        if motor_controller and detection_list:
            try:
                motor_controller.set_detections(detection_list)
            except Exception as e:
                logger.debug(f"Motor controller güncelleme hatası: {e}")

        resized_frame = cv2.resize(frame, (1280, 720))

        if video_display:
            video_display.update_frame(resized_frame)
            if isinstance(source, str):
                QThread.msleep(int(1000 / video_fps / frame_skip))
        else:
            cv2.imshow("Balon Takibi - ByteTrack+", resized_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    logger.info("🔚 ByteTracker tracking sonlandırıldı")
    if not video_display:
        cv2.destroyAllWindows() 