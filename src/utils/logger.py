#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logger Service
-------------
Singleton service for logging application events.
Integrated from Teknofest project with thread-safe logging.
"""

import os
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QMutex
from .config import config

class LoggerService(QObject):
    """
    Singleton Logger Service for application-wide logging.
    Implements the Singleton pattern with thread-safe operations.
    """
    # Singleton instance
    _instance = None
    
    # Signal emitted when a new log message is added
    log_added = pyqtSignal(str)
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the logger service."""
        super().__init__()
        self.logs = []
        self.log_file = None
        self.mutex = QMutex()  # Thread safety
        
        # Logs dizinini config'den al
        logs_dir = config.logs_dir
        
        # Create logs directory if it doesn't exist
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(logs_dir, f"balon_takip_log_{timestamp}.txt")
        
        # Write header to log file
        with open(self.log_file, "w", encoding='utf-8') as f:
            f.write(f"=== Balon Takip Sistemi Log - Started at {timestamp} ===\n\n")
    
    def _format_message(self, level, message):
        """Format a log message with timestamp and level."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"{timestamp} [{level}]: {message}"
    
    def _write_to_file(self, formatted_message):
        """Write a log message to the log file."""
        try:
            with open(self.log_file, "a", encoding='utf-8') as f:
                f.write(formatted_message + "\n")
        except Exception as e:
            # If we can't write to the file, print to console at least
            print(f"Error writing to log file: {e}")
            print(formatted_message)
    
    def log(self, level, message):
        """Log a message with the specified level."""
        # Use mutex to ensure thread safety
        self.mutex.lock()
        
        try:
            formatted_message = self._format_message(level, message)
            self.logs.append(formatted_message)
            self._write_to_file(formatted_message)
            
            # Emit the signal after we've done all the processing
            self.log_added.emit(formatted_message)
            
            return formatted_message
        finally:
            self.mutex.unlock()
    
    def info(self, message):
        """Log an info message."""
        return self.log("INFO", message)
    
    def warning(self, message):
        """Log a warning message."""
        return self.log("WARNING", message)
    
    def error(self, message):
        """Log an error message."""
        return self.log("ERROR", message)
    
    def debug(self, message):
        """Log a debug message."""
        return self.log("DEBUG", message)
    
    def clear(self):
        """Clear the in-memory logs."""
        self.mutex.lock()
        try:
            # Önce logları temizle
            self.logs = []
            
            # "Logs cleared" mesajını oluştur ve yeni listeye ekle
            cleared_message = self._format_message("INFO", "Loglar temizlendi")
            self.logs.append(cleared_message)
            self._write_to_file(cleared_message)
            
            # Sinyal gönder
            self.log_added.emit(cleared_message)
        finally:
            self.mutex.unlock()
        
    def get_logs(self):
        """Get all logs."""
        self.mutex.lock()
        try:
            return self.logs.copy()  # Return a copy for thread safety
        finally:
            self.mutex.unlock()
    
    def get_log_file_path(self):
        """Get the path to the current log file."""
        return self.log_file

# Create a singleton instance for easy import
logger = LoggerService() 