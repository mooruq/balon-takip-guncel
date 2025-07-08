#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Motor Pan-Tilt Control Service - IBVS Implementation
--------------------------------------------------
Service for controlling pan-tilt mechanism using Image-Based Visual Servoing (IBVS).
Enhanced PID control, adaptive gains, and Kalman filter integration for Balon Takip system.
Uses LZ-100 servo motors with Modbus RTU protocol.
"""

import time
import threading
import math
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from src.utils.logger import logger
from src.utils.config import config
from src.services.lz100_servo_service import LZ100ServoService


class MotorPanTiltService(QObject):
    """
    IBVS Pan-Tilt Control Service with LZ-100 Servo Motors.
    
    Features:
    - PID control with integral and derivative terms
    - Adaptive gain system based on error magnitude
    - Progressive reduction based on error magnitude
    - Kalman filter prediction integration
    - LZ-100 servo motor control via Modbus RTU
    
    Servo assignments:
    - Pan servo (Slave ID: 1) controls vertical movement
    - Tilt servo (Slave ID: 10) controls horizontal movement
    """
    
    # Signals
    command_sent = pyqtSignal(str)
    tracking_update = pyqtSignal(int, int, int, int)
    connection_status_changed = pyqtSignal(bool)
    target_reached = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        # LZ-100 Servo Control Service
        self.servo_service = LZ100ServoService()
        self.servo_service.connection_status_changed.connect(self.connection_status_changed.emit)
        self.servo_service.command_sent.connect(self.command_sent.emit)
        self.is_connected = False
        
        # Current servo speeds (RPM)
        self.pan_speed = 0
        self.tilt_speed = 0
        
        # Speed limits (RPM) from config
        self.max_speed = config.lz100_max_speed   # From config
        self.min_speed = config.lz100_min_speed   # From config
        
        # IBVS Control Parameters from config
        self.K_pan_gain_ibvs = config.ibvs_pan_gain
        self.K_tilt_gain_ibvs = config.ibvs_tilt_gain
        
        # PID additional parameters
        self.K_pan_integral_ibvs = config.ibvs_pan_integral
        self.K_tilt_integral_ibvs = config.ibvs_tilt_integral
        self.K_pan_derivative_ibvs = config.ibvs_pan_derivative
        self.K_tilt_derivative_ibvs = config.ibvs_tilt_derivative
        
        # Adaptive gain parameters
        self.gain_boost_threshold_px = 25.0  # Error threshold for gain boost
        self.gain_boost_factor = 1.8         # Gain multiplier
        self.min_speed_rps = config.lz100_min_speed  # Minimum speed in RPM from config
        
        self.deadzone_px = config.lz100_deadzone_threshold  # Deadzone in pixels
        self.max_speed_rps = config.lz100_max_speed   # Maximum speed in RPM from config
        
        # Error history for derivative calculation
        self.error_history_length = 6
        self.error_u_history = np.zeros(self.error_history_length)
        self.error_v_history = np.zeros(self.error_history_length)
        self.error_integral_u = 0.0
        self.error_integral_v = 0.0
        
        # Control loop timing
        self.control_loop_delay = 0.1  # Control loop time step (10 Hz)
        
        # Frame center coordinates (kamera merkezindeki artı işareti)
        self.center_x = config.camera_width // 2
        self.center_y = config.camera_height // 2
        
        # Camera intrinsic parameters (loaded from calibration)
        self.fx_px = config.camera_fx  # Focal length in pixels (x)
        self.fy_px = config.camera_fy  # Focal length in pixels (y)
        self.cx_px = config.camera_cx  # Principal point x
        self.cy_px = config.camera_cy  # Principal point y
        
        # Pixel size (meters/pixel)
        self.pixel_size_x = config.pixel_size_x
        self.pixel_size_y = config.pixel_size_y
        
        # Focal length in meters
        self.f_m = config.focal_length_m
        
        # Target parameters
        self.target_depth = 5.0  # Initial depth estimate (5 meters)
        
        # Tracking parameters
        self.target_id = None
        self.is_tracking = False
        self.tracking_thread = None
        self.tracking_lock = threading.Lock()
        
        # Detection data
        self.balloon_detections = []
        
        # Target persistence
        self.target_lost_count = 0
        self.max_target_lost_frames = 10
        self.last_known_target_pos = None
        
        # Error statistics
        self.error_history = []
        self.max_error_history = 30
        
        # Kalman filter integration
        self.use_kalman_prediction = True
        self.kalman_prediction_weight = 0.7  # 70% Kalman, 30% detection
        
        logger.info("🎯 IBVS Pan-Tilt Service with LZ-100 Servos initialized")
    
    def set_frame_center(self, width, height):
        """Set the center point of the frame."""
        self.center_x = width // 2
        self.center_y = height // 2
        # Update principal point if needed
        self.cx_px = self.center_x
        self.cy_px = self.center_y
        logger.info(f"🎯 Frame center set to ({self.center_x}, {self.center_y})")
    
    def connect(self):
        """Connect to the LZ-100 servo motors."""
        if self.is_connected:
            logger.info("🔌 LZ-100 servo bağlantısı zaten kurulmuş")
            return True
            
        try:
            logger.info("🔌 LZ-100 servo motorlarına bağlanılıyor...")
            
            if self.servo_service.connect():
                self.is_connected = True
                logger.info("✅ LZ-100 servo motorları başarıyla bağlandı")
                
                # Motorları durdur (merkez pozisyon)
                self.stop_movement()
                
                return True
            else:
                logger.error("❌ LZ-100 servo motorlarına bağlanılamadı")
                return False
                
        except Exception as e:
            self.is_connected = False
            logger.error(f"❌ LZ-100 servo bağlantısında hata: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from LZ-100 servo motors."""
        if self.is_tracking:
            self.stop_tracking()
            
        try:
            if self.servo_service:
                self.servo_service.disconnect()
                self.is_connected = False
                logger.info("🔌 LZ-100 servo motorlarından ayrıldı")
                return True
        except Exception as e:
            logger.error(f"❌ LZ-100 servo ayrılırken hata: {str(e)}")
            return False
    
    def send_command(self, command_str):
        """Send a command to the servo motors - kept for compatibility."""
        self.command_sent.emit(command_str)
        return True
    
    def move_to_speeds(self, pan_speed, tilt_speed):
        """Move servos to specific speeds."""
        if not self.is_connected or not self.servo_service:
            return False
        
        # Update current speeds
        self.pan_speed = pan_speed
        self.tilt_speed = tilt_speed
        
        # Send to servo service
        return self.servo_service.move_to_speeds(pan_speed, tilt_speed)
    
    def stop_movement(self):
        """Stop servo movement."""
        return self.move_to_speeds(0, 0)
    
    def emergency_stop(self):
        """ACİL DURDURMA - ANINDA motor durdur"""
        try:
            logger.warning("🚨 IBVS ACİL DURDURMA!")
            
            # 1. İLK ÖNCELİK: Servo motorları acil durdur
            if self.servo_service:
                self.servo_service.emergency_stop()
            
            # 2. Tracking'i zorla durdur
            self.is_tracking = False
            
            # 3. Hızları sıfırla
            self.pan_speed = 0
            self.tilt_speed = 0
            
            logger.warning("⚡ IBVS ACİL DURDURMA TAMAMLANDI!")
            return True
            
        except Exception as e:
            logger.error(f"❌ IBVS ACİL DURDURMA HATASI: {e}")
            return False
    
    def calculate_control_ibvs(self, target_x, target_y, target_width=None, target_height=None):
        """
        IBVS control calculation for LZ-100 servo motors with Kalman integration.
        
        Features:
        - PID control with integral and derivative terms
        - Adaptive gain system
        - Progressive reduction based on error magnitude
        - Direct speed control for servo motors
        - Kalman filter prediction integration
        
        Args:
            target_x: Target x-coordinate in image (hedef merkezi veya Kalman tahmini)
            target_y: Target y-coordinate in image (hedef merkezi veya Kalman tahmini)
            target_width: Target width for depth estimation
            target_height: Target height for depth estimation
            
        Returns:
            Tuple of (pan_speed_rpm, tilt_speed_rpm)
        """
        # Calculate pixel errors (kamera merkezindeki artı işaretine göre)
        error_u_px = target_x - self.cx_px  # Horizontal error (u-axis)
        error_v_px = target_y - self.cy_px  # Vertical error (v-axis)
        error_magnitude = np.sqrt(error_u_px**2 + error_v_px**2)
        
        # Store error in history
        self.error_history.append(error_magnitude)
        if len(self.error_history) > self.max_error_history:
            self.error_history.pop(0)
        
        # Update error history for derivative calculation
        self.error_u_history = np.roll(self.error_u_history, -1)
        self.error_v_history = np.roll(self.error_v_history, -1)
        self.error_u_history[-1] = error_u_px
        self.error_v_history[-1] = error_v_px
        
        # Calculate derivative (average of last 3 differences)
        if len(self.error_history) > 3:
            error_u_derivative = np.mean(np.diff(self.error_u_history[-3:])) / self.control_loop_delay
            error_v_derivative = np.mean(np.diff(self.error_v_history[-3:])) / self.control_loop_delay
        else:
            error_u_derivative = 0.0
            error_v_derivative = 0.0
        
        # Apply deadzone
        if abs(error_u_px) < self.deadzone_px:
            error_u_px = 0
            self.error_integral_u = 0
        if abs(error_v_px) < self.deadzone_px:
            error_v_px = 0
            self.error_integral_v = 0
        
        # Update integral with windup protection
        max_integral = 200  # Integral windup limit
        self.error_integral_u = np.clip(
            self.error_integral_u + error_u_px * self.control_loop_delay,
            -max_integral, max_integral
        )
        self.error_integral_v = np.clip(
            self.error_integral_v + error_v_px * self.control_loop_delay,
            -max_integral, max_integral
        )
        
        # Adaptive gain system
        if error_magnitude < self.gain_boost_threshold_px and error_magnitude > self.deadzone_px:
            # Close to target - boost gains
            K_pan_effective = self.K_pan_gain_ibvs * self.gain_boost_factor
            K_tilt_effective = self.K_tilt_gain_ibvs * self.gain_boost_factor
            K_pan_int_effective = self.K_pan_integral_ibvs * self.gain_boost_factor
            K_tilt_int_effective = self.K_tilt_integral_ibvs * self.gain_boost_factor
        else:
            # Normal gains
            K_pan_effective = self.K_pan_gain_ibvs
            K_tilt_effective = self.K_tilt_gain_ibvs
            K_pan_int_effective = self.K_pan_integral_ibvs
            K_tilt_int_effective = self.K_tilt_integral_ibvs
        
        # PID Control calculation for direct speed control
        # LZ-100 Servo motor directions:
        # - Hedef sağda (error_u_px > 0) → Tilt pozitif hız (sağa dönmek için)
        # - Hedef solda (error_u_px < 0) → Tilt negatif hız (sola dönmek için)
        # - Hedef aşağıda (error_v_px > 0) → Pan negatif hız (aşağı bakmak için)
        # - Hedef yukarıda (error_v_px < 0) → Pan pozitif hız (yukarı bakmak için)
        
        tilt_speed_rpm = (error_u_px * K_tilt_effective + 
                         self.error_integral_u * K_tilt_int_effective + 
                         error_u_derivative * self.K_tilt_derivative_ibvs)
                        
        pan_speed_rpm = (-error_v_px * K_pan_effective - 
                        self.error_integral_v * K_pan_int_effective - 
                        error_v_derivative * self.K_pan_derivative_ibvs)
        
        # Minimum speed guarantee (tam sayı olarak)
        if abs(pan_speed_rpm) > 0 and abs(pan_speed_rpm) < self.min_speed_rps:
            pan_speed_rpm = np.sign(pan_speed_rpm) * self.min_speed_rps
        if abs(tilt_speed_rpm) > 0 and abs(tilt_speed_rpm) < self.min_speed_rps:
            tilt_speed_rpm = np.sign(tilt_speed_rpm) * self.min_speed_rps
        
        # Tam sayıya çevir (motor sürücüsü için)
        pan_speed_rpm = int(round(pan_speed_rpm))
        tilt_speed_rpm = int(round(tilt_speed_rpm))
        
        # Limit speeds
        pan_speed_rpm = np.clip(pan_speed_rpm, -self.max_speed_rps, self.max_speed_rps)
        tilt_speed_rpm = np.clip(tilt_speed_rpm, -self.max_speed_rps, self.max_speed_rps)
        
        # Progressive reduction based on error magnitude
        if len(self.error_history) >= 3:
            recent_errors = self.error_history[-3:]
            avg_error = np.mean(recent_errors)
            
            # Progressive reduction thresholds
            if avg_error < 20.0:  # Very close
                reduction_factor = 0.3
            elif avg_error < 40.0:  # Close
                reduction_factor = 0.6
            elif avg_error < 80.0:  # Medium
                reduction_factor = 0.8
            else:  # Far
                reduction_factor = 1.0
                
            pan_speed_rpm *= reduction_factor
            tilt_speed_rpm *= reduction_factor
        
        # Target reached detection
        if error_magnitude < self.deadzone_px:
            self.target_reached.emit()
        
        return (pan_speed_rpm, tilt_speed_rpm)
    
    # Keep the old method name for compatibility
    def calculate_control(self, target_x, target_y, target_width=None, target_height=None):
        """Wrapper for the IBVS calculation."""
        return self.calculate_control_ibvs(target_x, target_y, target_width, target_height)
    
    def update_tracking_target(self, target_id=None):
        """Set the ID of the target to track."""
        with self.tracking_lock:
            self.target_id = target_id
            if self.target_id is not None:
                logger.info(f"🎯 Updated tracking target to balloon ID: {target_id}")
    
    def reset_tracking(self):
        """Reset tracking parameters and clear error history."""
        self.error_history = []
        self.target_depth = 5.0  # Reset depth estimate
        
        # Reset PID terms
        self.error_integral_u = 0.0
        self.error_integral_v = 0.0
        self.error_u_history = np.zeros(self.error_history_length)
        self.error_v_history = np.zeros(self.error_history_length)
        
        logger.info("🔄 Tracking parameters reset")
    
    def get_error_stats(self):
        """Get statistics about the tracking error."""
        if not self.error_history:
            return None
            
        stats = {
            "current_error": self.error_history[-1] if self.error_history else 0,
            "avg_error": np.mean(self.error_history) if self.error_history else 0,
            "min_error": min(self.error_history) if self.error_history else 0,
            "max_error": max(self.error_history) if self.error_history else 0,
            "is_converged": False
        }
        
        # Check convergence
        if len(self.error_history) >= 5:
            recent_errors = self.error_history[-5:]
            if max(recent_errors) - min(recent_errors) < 2.0 and np.mean(recent_errors) < 10.0:
                stats["is_converged"] = True
                
        return stats
    
    def start_tracking(self, target_id=None):
        """Start tracking a balloon."""
        if self.is_tracking:
            self.stop_tracking()
        
        self.reset_tracking()
        self.update_tracking_target(target_id)
        
        self.is_tracking = True
        self.tracking_thread = threading.Thread(target=self._tracking_loop)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        
        logger.info(f"🎯 Started tracking {'balloon ID: ' + str(target_id) if target_id is not None else 'any detected balloon'}")
    
    def stop_tracking(self):
        """Stop tracking."""
        if not self.is_tracking:
            return
            
        self.is_tracking = False
        if self.tracking_thread:
            self.tracking_thread.join(timeout=1.0)
            self.tracking_thread = None
        
        # Stop movement
        self.stop_movement()
        
        logger.info("⏹️ Stopped tracking")
    
    def _tracking_loop(self):
        """Main tracking loop with IBVS control and Kalman integration."""
        logger.info("🎯 IBVS tracking loop started")
        
        loop_count = 0
        last_detection_time = 0
        
        # Control loop timing
        control_sleep_time = self.control_loop_delay  # 100ms for stable control
        
        while self.is_tracking:
            try:
                loop_count += 1
                current_time = time.time()
                
                # Control loop timing
                time.sleep(control_sleep_time)
                
                # Check for detections
                if not hasattr(self, 'balloon_detections') or not self.balloon_detections:
                    continue
                
                # Find target
                target_detection = self._find_target_detection()
                if not target_detection:
                    continue
                
                last_detection_time = current_time
                
                # Extract target position and size
                x, y, w, h = target_detection[:4]
                
                # Hedefin gerçek merkezi (Kalman filter tahmini de bu merkezi hedefler)
                target_x = x + w//2
                target_y = y + h//2
                
                # Kalman filter entegrasyonu burada olabilir
                # Şu an ByteTracker'daki prediction'ları kullanıyoruz
                # İleride Kalman tahmini varsa o da entegre edilebilir
                
                # Calculate error for debug
                error_u_px = target_x - self.cx_px
                error_v_px = target_y - self.cy_px
                
                # Calculate IBVS control
                pan_speed, tilt_speed = self.calculate_control_ibvs(target_x, target_y, w, h)
                
                # Apply control if significant enough
                min_speed = self.min_speed_rps  # Minimum RPM threshold from config
                
                # Debug log (sadece hareket varsa)
                if abs(error_u_px) > 2 or abs(error_v_px) > 2:
                    logger.debug(f"🎯 Tracking: target=({target_x},{target_y}), center=({self.cx_px},{self.cy_px}), error=({error_u_px:.1f},{error_v_px:.1f}), speeds=({pan_speed},{tilt_speed})")
                
                if abs(pan_speed) >= min_speed or abs(tilt_speed) >= min_speed:
                    self.move_to_speeds(pan_speed, tilt_speed)
                else:
                    # Stop movement if within deadzone or speeds too low
                    self.stop_movement()
                    if abs(error_u_px) < self.deadzone_px and abs(error_v_px) < self.deadzone_px:
                        logger.info(f"🎯 TARGET REACHED - In deadzone ({self.deadzone_px} px)")
                
                # Update tracking info signal
                self.tracking_update.emit(int(target_x), int(target_y), int(self.cx_px), int(self.cy_px))
                
                # Periodic cleanup
                if loop_count % 1000 == 0:
                    self._cleanup_tracking_data()
                
            except Exception as e:
                logger.error(f"❌ Error in IBVS tracking loop: {str(e)}")
        
        logger.info("🏁 IBVS tracking loop ended")
    
    def _cleanup_tracking_data(self):
        """Clean up tracking data to prevent memory buildup."""
        try:
            # Limit error history
            if len(self.error_history) > 100:
                self.error_history = self.error_history[-100:]
            
        except Exception as e:
            logger.error(f"❌ Error during tracking data cleanup: {str(e)}")
    
    def _find_target_detection(self):
        """Find target detection with enhanced persistence."""
        with self.tracking_lock:
            if not self.balloon_detections:
                self.target_lost_count += 1
                return None
                
            # If tracking specific ID
            if self.target_id is not None:
                for detection in self.balloon_detections:
                    if len(detection) > 6 and detection[6] == self.target_id:
                        self.target_lost_count = 0
                        x, y, w, h = detection[:4]
                        self.last_known_target_pos = (x + w//2, y + h//2)
                        return detection
                        
                # Target ID not found
                self.target_lost_count += 1
                
                # If lost too many frames, find largest balloon
                if self.target_lost_count > self.max_target_lost_frames:
                    logger.warning(f"⚠️ Target ID {self.target_id} lost, switching to largest balloon")
                    return self._find_largest_balloon()
                    
                return None
            else:
                # No specific target - find largest balloon
                return self._find_largest_balloon()
    
    def _find_largest_balloon(self):
        """Find the largest balloon in detections."""
        if not self.balloon_detections:
            return None
            
        largest_balloon = None
        largest_area = 0
        
        for detection in self.balloon_detections:
            x, y, w, h = detection[:4]
            area = w * h
            if area > largest_area:
                largest_area = area
                largest_balloon = detection
        
        if largest_balloon:
            self.target_lost_count = 0
            
        return largest_balloon
    
    def set_detections(self, detections):
        """Update balloon detections from ByteTracker."""
        with self.tracking_lock:
            self.balloon_detections = detections
    
    def release(self):
        """Release resources."""
        if self.is_tracking:
            self.stop_tracking()
        if self.servo_service:
            self.servo_service.release()
    
    def get_status(self):
        """Get motor system status."""
        servo_status = self.servo_service.get_status() if self.servo_service else {}
        
        return {
            "connected": self.is_connected,
            "tracking": self.is_tracking,
            "target_id": self.target_id,
            "servo_status": servo_status,
            "error_stats": self.get_error_stats()
        } 