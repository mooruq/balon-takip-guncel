from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout,
    QLabel, QHBoxLayout, QFrame, QMessageBox, QDoubleSpinBox, QComboBox, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon, QColor
import sys
import os
import cv2
import time
from ultralytics import YOLO

from src.interfaces.video_widget import VideoWidget
from src.interfaces.teknofest_sidebar import LogSidebar, MenuSidebar, IconThemeManager
from src.interfaces.teknofest_camera_view import TeknoFestCameraView
from src.core.controller.main_controller import MainController
from src.utils.config import config
from src.utils.logger import logger


class ModelLoader(QThread):
    """YOLO model'ini arka planda yükleyen thread"""
    model_loaded = pyqtSignal(object)
    progress_update = pyqtSignal(str)
    
    def __init__(self, model_path):
        super().__init__()
        self.model_path = model_path
        
    def run(self):
        try:
            logger.info(f"🤖 Model yükleme başlatıldı: {self.model_path}")
            self.progress_update.emit("Model yükleniyor...")
            model = YOLO(self.model_path)
            self.progress_update.emit("Model hazır!")
            logger.info("✅ Model başarıyla yüklendi")
            self.model_loaded.emit(model)
        except Exception as e:
            error_msg = f"Model yükleme hatası: {e}"
            logger.error(f"❌ {error_msg}")
            self.progress_update.emit(error_msg)
            self.model_loaded.emit(None)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Start timing
        init_start_time = time.time()
        
        # Config'den ayarları al
        self.setWindowTitle(config.app_name)
        self.setGeometry(100, 100, config.window_width, config.window_height)
        
        logger.info(f"🖥️ Ana pencere oluşturuluyor: {config.window_width}x{config.window_height}")
        
        # Set default theme
        self.current_theme = "dark"  # Default to dark theme
        
        # Focus policy ayarı - focus almayı engellemek için
        self.setFocusPolicy(Qt.NoFocus)
        
        # Initialize UI components
        ui_start = time.time()
        self.init_ui()
        self._log_timing("UI Bileşenleri Başlatma", ui_start)

        # Model path'ini config'den al
        self.model_path = config.get_balloon_custom_model_path() or config.get_balloon_model_path()
        logger.info(f"🎯 Kullanılacak model: {self.model_path}")
        
        self.controller = None
        self.is_tracking = False
        self.loaded_model = None  # Preloaded model

        # Initialize controller with Teknofest camera view
        self.controller = MainController(self.camera_view, self)
        
        # Model'i arka planda yükle
        self.start_model_loading()
        
        # Show in fullscreen mode
        show_start = time.time()
        self.showFullScreen()
        self._log_timing("Pencere Gösterme", show_start)
        
        # Log that application has started
        total_init_time = time.time() - init_start_time
        logger.info(f"🏁 Teknofest Ana pencere başlatma tamamlandı: {total_init_time:.2f} saniye")
        
        # Connect logger to sidebar
        logger.log_added.connect(self.log_sidebar.add_log)
        
        QTimer.singleShot(100, self.refresh_camera_list)

    def _log_timing(self, component_name, start_time):
        """Log timing for important components only"""
        elapsed = time.time() - start_time
        # Only log significant components (> 0.05s) or always log total
        if elapsed > 0.05 or "tamamlandı" in component_name:
            logger.info(f"⏱️ {component_name}: {elapsed:.2f}s")

    def init_ui(self):
        """Initialize the fixed-layout user interface components."""
        # Set window properties
        self.setWindowTitle(config.app_name)
        
        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout - horizontal with 3 fixed sections
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create left sidebar (Log Window) with fixed 10% width
        self.log_sidebar = LogSidebar(self)
        
        # Create Teknofest camera view for center area (80% width)
        self.camera_view = TeknoFestCameraView()
        # Set camera view to 'fit' mode to maintain aspect ratio with letterboxing
        self.camera_view.set_scale_mode("fit")
        
        # Create right sidebar (Menu) with fixed 10% width  
        self.menu_sidebar = MenuSidebar(self)
        
        # Connect menu button signals
        self.menu_sidebar.theme_button.clicked.connect(self.toggle_theme)
        self.menu_sidebar.exit_button.clicked.connect(self.on_exit_clicked)
        self.menu_sidebar.emergency_stop_button.clicked.connect(self.on_emergency_stop_clicked)
        self.menu_sidebar.balloon_tracking_button.clicked.connect(self.on_balloon_tracking_clicked)
        
        # Connect motor control button signals
        self.menu_sidebar.motor_connect_button.clicked.connect(self.on_motor_connect_clicked)
        self.menu_sidebar.motor_tracking_button.clicked.connect(self.on_motor_tracking_clicked)
        
        # Add widgets to main layout with stretch factors
        # Left sidebar: 10% width
        self.main_layout.addWidget(self.log_sidebar, 1)  
        
        # Camera view: 80% width  
        self.main_layout.addWidget(self.camera_view, 8)
        
        # Right sidebar: 10% width
        self.main_layout.addWidget(self.menu_sidebar, 1)
        
        # Apply the default theme
        self.apply_theme()

    def start_model_loading(self):
        """YOLO model'ini arka planda yükle"""
        self.model_loader = ModelLoader(self.model_path)
        self.model_loader.model_loaded.connect(self.on_model_loaded)
        self.model_loader.progress_update.connect(self.update_status_loading)
        self.model_loader.start()
        
        # Loading durumunu göster
        self.menu_sidebar.balloon_tracking_button.setEnabled(False)
        self.menu_sidebar.balloon_tracking_button.setText("Model Yükleniyor...")
        
    def on_model_loaded(self, model):
        """Model yüklendiğinde çalışır"""
        self.loaded_model = model
        if model:
            self.menu_sidebar.balloon_tracking_button.setEnabled(True)
            self.menu_sidebar.balloon_tracking_button.setText("Balon Takip Modu\n(ByteTracker AI)")
            self.camera_view.show_message("Model Hazır - Balon Takip Başlatılabilir", QColor(76, 175, 80), 2000)
        else:
            self.menu_sidebar.balloon_tracking_button.setEnabled(False)
            self.menu_sidebar.balloon_tracking_button.setText("Model Hatası")
            self.camera_view.show_message("Model Yüklenemedi", QColor(231, 76, 60), 3000)
    
    def update_status_loading(self, message):
        """Model yükleme durumunu göster"""
        self.camera_view.show_message(message, QColor(255, 193, 7), 1000)

    def apply_theme(self):
        """Apply the current theme to the application."""
        if self.current_theme == "dark":
            self.apply_dark_theme()
        else:
            self.apply_light_theme()
    
    def apply_dark_theme(self):
        """Apply dark theme (night mode)."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QWidget {
                background-color: #121212;
                color: white;
            }
            QPushButton {
                background-color: #333333;
                color: white;
                border-radius: 5px;
                padding: 5px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:pressed {
                background-color: #555555;
            }
        """)
        
        # Set the camera view background color
        self.camera_view.setStyleSheet("background-color: #121212;")
        
        # Set sidebar backgrounds
        self.log_sidebar.setStyleSheet("background-color: #333333;")
        self.menu_sidebar.setStyleSheet("background-color: #333333;")
        
        # Update sidebar themes
        if hasattr(self.log_sidebar, 'update_text_area_style'):
            self.log_sidebar.update_text_area_style(is_dark=True)
        
        if hasattr(self.menu_sidebar, 'update_theme'):
            self.menu_sidebar.update_theme(is_dark=True)
        
        logger.info("🌙 Koyu temaya geçildi")
        self.current_theme = "dark"
    
    def apply_light_theme(self):
        """Apply light theme."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QWidget {
                background-color: #f0f0f0;
                color: black;
            }
            QPushButton {
                background-color: #e0e0e0;
                color: black;
                border-radius: 5px;
                padding: 5px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
        """)
        
        # Set the camera view background color
        self.camera_view.setStyleSheet("background-color: #F5F5F5;")
        
        # Set sidebar backgrounds
        self.log_sidebar.setStyleSheet("background-color: #E0E0E0;")
        self.menu_sidebar.setStyleSheet("background-color: #E0E0E0;")
        
        # Update sidebar themes
        if hasattr(self.log_sidebar, 'update_text_area_style'):
            self.log_sidebar.update_text_area_style(is_dark=False)
        
        if hasattr(self.menu_sidebar, 'update_theme'):
            self.menu_sidebar.update_theme(is_dark=False)
        
        logger.info("☀️ Açık temaya geçildi")
        self.current_theme = "light"
    
    def toggle_theme(self):
        """Toggle between dark and light themes."""
        if self.current_theme == "dark":
            self.apply_light_theme()
        else:
            self.apply_dark_theme()
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def on_exit_clicked(self):
        """Handle exit button click."""
        logger.info("🚪 Çıkış butonu tıklandı")
        self.close()
    
    def on_emergency_stop_clicked(self):
        """Handle emergency stop button click."""
        logger.warning("🚨 ACİL STOP butonuna basıldı!")
        
        # 🚨 1. ÖNCELİK: MOTORLARI ACIL DURDUR
        if self.controller:
            logger.warning("🚨 ACİL MOTOR DURDURMA - İLK ÖNCELİK!")
            self.controller.emergency_stop_motors()
        
        # 2. Video tracking'i durdur  
        if self.controller:
            self.controller.stop_video()
        
        # 3. UI'ı güncelle
        self.camera_view.show_emergency_stop()
        
        # 4. Tüm butonları devre dışı bırak
        self.menu_sidebar.balloon_tracking_button.setEnabled(False)
        self.menu_sidebar.balloon_tracking_button.setText("ACİL STOP ETKİN")
        
        # 5. Motor butonlarını devre dışı bırak
        self.menu_sidebar.motor_connect_button.setEnabled(False)
        self.menu_sidebar.motor_tracking_button.setEnabled(False)
        self.menu_sidebar.motor_tracking_button.setChecked(False)
        
        # 6. Son olarak uyarı mesajı
        QMessageBox.critical(self, "ACİL STOP", 
                            "🚨 ACİL DURDURMA AKTİF! 🚨\n\n" +
                            "1. Motorlar acil durduruldu\n" +
                            "2. Tüm tracking işlemleri sonlandırıldı\n" +
                            "3. Sistem güvenli moda alındı\n\n" +
                            "Yeniden başlatmak için uygulamayı kapatıp açın.")
    
    def on_balloon_tracking_clicked(self):
        """Handle balloon tracking button click."""
        if not self.loaded_model:
            self.camera_view.show_message("Model henüz yüklenmedi!", QColor(231, 76, 60), 2000)
            return
        
        if self.menu_sidebar.balloon_tracking_button.isChecked():
            self.start_balloon_tracking()
        else:
            self.stop_balloon_tracking()

    def refresh_camera_list(self, max_devices=3):
        logger.info("📷 Kamera listesi yenileniyor")
        
        # Create temporary camera list for selection
        self.available_cameras = []
        camera_count = 0
        
        for i in range(max_devices):
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        self.available_cameras.append(i)
                        camera_count += 1
                        logger.info(f"✅ Kamera {i} bulundu")
                    cap.release()
            except Exception as e:
                logger.debug(f"Kamera {i} kontrol hatası: {e}")
        
        if camera_count == 0:
            logger.warning("❌ Hiç kamera bulunamadı")
            self.camera_view.show_message("Kamera bulunamadı", QColor(231, 76, 60), 3000)
        else:
            logger.info(f"📷 Toplam {camera_count} kamera bulundu")
            self.camera_view.show_message(f"Hazır - {camera_count} kamera bulundu", QColor(76, 175, 80), 2000)
    
    def start_balloon_tracking(self):
        """Start balloon tracking with the first available camera."""
        if not self.available_cameras:
            self.camera_view.show_message("Kamera bulunamadı!", QColor(231, 76, 60), 3000)
            self.menu_sidebar.balloon_tracking_button.setChecked(False)
            return

        source = self.available_cameras[0]  # Use first available camera
        confidence = config.confidence_threshold
        
        logger.info(f"🎥 Balon tracking başlatılıyor - Kamera ID: {source}, Confidence: {confidence}")
        
        # Set camera view to active
        self.camera_view.set_detection_active(True)
        self.camera_view.set_detection_mode("balon_tracking")
        self.camera_view.show_message("Balon Takip Başlatılıyor...", QColor(33, 150, 243), 2000)
        
        # Start tracking with preloaded model
        self.controller.start_video_with_model(
            source, self.loaded_model, "bytetrack", confidence
        )
        
        self.is_tracking = True
    
    def stop_balloon_tracking(self):
        """Stop balloon tracking."""
        logger.info("⏹️ Balon tracking durduruluyor")
        
        if self.controller:
            self.controller.stop_video()

        # Reset camera view
        self.camera_view.set_detection_active(False)
        self.camera_view.show_message("Balon Takip Durduruldu", QColor(255, 193, 7), 2000)
        
        self.is_tracking = False
    
    def on_motor_connect_clicked(self):
        """Handle motor connect button click."""
        if not self.controller:
            self.camera_view.show_message("Controller hazır değil!", QColor(231, 76, 60), 2000)
            return
            
        # Check current motor status
        motor_status = self.controller.get_motor_status()
        
        if motor_status.get("connected", False):
            # Already connected - disconnect
            logger.info("🔌 Motor bağlantısı kesiliyor...")
            self.camera_view.show_message("Motor Bağlantısı Kesiliyor...", QColor(255, 193, 7), 1000)
            
            if self.controller.disconnect_motors():
                self.menu_sidebar.motor_connect_button.setText("🔌 Motor Bağlan")
                self.menu_sidebar.motor_connect_button.setStyleSheet("""
                    QPushButton {
                        background-color: #27ae60;
                        color: white;
                        font-weight: bold;
                        font-size: 12px;
                        border: none;
                        border-radius: 8px;
                        padding: 8px;
                        margin: 2px;
                    }
                    QPushButton:hover {
                        background-color: #2ecc71;
                    }
                """)
                self.menu_sidebar.motor_tracking_button.setEnabled(False)
                self.menu_sidebar.motor_tracking_button.setChecked(False)
                self.camera_view.show_message("Motor Bağlantısı Kesildi", QColor(255, 193, 7), 2000)
            else:
                self.camera_view.show_message("Motor Bağlantısı Kesilemedi!", QColor(231, 76, 60), 2000)
        else:
            # Not connected - connect
            logger.info("🔌 Motor bağlantısı kuruluyor...")
            self.camera_view.show_message("Motorlara Bağlanılıyor...", QColor(33, 150, 243), 1000)
            
            if self.controller.connect_motors():
                self.menu_sidebar.motor_connect_button.setText("🔌 Motor Ayrıl")
                self.menu_sidebar.motor_connect_button.setStyleSheet("""
                    QPushButton {
                        background-color: #e67e22;
                        color: white;
                        font-weight: bold;
                        font-size: 12px;
                        border: none;
                        border-radius: 8px;
                        padding: 8px;
                        margin: 2px;
                    }
                    QPushButton:hover {
                        background-color: #d35400;
                    }
                """)
                self.menu_sidebar.motor_tracking_button.setEnabled(True)
                self.camera_view.show_message("Motor Sistemi Bağlandı!", QColor(76, 175, 80), 2000)
            else:
                self.camera_view.show_message("Motor Bağlantısı Başarısız!", QColor(231, 76, 60), 2000)
    
    def on_motor_tracking_clicked(self):
        """Handle motor tracking button click."""
        if not self.controller:
            self.camera_view.show_message("Controller hazır değil!", QColor(231, 76, 60), 2000)
            return
            
        # Check if motors are connected
        motor_status = self.controller.get_motor_status()
        if not motor_status.get("connected", False):
            self.camera_view.show_message("Önce motorları bağlayın!", QColor(231, 76, 60), 2000)
            self.menu_sidebar.motor_tracking_button.setChecked(False)
            return
        
        if self.menu_sidebar.motor_tracking_button.isChecked():
            # Start motor tracking
            logger.info("🎯 Motor tracking başlatılıyor...")
            self.camera_view.show_message("Motor Tracking Başlatılıyor...", QColor(33, 150, 243), 1000)
            
            if self.controller.start_motor_tracking():
                self.camera_view.show_message("Motor Tracking Aktif!", QColor(76, 175, 80), 2000)
            else:
                self.camera_view.show_message("Motor Tracking Başlatılamadı!", QColor(231, 76, 60), 2000)
                self.menu_sidebar.motor_tracking_button.setChecked(False)
        else:
            # Stop motor tracking
            logger.info("⏹️ Motor tracking durduruluyor...")
            self.camera_view.show_message("Motor Tracking Durduruluyor...", QColor(255, 193, 7), 1000)
            
            if self.controller.stop_motor_tracking():
                self.camera_view.show_message("Motor Tracking Durduruldu", QColor(255, 193, 7), 2000)
            else:
                self.camera_view.show_message("Motor Tracking Durdurulamadı!", QColor(231, 76, 60), 2000)

    def closeEvent(self, event):
        logger.info("🚪 Uygulama kapatılıyor")
        if hasattr(self, 'controller'):
            self.controller.stop_video()
        event.accept()

    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key_Escape:
            # ESC key to exit fullscreen
            if self.isFullScreen():
                self.showNormal()
        elif event.key() == Qt.Key_F11:
            # F11 to toggle fullscreen
            self.toggle_fullscreen()
        elif event.key() == Qt.Key_T:
            # T key to toggle theme
            self.toggle_theme()
        super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
