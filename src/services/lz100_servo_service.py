#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LZ-100 Servo Motor Control Service
---------------------------------
Service for controlling LZ-100 servo motors with Modbus RTU protocol.
Replaces Arduino-based pan-tilt control with industrial servo motors.
Adapted from Teknofest project for Balon Takip system.
"""

import time
import threading
import math
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from src.utils.logger import logger
from src.utils.config import config

try:
    from pymodbus.client.serial import ModbusSerialClient as ModbusClient
    MODBUS_AVAILABLE = True
except ImportError:
    try:
        from pymodbus.client import ModbusSerialClient as ModbusClient
        MODBUS_AVAILABLE = True
    except ImportError:
        MODBUS_AVAILABLE = False


class LZ100ServoService(QObject):
    """
    LZ-100 Servo Motor Control Service.
    
    Controls two LZ-100 servo motors for pan-tilt mechanism:
    - Pan servo (Slave ID: 1) - controls vertical movement (Y-axis)
    - Tilt servo (Slave ID: 10) - controls horizontal movement (X-axis)
    
    Uses Modbus RTU protocol for communication.
    """
    
    # Signals
    command_sent = pyqtSignal(str)
    connection_status_changed = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        
        if not MODBUS_AVAILABLE:
            logger.error("pymodbus library not available. Install with: pip install pymodbus")
            self.is_connected = False
            return
        
        # Modbus connection parameters from config
        self.modbus_port = config.lz100_modbus_port
        self.modbus_baudrate = config.lz100_modbus_baudrate
        self.modbus_stopbits = config.lz100_modbus_stopbits
        self.modbus_bytesize = config.lz100_modbus_bytesize
        self.modbus_parity = config.lz100_modbus_parity
        self.modbus_timeout = config.lz100_modbus_timeout
        
        self.modbus_client = None
        self.is_connected = False
        
        # Servo slave IDs from config
        self.PAN_SLAVE_ID = config.lz100_pan_slave_id    # Y ekseni (Pan - dikey hareket)
        self.TILT_SLAVE_ID = config.lz100_tilt_slave_id  # X ekseni (Tilt - yatay hareket)
        
        # Current speeds (RPM)
        self.pan_speed = 0
        self.tilt_speed = 0
        
        # Speed limits (RPM) from config
        self.max_speed = config.lz100_max_speed
        self.min_speed = config.lz100_min_speed
        
        # Speed smoothing from config
        self.speed_smoothing = config.lz100_speed_smoothing
        
        # Control parameters from config
        self.deadzone_threshold = config.lz100_deadzone_threshold
        self.speed_scale_factor = config.lz100_speed_scale_factor
        
        # Current positions (estimated)
        self.pan_position = 0   # Merkez = 0
        self.tilt_position = 0  # Merkez = 0
        
        # Movement tracking
        self.last_movement_time = time.time()
        self.movement_timeout = 0.5  # Saniye
        
        # Threading
        self.control_lock = threading.Lock()
        
        logger.info("🎛️ LZ-100 Servo Service initialized")
    
    def to_modbus_16bit(self, val):
        """Signed 16-bit değeri unsigned olarak dönüştür (2's complement)."""
        return val & 0xFFFF
    
    def write_register(self, slave_id, address, value):
        """Register yazma işlemi."""
        if not self.is_connected or not self.modbus_client:
            return False
            
        try:
            value = self.to_modbus_16bit(value)
            
            if not self.modbus_client.connect():
                logger.error("❌ Modbus bağlantısı kurulamadı")
                return False

            result = self.modbus_client.write_register(address=address, value=value, unit=slave_id)
            self.modbus_client.close()

            if result.isError():
                logger.error(f"❌ Yazma Hatası (Slave {slave_id}): {result}")
                return False
            else:
                logger.debug(f"✅ Slave {slave_id} → Register {address} = {value}")
                return True

        except Exception as e:
            logger.error(f"❌ Modbus yazma hatası (Slave {slave_id}): {e}")
            return False
    
    def motor_control(self, slave_id, speed):
        """Motor hız kontrol fonksiyonu."""
        try:
            # Tam sayıya çevir
            original_speed = int(round(speed))
            
            # Motor yönlendirme - Teknofest montajına göre ters çevir
            if slave_id == self.PAN_SLAVE_ID:
                speed = -original_speed  # Pan motor tersine
                motor_name = "PAN"
            elif slave_id == self.TILT_SLAVE_ID:
                speed = -original_speed  # Tilt motor tersine
                motor_name = "TILT"
            else:
                speed = original_speed
                motor_name = "UNKNOWN"
            
            # Hız sınırları
            speed = max(-self.max_speed, min(self.max_speed, speed))
            
            # Çok küçük hızları sıfırla
            if abs(speed) < self.min_speed:
                speed = 0
            
            # Debug log (sadece hareket varsa)
            if abs(original_speed) > 0:
                logger.debug(f"🎛️ Motor {motor_name} (Slave {slave_id}): {original_speed} → {speed} RPM")
            
            return self.write_register(slave_id, 25, speed)  # Register 25: Hız kontrolü
            
        except Exception as e:
            logger.error(f"❌ Motor kontrol hatası: {e}")
            return False
    
    def start_motors(self):
        """Her iki motoru başlat."""
        durum1 = self.write_register(self.PAN_SLAVE_ID, 53, 1)    # Register 53: Start/Stop
        durum2 = self.write_register(self.TILT_SLAVE_ID, 53, 1)
        
        if durum1 and durum2:
            logger.info("✅ LZ-100 servo motorları başlatıldı")
            return True
        else:
            logger.error("❌ LZ-100 servo motorları başlatılamadı")
            return False
    
    def stop_motors(self):
        """Her iki motoru durdur."""
        # Önce hızları sıfırla
        self.motor_control(self.PAN_SLAVE_ID, 0)
        self.motor_control(self.TILT_SLAVE_ID, 0)
        
        # Sonra motorları durdur
        durum1 = self.write_register(self.PAN_SLAVE_ID, 53, 0)
        durum2 = self.write_register(self.TILT_SLAVE_ID, 53, 0)
        
        if durum1 and durum2:
            logger.info("⏹️ LZ-100 servo motorları durduruldu")
            return True
        else:
            logger.error("❌ LZ-100 servo motorları durdurulamadı")
            return False
    
    def connect(self):
        """Modbus bağlantısını kur."""
        if not MODBUS_AVAILABLE:
            logger.error("❌ pymodbus library gerekli")
            return False
            
        if self.is_connected:
            logger.info("🔌 LZ-100 bağlantısı zaten kurulmuş")
            return True
            
        try:
            logger.info(f"🔌 LZ-100 Modbus bağlantısı kuruluyor: {self.modbus_port} ({self.modbus_baudrate} baud)...")
            
            self.modbus_client = ModbusClient(
                method='rtu',
                port=self.modbus_port,
                baudrate=self.modbus_baudrate,
                stopbits=self.modbus_stopbits,
                bytesize=self.modbus_bytesize,
                parity=self.modbus_parity,
                timeout=self.modbus_timeout
            )
            
            # Test bağlantısı
            if self.modbus_client.connect():
                self.modbus_client.close()
                self.is_connected = True
                logger.info(f"✅ LZ-100 Modbus bağlantısı başarılı: {self.modbus_port}")
                
                # Motorları başlat
                if self.start_motors():
                    self.connection_status_changed.emit(True)
                    return True
                else:
                    self.is_connected = False
                    return False
            else:
                logger.error("❌ LZ-100 Modbus test bağlantısı başarısız")
                return False
                
        except Exception as e:
            self.is_connected = False
            logger.error(f"❌ LZ-100 bağlantısında hata: {str(e)}")
            self.connection_status_changed.emit(False)
            return False
    
    def disconnect(self):
        """Modbus bağlantısını kes."""
        try:
            if self.is_connected:
                # Motorları durdur
                self.stop_motors()
                
                if self.modbus_client:
                    self.modbus_client.close()
                    self.modbus_client = None
                
                self.is_connected = False
                logger.info("🔌 LZ-100 bağlantısı kesildi")
                self.connection_status_changed.emit(False)
                return True
        except Exception as e:
            logger.error(f"❌ LZ-100 bağlantısı kesilirken hata: {str(e)}")
            return False
    
    def move_to_speeds(self, pan_speed, tilt_speed):
        """Servo motorları belirtilen hızlarda hareket ettir."""
        if not self.is_connected:
            return False
        
        with self.control_lock:
            # Hız smoothing uygula
            pan_speed = self.pan_speed + (pan_speed - self.pan_speed) * self.speed_smoothing
            tilt_speed = self.tilt_speed + (tilt_speed - self.tilt_speed) * self.speed_smoothing
            
            # TAM SAYI'ya çevir (motor sürücüsü için)
            pan_speed_int = int(round(pan_speed))
            tilt_speed_int = int(round(tilt_speed))
            
            # Çok küçük hızları sıfırla (1 RPM altı)
            if abs(pan_speed_int) < 1:
                pan_speed_int = 0
            if abs(tilt_speed_int) < 1:
                tilt_speed_int = 0
            
            # Güncel hızları sakla (tam sayı)
            self.pan_speed = pan_speed_int
            self.tilt_speed = tilt_speed_int
            
            # Motorları kontrol et
            pan_success = self.motor_control(self.PAN_SLAVE_ID, pan_speed_int)
            tilt_success = self.motor_control(self.TILT_SLAVE_ID, tilt_speed_int)
            
            if pan_success and tilt_success:
                if abs(pan_speed_int) > 0 or abs(tilt_speed_int) > 0:
                    self.command_sent.emit(f"Pan: {pan_speed_int} RPM, Tilt: {tilt_speed_int} RPM")
                self.last_movement_time = time.time()
                return True
            else:
                return False
    
    def stop_movement(self):
        """Hareketi durdur."""
        return self.move_to_speeds(0, 0)
    
    def emergency_stop(self):
        """ACİL DURDURMA - Threading lock'sız direkt motor kontrolü"""
        if not self.is_connected:
            return False
        
        try:
            logger.warning("🚨 LZ100 ACİL DURDURMA - Direkt register yazımı!")
            
            # Direkt motor kontrolü - lock'sız
            pan_success = self.motor_control(self.PAN_SLAVE_ID, 0)
            tilt_success = self.motor_control(self.TILT_SLAVE_ID, 0)
            
            # Hızları sıfırla
            self.pan_speed = 0
            self.tilt_speed = 0
            
            if pan_success and tilt_success:
                logger.warning("⚡ LZ100 ACİL DURDURMA BAŞARILI!")
                return True
            else:
                logger.error("❌ LZ100 ACİL DURDURMA BAŞARISIZ!")
                return False
                
        except Exception as e:
            logger.error(f"❌ LZ100 ACİL DURDURMA HATASI: {e}")
            return False
    
    def calculate_control_speeds(self, target_x, target_y, frame_center_x, frame_center_y):
        """
        Hedef koordinatlarına göre servo hızlarını hesapla.
        
        Args:
            target_x: Hedef x koordinatı
            target_y: Hedef y koordinatı
            frame_center_x: Frame merkez x koordinatı
            frame_center_y: Frame merkez y koordinatı
            
        Returns:
            Tuple of (pan_speed, tilt_speed) in RPM
        """
        # Hata hesapla
        error_x = target_x - frame_center_x  # Yatay hata
        error_y = target_y - frame_center_y  # Dikey hata
        
        # Deadzone uygula
        if abs(error_x) < self.deadzone_threshold:
            error_x = 0
        if abs(error_y) < self.deadzone_threshold:
            error_y = 0
        
        # Hızları hesapla
        # Pan motor (dikey hareket): error_y kullan
        # Negatif çünkü hedef aşağıda ise yukarı hareket etmeli
        pan_speed = -error_y * self.speed_scale_factor
        
        # Tilt motor (yatay hareket): error_x kullan
        # Pozitif çünkü hedef sağda ise sağa hareket etmeli
        tilt_speed = error_x * self.speed_scale_factor
        
        # Hız sınırları
        pan_speed = max(-self.max_speed, min(self.max_speed, pan_speed))
        tilt_speed = max(-self.max_speed, min(self.max_speed, tilt_speed))
        
        return (pan_speed, tilt_speed)
    
    def get_status(self):
        """Servo motor durumunu al."""
        return {
            "connected": self.is_connected,
            "pan_speed": self.pan_speed,
            "tilt_speed": self.tilt_speed,
            "pan_position": self.pan_position,
            "tilt_position": self.tilt_position,
            "last_movement": time.time() - self.last_movement_time
        }
    
    def release(self):
        """Kaynakları serbest bırak."""
        self.disconnect() 