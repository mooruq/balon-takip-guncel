import threading

from src.core.trackers.bytetrack_tracker import run_bytetrack_tracking, stop_bytetrack_tracking, run_bytetrack_with_model
from src.services.motor_pan_tilt_service import MotorPanTiltService
from src.utils.config import config
from src.utils.logger import logger


class MainController:
    def __init__(self, video_display, gui_reference=None):
        self.video_display = video_display
        self.running_thread = None
        self.current_algorithm = "bytetrack"  # Artık sadece temizlenmiş ByteTrack+
        self.gui = gui_reference
        
        # Motor kontrol sistemi
        self.motor_controller = MotorPanTiltService()
        self.motor_enabled = False
        
        # Kamera frame boyutlarını motor sistemine bildir
        self.motor_controller.set_frame_center(config.camera_width, config.camera_height)
        
        logger.info("🎮 MainController başlatıldı - ByteTrack+ algoritması + LZ100 Motor Kontrol")

    def start_video(self, source, model_path, algorithm="bytetrack", confidence_threshold=0.5):
        logger.info(f"▶️ Video tracking başlatılıyor - Kaynak: {source}, Model: {model_path}, Confidence: {confidence_threshold}")
        self.stop_video()
        
        # Artık sadece temizlenmiş ByteTracker kullanıyoruz
        self.current_algorithm = "bytetrack"
        def run():
            run_bytetrack_tracking(source, model_path, self.video_display, confidence_threshold)

        self.running_thread = threading.Thread(target=run)
        self.running_thread.daemon = True
        self.running_thread.start()

    def start_video_with_model(self, source, loaded_model, algorithm="bytetrack", confidence_threshold=0.5):
        """Preloaded model ile hızlı başlatma"""
        logger.info(f"⚡ Hızlı tracking başlatılıyor - Kaynak: {source}, Confidence: {confidence_threshold}")
        self.stop_video()
        
        self.current_algorithm = "bytetrack"
        def run():
            # Motor controller'ı motor enabled ise geç
            motor_ctrl = self.motor_controller if self.motor_enabled else None
            run_bytetrack_with_model(source, loaded_model, self.video_display, confidence_threshold, motor_ctrl)

        self.running_thread = threading.Thread(target=run)
        self.running_thread.daemon = True
        self.running_thread.start()

    def stop_video(self):
        logger.info("⏹️ Video tracking durduruluyor")
        
        # Temizlenmiş ByteTracker'ı durdur
        stop_bytetrack_tracking()

        if self.running_thread and self.running_thread.is_alive():
            self.running_thread.join(timeout=2.0)

        self.running_thread = None
        self.current_algorithm = None
    
    # Motor Control Methods
    def connect_motors(self):
        """LZ-100 servo motorlarına bağlan"""
        try:
            if self.motor_controller.connect():
                self.motor_enabled = True
                logger.info("✅ Motor sistemi bağlandı ve aktif edildi")
                return True
            else:
                logger.error("❌ Motor sistemi bağlanamadı")
                return False
        except Exception as e:
            logger.error(f"❌ Motor bağlantı hatası: {e}")
            return False
    
    def disconnect_motors(self):
        """LZ-100 servo motorlarından ayrıl"""
        try:
            self.motor_enabled = False
            if self.motor_controller.disconnect():
                logger.info("🔌 Motor sistemi bağlantısı kesildi")
                return True
            else:
                logger.error("❌ Motor sistemi bağlantısı kesilemedi")
                return False
        except Exception as e:
            logger.error(f"❌ Motor bağlantı kesme hatası: {e}")
            return False
    
    def start_motor_tracking(self, target_id=None):
        """Motor tracking başlat"""
        if not self.motor_enabled:
            logger.warning("⚠️ Motor sistemi bağlı değil")
            return False
        
        try:
            self.motor_controller.start_tracking(target_id)
            logger.info(f"🎯 Motor tracking başlatıldı - Target ID: {target_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Motor tracking başlatma hatası: {e}")
            return False
    
    def stop_motor_tracking(self):
        """Motor tracking durdur"""
        try:
            self.motor_controller.stop_tracking()
            logger.info("⏹️ Motor tracking durduruldu")
            return True
        except Exception as e:
            logger.error(f"❌ Motor tracking durdurma hatası: {e}")
            return False
    
    def get_motor_status(self):
        """Motor sistemi durumunu al"""
        if not self.motor_controller:
            return {"enabled": False, "connected": False}
        
        status = self.motor_controller.get_status()
        status["enabled"] = self.motor_enabled
        return status
    
    def emergency_stop_motors(self):
        """Acil motor durdurma - ANINDA hareket durdur"""
        try:
            logger.warning("🚨 ACİL MOTOR DURDURMA - ANINDA!")
            
            # 1. ÖNCELİK: Motor hareketi ANINDA durdur
            if self.motor_controller:
                self.motor_controller.emergency_stop()  # ACİL DURDURMA - Lock'sız direkt kontrol
                logger.warning("⚡ Motor hareketi anında durduruldu!")
            
            # 2. Tracking thread'ini sonlandır
            self.stop_motor_tracking()
            
            # 3. Motor sistemini devre dışı bırak
            self.motor_enabled = False
            
            logger.warning("🚨 ACİL MOTOR DURDURMA TAMAMLANDI!")
            return True
        except Exception as e:
            logger.error(f"❌ Acil durdurma hatası: {e}")
            return False
