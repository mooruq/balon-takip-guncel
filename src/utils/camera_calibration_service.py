#!/usr/bin/env python3
"""
Camera Calibration Service
Mevcut balon takip sistemine entegre edilmiş kamera kalibrasyon servisi

Bu servis kamera parametrelerini hesaplayarak:
- Lens distorsiyonunu düzeltir  
- Hassas koordinat dönüşümü sağlar
- IBVS algoritmasının performansını artırır
"""

import cv2
import numpy as np
import os
import json
from datetime import datetime
import logging

class CameraCalibrationService:
    def __init__(self, checkerboard_size=(9, 6), square_size_mm=25.0):
        """
        Kamera kalibrasyon servisi
        
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
        
        # Sonuçlar
        self.camera_matrix = None
        self.dist_coeffs = None
        self.calibration_error = None
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
    def load_calibration(self, calibration_file):
        """
        Önceden kaydedilmiş kalibrasyon dosyasını yükle
        
        Args:
            calibration_file: .npz veya .json kalibrasyon dosya yolu
            
        Returns:
            bool: Yükleme başarılı mı
        """
        try:
            if calibration_file.endswith('.npz'):
                data = np.load(calibration_file)
                self.camera_matrix = data['camera_matrix']
                self.dist_coeffs = data['dist_coeffs']
                self.calibration_error = float(data['calibration_error'])
                
            elif calibration_file.endswith('.json'):
                with open(calibration_file, 'r') as f:
                    data = json.load(f)
                self.camera_matrix = np.array(data['camera_matrix'])
                self.dist_coeffs = np.array(data['dist_coeffs'])
                self.calibration_error = data['calibration_error']
                
            else:
                self.logger.error(f"Desteklenmeyen dosya formatı: {calibration_file}")
                return False
                
            self.logger.info(f"Kalibrasyon dosyası yüklendi: {calibration_file}")
            self.logger.info(f"Reprojection Error: {self.calibration_error:.3f} piksel")
            return True
            
        except Exception as e:
            self.logger.error(f"Kalibrasyon dosyası yüklenemedi: {e}")
            return False
    
    def undistort_frame(self, frame):
        """
        Kalibrasyon parametrelerini kullanarak görüntü distorsiyonunu düzelt
        
        Args:
            frame: OpenCV görüntü (BGR)
            
        Returns:
            Düzeltilmiş görüntü veya orijinal görüntü (kalibrasyon yoksa)
        """
        if self.camera_matrix is None or self.dist_coeffs is None:
            return frame
            
        try:
            # type: ignore yapıyoruz OpenCV type annotation sorunları için
            undistorted = cv2.undistort(frame, self.camera_matrix, self.dist_coeffs)  # type: ignore
            return undistorted
        except Exception as e:
            self.logger.error(f"Distorsiyon düzeltme hatası: {e}")
            return frame
    
    def pixel_to_world_coordinates(self, pixel_coords, z_distance=1.0):
        """
        Piksel koordinatlarını dünya koordinatlarına dönüştür
        
        Args:
            pixel_coords: (x, y) piksel koordinatları
            z_distance: Z mesafesi (metre)
            
        Returns:
            (x, y) dünya koordinatları (metre)
        """
        if self.camera_matrix is None:
            return pixel_coords
            
        try:
            fx = self.camera_matrix[0, 0]
            fy = self.camera_matrix[1, 1]
            cx = self.camera_matrix[0, 2]
            cy = self.camera_matrix[1, 2]
            
            # Kamera koordinat sisteminde
            x_cam = (pixel_coords[0] - cx) * z_distance / fx
            y_cam = (pixel_coords[1] - cy) * z_distance / fy
            
            return (x_cam, y_cam)
            
        except Exception as e:
            self.logger.error(f"Koordinat dönüşüm hatası: {e}")
            return pixel_coords
    
    def world_to_pixel_coordinates(self, world_coords, z_distance=1.0):
        """
        Dünya koordinatlarını piksel koordinatlarına dönüştür
        
        Args:
            world_coords: (x, y) dünya koordinatları (metre)
            z_distance: Z mesafesi (metre)
            
        Returns:
            (x, y) piksel koordinatları
        """
        if self.camera_matrix is None:
            return world_coords
            
        try:
            fx = self.camera_matrix[0, 0]
            fy = self.camera_matrix[1, 1]
            cx = self.camera_matrix[0, 2]
            cy = self.camera_matrix[1, 2]
            
            # Piksel koordinatlarına dönüştür
            pixel_x = world_coords[0] * fx / z_distance + cx
            pixel_y = world_coords[1] * fy / z_distance + cy
            
            return (pixel_x, pixel_y)
            
        except Exception as e:
            self.logger.error(f"Koordinat dönüşüm hatası: {e}")
            return world_coords
    
    def get_focal_length_pixels(self):
        """
        Odak uzaklığını piksel cinsinden döndür
        
        Returns:
            (fx, fy) focal length piksel cinsinden
        """
        if self.camera_matrix is None:
            return None
            
        fx = self.camera_matrix[0, 0]
        fy = self.camera_matrix[1, 1]
        return (fx, fy)
    
    def get_principal_point(self):
        """
        Ana nokta koordinatlarını döndür
        
        Returns:
            (cx, cy) ana nokta koordinatları
        """
        if self.camera_matrix is None:
            return None
            
        cx = self.camera_matrix[0, 2]
        cy = self.camera_matrix[1, 2]
        return (cx, cy)
    
    def is_calibrated(self):
        """
        Kameranın kalibre olup olmadığını kontrol et
        
        Returns:
            bool: Kalibrasyon durumu
        """
        return (self.camera_matrix is not None and 
                self.dist_coeffs is not None)
    
    def get_calibration_info(self):
        """
        Kalibrasyon bilgilerini döndür
        
        Returns:
            dict: Kalibrasyon parametreleri
        """
        if not self.is_calibrated():
            return None
            
        fx, fy = self.get_focal_length_pixels()
        cx, cy = self.get_principal_point()
        
        return {
            'camera_matrix': self.camera_matrix.tolist(),
            'dist_coeffs': self.dist_coeffs.tolist(),
            'focal_length_pixels': (fx, fy),
            'principal_point': (cx, cy),
            'calibration_error': self.calibration_error,
            'checkerboard_size': self.checkerboard_size,
            'square_size_mm': self.square_size_mm
        }

def find_latest_calibration_file(search_dir="."):
    """
    En son oluşturulan kalibrasyon dosyasını bul
    
    Args:
        search_dir: Arama yapılacak dizin
        
    Returns:
        str: Kalibrasyon dosya yolu veya None
    """
    try:
        # .npz ve .json dosyalarını ara
        calibration_files = []
        
        for filename in os.listdir(search_dir):
            if 'calibration' in filename and (filename.endswith('.npz') or filename.endswith('.json')):
                file_path = os.path.join(search_dir, filename)
                mtime = os.path.getmtime(file_path)
                calibration_files.append((mtime, file_path))
        
        if calibration_files:
            # En son dosyayı döndür
            calibration_files.sort(reverse=True)
            return calibration_files[0][1]
        
        return None
        
    except Exception as e:
        logging.error(f"Kalibrasyon dosyası arama hatası: {e}")
        return None 