#!/usr/bin/env python3
"""
Kamera Kalibrasyonu - OpenCV
Logitech C920 Pro ve diğer USB kameralar için

Kullanım:
1. Satranç tahtası desenini yazdırın (9x6 iç köşe)
2. Scripti çalıştırın: python camera_calibration.py
3. Farklı açılardan 15-20 fotoğraf çekin
4. Kalibrasyon sonuçlarını kaydedin

Gereksinimler:
pip install opencv-python numpy matplotlib
"""

import cv2
import numpy as np
import os
import json
from datetime import datetime
import matplotlib.pyplot as plt

class CameraCalibrator:
    def __init__(self, checkerboard_size=(9, 6), square_size_mm=25.0):
        """
        Kamera kalibratörü başlatıcı
        
        Args:
            checkerboard_size: (width, height) iç köşe sayısı
            square_size_mm: Satranç tahtası kare boyutu (mm)
        """
        self.checkerboard_size = checkerboard_size
        self.square_size_mm = square_size_mm
        
        # 3D nokta koordinatları hazırla
        self.objp = np.zeros((checkerboard_size[0] * checkerboard_size[1], 3), np.float32)
        self.objp[:, :2] = np.mgrid[0:checkerboard_size[0], 0:checkerboard_size[1]].T.reshape(-1, 2)
        self.objp *= square_size_mm
        
        # Veri saklama listeleri
        self.objpoints = []  # 3D noktalar
        self.imgpoints = []  # 2D noktalar
        self.images = []     # Kalibrasyon görüntüleri
        
        # Sonuçlar
        self.camera_matrix = None
        self.dist_coeffs = None
        self.calibration_error = None
        
    def capture_calibration_images(self, camera_id=0, target_count=20):
        """
        Kalibrasyon için görüntü yakalama
        
        Args:
            camera_id: Kamera ID (genellikle 0)
            target_count: Hedef görüntü sayısı
        """
        print(f"Kamera {camera_id} açılıyor...")
        cap = cv2.VideoCapture(camera_id)
        
        # Logitech C920 Pro için önerilen ayarlar
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        if not cap.isOpened():
            print("Kamera açılamadı!")
            return False
            
        print(f"\n=== KALIBRASYON MODU ===")
        print(f"Hedef: {target_count} fotoğraf")
        print(f"Satranç tahtası: {self.checkerboard_size[0]}x{self.checkerboard_size[1]} iç köşe")
        print(f"Kare boyutu: {self.square_size_mm}mm")
        print("\nKontroller:")
        print("  's' - Fotoğraf çek (pattern bulunduğunda)")
        print("  'r' - Son fotoğrafı sil")
        print("  'q' - Çıkış")
        print("  'c' - Kalibrasyonu başlat")
        
        captured_count = 0
        
        while captured_count < target_count:
            ret, frame = cap.read()
            if not ret:
                print("Kameradan görüntü alınamadı!")
                break
                
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Satranç tahtası köşelerini bul
            ret_corners, corners = cv2.findChessboardCorners(
                gray, self.checkerboard_size, None,
                cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FAST_CHECK + cv2.CALIB_CB_NORMALIZE_IMAGE
            )
            
            # Görüntü üzerine bilgi yaz
            info_color = (0, 255, 0) if ret_corners else (0, 0, 255)
            status_text = f"Pattern: {'BULUNDU' if ret_corners else 'BULUNAMADI'}"
            cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, info_color, 2)
            cv2.putText(frame, f"Yakalanan: {captured_count}/{target_count}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            if ret_corners:
                # Köşeleri çiz
                cv2.drawChessboardCorners(frame, self.checkerboard_size, corners, ret_corners)
                cv2.putText(frame, "Hazir! 's' tusuna basin", (10, 90), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow('Kamera Kalibrasyonu', frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('s') and ret_corners:
                # Köşe koordinatlarını iyileştir
                criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
                
                self.objpoints.append(self.objp)
                self.imgpoints.append(corners2)
                self.images.append(gray.copy())
                captured_count += 1
                
                print(f"✓ Fotoğraf {captured_count} kaydedildi")
                
            elif key == ord('r') and captured_count > 0:
                # Son fotoğrafı sil
                self.objpoints.pop()
                self.imgpoints.pop()
                self.images.pop()
                captured_count -= 1
                print(f"✗ Son fotoğraf silindi. Kalan: {captured_count}")
                
            elif key == ord('c') and captured_count >= 10:
                print(f"\nKalibrasyon başlatılıyor ({captured_count} fotoğraf ile)...")
                break
                
            elif key == ord('q'):
                print("Kullanıcı tarafından iptal edildi.")
                cap.release()
                cv2.destroyAllWindows()
                return False
        
        cap.release()
        cv2.destroyAllWindows()
        
        if captured_count < 10:
            print(f"Yetersiz fotoğraf! En az 10 gerekli, {captured_count} var.")
            return False
            
        return True
    
    def calibrate(self):
        """
        Kamera kalibrasyonunu gerçekleştir
        """
        if len(self.objpoints) < 10:
            print("Kalibrasyon için yeterli veri yok!")
            return False
            
        print("Kalibrasyon hesaplanıyor...")
        
        # İlk görüntünün boyutunu al
        img_shape = self.images[0].shape[::-1]
        
        # Kalibrasyon hesapla
        ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
            self.objpoints, self.imgpoints, img_shape, None, None
        )
        
        if not ret:
            print("Kalibrasyon başarısız!")
            return False
            
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
        
        # Kalibrasyon hatasını hesapla
        total_error = 0
        for i in range(len(self.objpoints)):
            imgpoints2, _ = cv2.projectPoints(
                self.objpoints[i], rvecs[i], tvecs[i], camera_matrix, dist_coeffs
            )
            error = cv2.norm(self.imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
            total_error += error
            
        self.calibration_error = total_error / len(self.objpoints)
        
        print("✓ Kalibrasyon tamamlandı!")
        return True
    
    def print_results(self):
        """
        Kalibrasyon sonuçlarını yazdır
        """
        if self.camera_matrix is None:
            print("Henüz kalibrasyon yapılmadı!")
            return
            
        print("\n" + "="*50)
        print("KALIBRASYON SONUÇLARI")
        print("="*50)
        
        fx = self.camera_matrix[0, 0]
        fy = self.camera_matrix[1, 1]
        cx = self.camera_matrix[0, 2]
        cy = self.camera_matrix[1, 2]
        
        print(f"Focal Length X (fx): {fx:.3f} piksel")
        print(f"Focal Length Y (fy): {fy:.3f} piksel")
        print(f"Principal Point X (cx): {cx:.3f} piksel")
        print(f"Principal Point Y (cy): {cy:.3f} piksel")
        print(f"Ortalama Reprojection Error: {self.calibration_error:.3f} piksel")
        
        print(f"\nKamera Matrisi:")
        print(self.camera_matrix)
        
        print(f"\nDistortion Coefficients:")
        print(self.dist_coeffs.flatten())
        
        # MATLAB formatında yazdır
        print(f"\n--- MATLAB Formatı ---")
        print(f"fx_px = {fx:.3f};")
        print(f"fy_px = {fy:.3f};")
        print(f"cx_px = {cx:.3f};")
        print(f"cy_px = {cy:.3f};")
        print(f"K_cam = [{fx:.3f}, 0, {cx:.3f};")
        print(f"         0, {fy:.3f}, {cy:.3f};")
        print(f"         0, 0, 1];")
    
    def save_calibration(self, filename="camera_calibration"):
        """
        Kalibrasyon sonuçlarını kaydet
        """
        if self.camera_matrix is None:
            print("Kaydedilecek kalibrasyon verisi yok!")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # NumPy formatında kaydet
        np.savez(f"{filename}_{timestamp}.npz",
                camera_matrix=self.camera_matrix,
                dist_coeffs=self.dist_coeffs,
                calibration_error=self.calibration_error,
                checkerboard_size=self.checkerboard_size,
                square_size_mm=self.square_size_mm)
        
        # JSON formatında da kaydet
        calibration_data = {
            "timestamp": timestamp,
            "camera_matrix": self.camera_matrix.tolist(),
            "dist_coeffs": self.dist_coeffs.tolist(),
            "calibration_error": float(self.calibration_error),
            "checkerboard_size": self.checkerboard_size,
            "square_size_mm": self.square_size_mm,
            "fx": float(self.camera_matrix[0, 0]),
            "fy": float(self.camera_matrix[1, 1]),
            "cx": float(self.camera_matrix[0, 2]),
            "cy": float(self.camera_matrix[1, 2])
        }
        
        with open(f"{filename}_{timestamp}.json", 'w') as f:
            json.dump(calibration_data, f, indent=2)
        
        print(f"✓ Kalibrasyon kaydedildi:")
        print(f"  - {filename}_{timestamp}.npz")
        print(f"  - {filename}_{timestamp}.json")
    
    def test_calibration(self, camera_id=0):
        """
        Kalibrasyonu test et
        """
        if self.camera_matrix is None:
            print("Test için kalibrasyon verisi yok!")
            return
            
        print("Kalibrasyon testi başlatılıyor...")
        print("'q' tuşu ile çıkış")
        
        cap = cv2.VideoCapture(camera_id)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Distorsiyon düzeltme
            undistorted = cv2.undistort(frame, self.camera_matrix, self.dist_coeffs)
            
            # Yan yana göster
            combined = np.hstack((frame, undistorted))
            
            # Başlık ekle
            cv2.putText(combined, "Original", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(combined, "Undistorted", (650, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.imshow('Kalibrasyon Testi - Original vs Undistorted', combined)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()

def main():
    """
    Ana fonksiyon
    """
    print("Kamera Kalibrasyonu - OpenCV")
    print("="*40)
    
    # Kalibratör oluştur
    calibrator = CameraCalibrator(
        checkerboard_size=(9, 6),  # 9x6 iç köşe
        square_size_mm=25.0        # 25mm kare boyutu
    )
    
    try:
        # 1. Kalibrasyon görüntülerini yakala
        if not calibrator.capture_calibration_images(camera_id=0, target_count=20):
            print("Görüntü yakalama başarısız!")
            return
        
        # 2. Kalibrasyonu gerçekleştir
        if not calibrator.calibrate():
            print("Kalibrasyon başarısız!")
            return
        
        # 3. Sonuçları göster
        calibrator.print_results()
        
        # 4. Sonuçları kaydet
        calibrator.save_calibration("logitech_c920_calibration")
        
        # 5. Test et (isteğe bağlı)
        test_choice = input("\nKalibrasyonu test etmek ister misiniz? (y/n): ")
        if test_choice.lower() == 'y':
            calibrator.test_calibration()
            
    except KeyboardInterrupt:
        print("\nProgram kullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    main() 