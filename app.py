#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Balon Takip Sistemi - Ana Dosya
-------------------------------
ByteTracker ile balon tracking uygulaması.
Teknofest projesi entegrasyonu ile gelişmiş logging ve config sistemi.
"""

import sys
import os
import time
import traceback

# PYTHONPATH'i otomatik ayarla
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QMessageBox
from src.interfaces.gui import MainWindow
from src.utils.config import config
from src.utils.logger import logger

# Global startup timer
startup_time = time.time()

def log_startup_time(component_name, start_time):
    """Log the startup time for important components only"""
    elapsed = time.time() - start_time
    total_elapsed = time.time() - startup_time
    # Only log significant components (> 0.05s) or always log total
    if elapsed > 0.05 or "tamamlandı" in component_name:
        logger.info(f"⏱️ {component_name}: {elapsed:.2f}s (Toplam: {total_elapsed:.2f}s)")

def global_exception_handler(exctype, value, tb):
    """Global exception handler for unhandled exceptions"""
    error_message = ''.join(traceback.format_exception(exctype, value, tb))
    logger.error(f'Global Exception: {error_message}')
    
    # Show error to user if GUI is available
    try:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle('Beklenmeyen Hata')
        msg.setText('Beklenmeyen bir hata oluştu. Uygulama log dosyasını kontrol edin.')
        msg.setDetailedText(error_message)
        msg.exec_()
    except Exception:
        # If GUI is not available, print to console
        print('Beklenmeyen bir hata oluştu:', error_message)

def main():
    """Main application entry point"""
    # Initialize application
    app_start = time.time()
    app = QApplication(sys.argv)
    app.setApplicationName(config.app_name)
    app.setApplicationVersion(config.app_version)
    log_startup_time("QApplication Başlatma", app_start)
    
    # Ensure required directories exist
    dirs_start = time.time()
    config.ensure_dirs_exist()
    log_startup_time("Dizin Kontrolü", dirs_start)
    
    # Initialize logger (already done via import, but log startup)
    logger_start = time.time()
    logger.info("🚀 Balon Takip Sistemi başlatılıyor...")
    logger.info(f"📷 Kullanılan Kamera ID: {config.camera_id}")
    logger.info(f"🎯 Model Dizini: {config.model_dir}")
    log_startup_time("Logger Servisi", logger_start)
    
    # Create and show main window
    window_start = time.time()
    window = MainWindow()
    window.show()
    log_startup_time("Ana Pencere Oluşturma", window_start)
    
    total_startup = time.time() - startup_time
    logger.info(f"✅ Uygulama başlatma tamamlandı! Toplam süre: {total_startup:.2f} saniye")
    
    # Start application event loop
    try:
        exit_code = app.exec_()
        logger.info("🔚 Uygulama normal şekilde sonlandırıldı")
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"🔥 Uygulama çıkışı sırasında hata: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Set global exception handler
    sys.excepthook = global_exception_handler
    main()
