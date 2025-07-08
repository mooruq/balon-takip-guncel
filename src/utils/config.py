#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration Utilities
---------------------
Configuration settings for the application.
Integrated from Teknofest project with advanced features.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Proje kök dizini
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# src dizini
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# .env dosyasını proje kök dizininde yükle
env_path = Path(ROOT_DIR) / '.env'
load_dotenv(dotenv_path=env_path)

# Alt dizinleri tanımla
DEFAULT_DATA_DIR = os.path.join(ROOT_DIR, 'data')
DEFAULT_MODELS_DIR = os.path.join(ROOT_DIR, 'models')

class Config:
    """
    Configuration settings for the application.
    Implements the Singleton pattern.
    """
    # Singleton instance
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize default configuration."""
        # Application settings
        self.app_name = "Balon Takip Sistemi"
        self.app_version = "2.0.0"
        
        # Camera settings
        self.camera_id = int(os.getenv('CAMERA_ID', 0))
        self.camera_fps = int(os.getenv('CAMERA_FPS', 30))
        self.camera_width = int(os.getenv('CAMERA_WIDTH', 640))
        self.camera_height = int(os.getenv('CAMERA_HEIGHT', 480))
        self.save_format = os.getenv('SAVE_FORMAT', 'JPEG')
        
        # Camera additional options
        self.auto_exposure = os.getenv('AUTO_EXPOSURE', 'True').lower() in ('true', '1', 't')
        self.auto_white_balance = os.getenv('AUTO_WHITE_BALANCE', 'True').lower() in ('true', '1', 't')
        
        # Kamera hızlı başlatma ayarları
        self.use_directshow_backend = os.getenv('USE_DIRECTSHOW_BACKEND', 'True').lower() in ('true', '1', 't')
        self.camera_buffer_size = int(os.getenv('CAMERA_BUFFER_SIZE', 1))
        self.disable_auto_settings_on_startup = os.getenv('DISABLE_AUTO_SETTINGS_ON_STARTUP', 'True').lower() in ('true', '1', 't')
        
        # FPS optimizasyonu
        self.force_fps_setting = os.getenv('FORCE_FPS_SETTING', 'True').lower() in ('true', '1', 't')
        self.camera_fourcc = os.getenv('CAMERA_FOURCC', 'MJPG')
        self.reduce_processing_delay = os.getenv('REDUCE_PROCESSING_DELAY', 'True').lower() in ('true', '1', 't')
        
        # Kamera başlatma timeout ayarları
        self.camera_init_timeout_seconds = float(os.getenv('CAMERA_INIT_TIMEOUT_SECONDS', 30.0))
        self.camera_open_check_timeout_seconds = float(os.getenv('CAMERA_OPEN_CHECK_TIMEOUT_SECONDS', 10.0))
        
        # Camera intrinsic parameters (for tracking calculations)
        self.camera_fx = float(os.getenv('CAMERA_FX', 500.0))  # Focal length X (pixels)
        self.camera_fy = float(os.getenv('CAMERA_FY', 500.0))  # Focal length Y (pixels) 
        self.camera_cx = float(os.getenv('CAMERA_CX', 320.0))  # Principal point X (pixels)
        self.camera_cy = float(os.getenv('CAMERA_CY', 240.0))  # Principal point Y (pixels)
        
        # Pixel size (meters/pixel)
        self.pixel_size_x = float(os.getenv('PIXEL_SIZE_X', 4.8e-6))  # meters/pixel
        self.pixel_size_y = float(os.getenv('PIXEL_SIZE_Y', 4.8e-6))  # meters/pixel
        
        # Focal length in meters
        self.focal_length_m = float(os.getenv('FOCAL_LENGTH_M', 0.0024))  # meters
        
        # UI settings
        self.theme = "light"
        self.window_width = int(os.getenv('WINDOW_WIDTH', 1400))
        self.window_height = int(os.getenv('WINDOW_HEIGHT', 800))
        
        # Yol ayarları
        self.data_dir = DEFAULT_DATA_DIR
        
        # Alt dizinler
        self.logs_dir = os.path.join(self.data_dir, 'logs')
        self.captures_dir = os.path.join(self.data_dir, 'captures')
        
        # Model dizini ve model dosyaları 
        self.model_dir = os.getenv('MODEL_DIR', DEFAULT_MODELS_DIR)
        
        # Model dosya adları
        self.balloon_model = os.getenv('BALLOON_MODEL', 'yolov8n.pt')
        self.balloon_model_custom = os.getenv('BALLOON_MODEL_CUSTOM', 'bests_balloon_30_dark.pt')
        
        # ByteTracker ayarları
        self.track_thresh = float(os.getenv('TRACK_THRESH', 0.5))
        self.track_buffer = int(os.getenv('TRACK_BUFFER', 30))
        self.match_thresh = float(os.getenv('MATCH_THRESH', 0.8))
        self.frame_rate = int(os.getenv('FRAME_RATE', 30))
        
        # Performance optimization settings
        self.enable_periodic_cleanup = os.getenv('ENABLE_PERIODIC_CLEANUP', 'True').lower() in ('true', '1', 't')
        self.cleanup_interval_frames = int(os.getenv('CLEANUP_INTERVAL_FRAMES', 100))
        self.gpu_cache_clear_interval = int(os.getenv('GPU_CACHE_CLEAR_INTERVAL', 50))
        self.max_frame_history = int(os.getenv('MAX_FRAME_HISTORY', 100))
        self.max_track_history = int(os.getenv('MAX_TRACK_HISTORY', 10))
        self.track_timeout_seconds = float(os.getenv('TRACK_TIMEOUT_SECONDS', 0.5))
        self.force_gc_interval = int(os.getenv('FORCE_GC_INTERVAL', 500))
        
        # Adaptive performance settings
        self.adaptive_tracking_sleep = os.getenv('ADAPTIVE_TRACKING_SLEEP', 'True').lower() in ('true', '1', 't')
        self.min_tracking_sleep_ms = float(os.getenv('MIN_TRACKING_SLEEP_MS', 5.0))
        self.max_tracking_sleep_ms = float(os.getenv('MAX_TRACKING_SLEEP_MS', 50.0))
        
        # Memory management settings
        self.enable_aggressive_cleanup = os.getenv('ENABLE_AGGRESSIVE_CLEANUP', 'True').lower() in ('true', '1', 't')
        self.max_error_history = int(os.getenv('MAX_ERROR_HISTORY', 100))
        self.max_timestamp_age_seconds = float(os.getenv('MAX_TIMESTAMP_AGE_SECONDS', 10.0))
        
        # Detection confidence
        self.confidence_threshold = float(os.getenv('CONFIDENCE_THRESHOLD', 0.25))
        
        # GPU usage
        self.use_gpu = os.getenv('USE_GPU', 'True').lower() in ('true', '1', 't')
        
        # LZ-100 Servo Motor Ayarları
        self.lz100_modbus_port = os.getenv('LZ100_MODBUS_PORT', 'COM3')
        self.lz100_modbus_baudrate = int(os.getenv('LZ100_MODBUS_BAUDRATE', 9600))
        self.lz100_modbus_stopbits = int(os.getenv('LZ100_MODBUS_STOPBITS', 2))
        self.lz100_modbus_bytesize = int(os.getenv('LZ100_MODBUS_BYTESIZE', 8))
        self.lz100_modbus_parity = os.getenv('LZ100_MODBUS_PARITY', 'N')
        self.lz100_modbus_timeout = float(os.getenv('LZ100_MODBUS_TIMEOUT', 1.0))
        
        # Servo Motor Slave ID'leri
        self.lz100_pan_slave_id = int(os.getenv('LZ100_PAN_SLAVE_ID', 1))
        self.lz100_tilt_slave_id = int(os.getenv('LZ100_TILT_SLAVE_ID', 10))
        
        # Hız Sınırları (RPM)
        self.lz100_max_speed = int(os.getenv('LZ100_MAX_SPEED', 10))
        self.lz100_min_speed = int(os.getenv('LZ100_MIN_SPEED', 1))
        
        # Kontrol Parametreleri
        self.lz100_speed_scale_factor = float(os.getenv('LZ100_SPEED_SCALE_FACTOR', 2.0))
        self.lz100_deadzone_threshold = float(os.getenv('LZ100_DEADZONE_THRESHOLD', 8.0))
        self.lz100_speed_smoothing = float(os.getenv('LZ100_SPEED_SMOOTHING', 0.7))
        
        # IBVS Kontrol Gains
        self.ibvs_pan_gain = float(os.getenv('IBVS_PAN_GAIN', 0.3))
        self.ibvs_tilt_gain = float(os.getenv('IBVS_TILT_GAIN', 0.3))
        self.ibvs_pan_integral = float(os.getenv('IBVS_PAN_INTEGRAL', 0.05))
        self.ibvs_tilt_integral = float(os.getenv('IBVS_TILT_INTEGRAL', 0.05))
        self.ibvs_pan_derivative = float(os.getenv('IBVS_PAN_DERIVATIVE', 0.1))
        self.ibvs_tilt_derivative = float(os.getenv('IBVS_TILT_DERIVATIVE', 0.1))
    
    def get(self, key, default=None):
        """Get a configuration value."""
        return getattr(self, key, default)
    
    def set(self, key, value):
        """Set a configuration value."""
        setattr(self, key, value)
    
    def ensure_dirs_exist(self):
        """Ensure that all required directories exist."""
        # Ana veri dizinini oluştur
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Alt dizinleri oluştur
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.captures_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)
        
        return True
        
    def get_model_dir(self):
        """Get the model directory"""
        if not os.path.exists(self.model_dir):
            print(f"Warning: Model directory {self.model_dir} not found. Using default: {DEFAULT_MODELS_DIR}")
            return DEFAULT_MODELS_DIR
        return self.model_dir
    
    def get_model_path(self, model_name):
        """Get the full path of a model file."""
        model_dir = self.get_model_dir()
        model_path = os.path.join(model_dir, model_name)
        
        # If model doesn't exist, look for it in the default directory
        if not os.path.exists(model_path):
            default_path = os.path.join(DEFAULT_MODELS_DIR, model_name)
            if os.path.exists(default_path):
                return default_path
            else:
                print(f"Warning: Model {model_name} not found in {model_dir} or {DEFAULT_MODELS_DIR}")
                return None
        
        return model_path
    
    def get_balloon_model_path(self):
        """Get path to balloon detection model."""
        return self.get_model_path(self.balloon_model)
    
    def get_balloon_custom_model_path(self):
        """Get path to custom balloon detection model."""
        return self.get_model_path(self.balloon_model_custom)
    
    def load_camera_calibration(self, calibration_file=None):
        """
        Load camera calibration parameters from file.
        
        Args:
            calibration_file: Path to calibration file (.json or .npz)
                             If None, looks for latest calibration in data directory
        """
        import json
        import numpy as np
        from glob import glob
        
        if calibration_file is None:
            # Look for latest calibration file in data directory
            search_dirs = [self.data_dir, ROOT_DIR]
            all_files = []
            
            for search_dir in search_dirs:
                json_files = glob(os.path.join(search_dir, "*calibration*.json"))
                npz_files = glob(os.path.join(search_dir, "*calibration*.npz"))
                all_files.extend(json_files + npz_files)
            
            if not all_files:
                print("No calibration files found")
                return False
                
            # Get the most recent file
            calibration_file = max(all_files, key=os.path.getmtime)
            print(f"Using calibration file: {calibration_file}")
        
        try:
            if calibration_file.endswith('.json'):
                # Load JSON calibration
                with open(calibration_file, 'r') as f:
                    cal_data = json.load(f)
                
                self.camera_fx = cal_data['fx']
                self.camera_fy = cal_data['fy'] 
                self.camera_cx = cal_data['cx']
                self.camera_cy = cal_data['cy']
                
                # Calculate focal length in meters
                self.focal_length_m = self.camera_fx * self.pixel_size_x
                
                print(f"✓ Camera calibration loaded from JSON:")
                print(f"  fx: {self.camera_fx:.3f} px")
                print(f"  fy: {self.camera_fy:.3f} px") 
                print(f"  cx: {self.camera_cx:.3f} px")
                print(f"  cy: {self.camera_cy:.3f} px")
                print(f"  focal length: {self.focal_length_m:.6f} m")
                
            elif calibration_file.endswith('.npz'):
                # Load NumPy calibration
                cal_data = np.load(calibration_file)
                camera_matrix = cal_data['camera_matrix']
                
                self.camera_fx = float(camera_matrix[0, 0])
                self.camera_fy = float(camera_matrix[1, 1])
                self.camera_cx = float(camera_matrix[0, 2]) 
                self.camera_cy = float(camera_matrix[1, 2])
                
                # Calculate focal length in meters
                self.focal_length_m = self.camera_fx * self.pixel_size_x
                
                print(f"✓ Camera calibration loaded from NPZ:")
                print(f"  fx: {self.camera_fx:.3f} px")
                print(f"  fy: {self.camera_fy:.3f} px")
                print(f"  cx: {self.camera_cx:.3f} px") 
                print(f"  cy: {self.camera_cy:.3f} px")
                print(f"  focal length: {self.focal_length_m:.6f} m")
                
            return True
            
        except Exception as e:
            print(f"Error loading calibration file: {e}")
            return False

# Create a singleton instance for easy import
config = Config() 