#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Teknofest Camera View Component
------------------------------
Component for displaying camera feed with advanced features.
Adapted from Teknofest project for Balon Takip system.
"""

import cv2
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QSize, QRect, QTimer
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QPen, QBrush

class TeknoFestCameraView(QWidget):
    """
    Advanced camera view component for Balon Takip system.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #121212;")  # Dark background for professional look
        self.current_pixmap = None
        self.aspect_ratio = 16/9  # Modern aspect ratio (16:9)
        self.scale_mode = "fill"  # Default scale mode: "fit" or "fill"
        self.detection_active = False
        self.detection_mode = None
        
        # Message display
        self.message = None
        self.message_color = QColor(255, 255, 255)
        self.message_timer = QTimer(self)
        self.message_timer.timeout.connect(self.clear_message)
        
        # Emergency stop
        self.emergency_mode = False
        self.emergency_pixmap = None
        
        # Tracking info
        self.tracking_info = None
        
    def update_frame(self, frame_data):
        """Update the displayed frame with a new QImage or OpenCV frame."""
        # Skip frame updates if in emergency mode
        if self.emergency_mode:
            return
        
        # Handle different input types
        q_image = None
        
        # Case 1: Already a QImage
        if isinstance(frame_data, QImage):
            if frame_data.isNull():
                return
            q_image = frame_data
            
        # Case 2: OpenCV frame (numpy array) - convert to QImage
        elif hasattr(frame_data, 'shape'):  # numpy array check
            try:
                height, width = frame_data.shape[:2]
                if len(frame_data.shape) == 3:
                    # Color image - convert BGR to RGB
                    rgb_frame = cv2.cvtColor(frame_data, cv2.COLOR_BGR2RGB)
                    bytes_per_line = 3 * width
                    q_image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                else:
                    # Grayscale image
                    bytes_per_line = width
                    q_image = QImage(frame_data.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
            except Exception as e:
                print(f"Error converting OpenCV frame to QImage: {e}")
                return
        else:
            print(f"Unsupported frame type: {type(frame_data)}")
            return
        
        # Ensure q_image is valid
        if q_image is None or q_image.isNull():
            return
            
        # Store the original image dimensions for aspect ratio calculation
        if not hasattr(self, 'original_size'):
            try:
                # Get size as QSize object
                size_obj = q_image.size()
                if isinstance(size_obj, QSize):
                    self.original_size = size_obj
                    self.aspect_ratio = self.original_size.width() / self.original_size.height()
                else:
                    # Fallback: get dimensions directly
                    width = q_image.width()
                    height = q_image.height()
                    self.original_size = QSize(width, height)
                    self.aspect_ratio = width / height if height > 0 else 16/9
            except Exception as e:
                # Fallback to default aspect ratio
                print(f"Error getting image size: {e}")
                self.original_size = QSize(640, 480)
                self.aspect_ratio = 640 / 480
        
        # Convert QImage to QPixmap only once
        try:
            self.current_pixmap = QPixmap.fromImage(q_image)
        except Exception as e:
            print(f"Error converting QImage to QPixmap: {e}")
            return
        
        # Force a repaint to display the new frame
        self.update()
    
    def set_scale_mode(self, mode):
        """Set the scaling mode ('fit' or 'fill')."""
        if mode in ["fit", "fill"]:
            self.scale_mode = mode
            self.update()
    
    def set_detection_active(self, active):
        """Set whether detection is active."""
        self.detection_active = active
        if not active:
            self.detection_mode = None
    
    def set_detection_mode(self, mode):
        """Set the detection mode (balon_tracking)."""
        self.detection_mode = mode
    
    def set_tracking_info(self, tracked_count, lost_count, fps=None):
        """Set tracking information to display."""
        self.tracking_info = {
            'tracked': tracked_count,
            'lost': lost_count,
            'fps': fps
        }
        self.update()
    
    def show_message(self, message, color=None, timeout=3000):
        """Show a message on the camera view."""
        self.message = message
        if color:
            self.message_color = color
        else:
            self.message_color = QColor(255, 255, 255)
        
        # Start timer to clear message
        self.message_timer.start(timeout)
        self.update()
    
    def clear_message(self):
        """Clear the message from the camera view."""
        self.message = None
        self.message_timer.stop()
        self.update()
    
    def show_emergency_stop(self):
        """Display the emergency stop screen."""
        self.emergency_mode = True
        
        # Create an emergency stop image
        emergency_image = QImage(640, 480, QImage.Format_RGB32)
        emergency_image.fill(QColor(0, 0, 0))
        
        # Create painter for the emergency image
        painter = QPainter(emergency_image)
        
        # Main title with larger font
        painter.setFont(QFont("Arial", 32, QFont.Bold))
        painter.setPen(QColor(255, 0, 0))
        
        # Draw title at top third of screen
        title_rect = QRect(emergency_image.rect())
        title_rect.setHeight(title_rect.height() // 3)
        painter.drawText(title_rect, Qt.AlignCenter, "ACİL STOP ETKİN!")
        
        # Additional warning text in middle third with smaller font
        painter.setFont(QFont("Arial", 18))
        painter.setPen(QColor(255, 0, 0))
        
        warning_rect = QRect(emergency_image.rect())
        warning_rect.setTop(warning_rect.top() + title_rect.height())
        warning_rect.setHeight(warning_rect.height() // 3)
        
        painter.drawText(warning_rect, Qt.AlignCenter, 
                         "Balon Takip Sistemi Durduruldu\nYeniden başlatmak için uygulamayı\nkapatıp tekrar açın.")
        
        painter.end()
        
        # Convert to pixmap
        self.emergency_pixmap = QPixmap.fromImage(emergency_image)
        self.update()
    
    def reset_emergency_stop(self):
        """Reset the emergency stop mode."""
        self.emergency_mode = False
        self.emergency_pixmap = None
        self.update()
    
    def on_detection(self, frame, detections):
        """Handle detection results from ByteTracker.
        
        Args:
            frame: The video frame with detections drawn on it
            detections: List of detection objects
        """
        if not self.detection_active:
            return
            
        # Convert OpenCV BGR image to QImage
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        
        # Update the view with the processed frame
        self.update_frame(q_img)
    
    def paintEvent(self, event):
        """Override paintEvent to handle custom drawing."""
        super().paintEvent(event)
        
        # Create a painter for this widget
        painter = QPainter(self)
        
        # Get the widget size
        widget_size = self.size()
        
        # Handle emergency mode
        if self.emergency_mode and self.emergency_pixmap:
            # Calculate position to center the image
            x = (widget_size.width() - self.emergency_pixmap.width()) // 2
            y = (widget_size.height() - self.emergency_pixmap.height()) // 2
            
            # Draw the emergency pixmap
            painter.drawPixmap(x, y, self.emergency_pixmap)
            painter.end()
            return
        
        # Handle normal camera display
        if self.current_pixmap is not None:
            if self.scale_mode == "fill":
                # Fill mode: Scale the image to fill the entire widget, may crop parts
                widget_ratio = widget_size.width() / widget_size.height()
                
                if widget_ratio > self.aspect_ratio:
                    # Widget is wider than the video - scale based on width
                    target_width = widget_size.width()
                    target_height = int(target_width / self.aspect_ratio)
                else:
                    # Widget is taller than the video - scale based on height
                    target_height = widget_size.height()
                    target_width = int(target_height * self.aspect_ratio)
                
                # Calculate position to center the image
                x = (widget_size.width() - target_width) // 2
                y = (widget_size.height() - target_height) // 2
                
                # Scale the pixmap to fill the widget
                scaled_pixmap = self.current_pixmap.scaled(
                    target_width, 
                    target_height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                
                # Draw the pixmap
                painter.drawPixmap(x, y, scaled_pixmap)
            else:
                # Fit mode: Fit the entire image within the widget with letterboxing
                # Calculate the target size based on the widget size and aspect ratio
                target_width = widget_size.width()
                target_height = int(target_width / self.aspect_ratio)
                
                if target_height > widget_size.height():
                    target_height = widget_size.height()
                    target_width = int(target_height * self.aspect_ratio)
                
                # Calculate position to center the image
                x = (widget_size.width() - target_width) // 2
                y = (widget_size.height() - target_height) // 2
                
                # Scale the pixmap
                scaled_pixmap = self.current_pixmap.scaled(
                    target_width, 
                    target_height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                
                # Draw the pixmap
                painter.drawPixmap(x, y, scaled_pixmap)
        
        # Draw any active message
        if self.message:
            painter.setFont(QFont("Arial", 20, QFont.Bold))
            painter.setPen(self.message_color)
            
            # Create a semi-transparent background for the text
            text_rect = painter.fontMetrics().boundingRect(self.message)
            bg_rect = QRect(
                (widget_size.width() - text_rect.width()) // 2 - 20,
                (widget_size.height() - text_rect.height()) // 2 - 10,
                text_rect.width() + 40,
                text_rect.height() + 20
            )
            
            # Draw background with 70% opacity
            painter.setOpacity(0.7)
            painter.fillRect(bg_rect, QColor(0, 0, 0))
            
            # Draw text at 100% opacity
            painter.setOpacity(1.0)
            painter.drawText(
                QRect(0, 0, widget_size.width(), widget_size.height()),
                Qt.AlignCenter,
                self.message
            )
        
        # Draw detection mode indicator if active
        if self.detection_active and self.detection_mode:
            mode_text = None
            if self.detection_mode == "balon_tracking":
                mode_text = "Balon Takip Modu (ByteTracker AI + Kalman Filter)"
                
            if mode_text:
                # Create semi-transparent background for mode text
                painter.setFont(QFont("Arial", 12, QFont.Bold))
                text_rect = painter.fontMetrics().boundingRect(mode_text)
                
                bg_rect = QRect(
                    10,
                    10,
                    text_rect.width() + 20,
                    text_rect.height() + 10
                )
                
                # Draw background with opacity
                painter.setOpacity(0.8)
                painter.fillRect(bg_rect, QColor(0, 0, 0))
                
                # Draw text with full opacity
                painter.setOpacity(1.0)
                painter.setPen(QColor(76, 175, 80))  # Green for balon tracking
                painter.drawText(
                    QRect(20, 15, text_rect.width(), text_rect.height()),
                    Qt.AlignLeft | Qt.AlignVCenter,
                    mode_text
                )
        
        # Draw tracking info if available
        if self.tracking_info:
            info_text = f"Takip: {self.tracking_info['tracked']} | Kayıp: {self.tracking_info['lost']}"
            if self.tracking_info.get('fps'):
                info_text += f" | FPS: {self.tracking_info['fps']:.1f}"
            
            # Position at bottom right
            painter.setFont(QFont("Arial", 11, QFont.Bold))
            text_rect = painter.fontMetrics().boundingRect(info_text)
            
            bg_rect = QRect(
                widget_size.width() - text_rect.width() - 30,
                widget_size.height() - text_rect.height() - 20,
                text_rect.width() + 20,
                text_rect.height() + 10
            )
            
            # Draw background with opacity
            painter.setOpacity(0.8)
            painter.fillRect(bg_rect, QColor(0, 0, 0))
            
            # Draw text with full opacity
            painter.setOpacity(1.0)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(
                QRect(widget_size.width() - text_rect.width() - 20, 
                     widget_size.height() - text_rect.height() - 15,
                     text_rect.width(), 
                     text_rect.height()),
                Qt.AlignLeft | Qt.AlignVCenter,
                info_text
            )
        
        # Draw center crosshair (+) for motor targeting
        if not self.emergency_mode:
            center_x = widget_size.width() // 2
            center_y = widget_size.height() // 2
            crosshair_size = 15
            crosshair_thickness = 2
            crosshair_color = QColor(255, 0, 0)  # Red color
            
            # Set pen for crosshair
            painter.setOpacity(1.0)
            painter.setPen(QPen(crosshair_color, crosshair_thickness))
            
            # Draw horizontal line
            painter.drawLine(
                center_x - crosshair_size, center_y,
                center_x + crosshair_size, center_y
            )
            
            # Draw vertical line  
            painter.drawLine(
                center_x, center_y - crosshair_size,
                center_x, center_y + crosshair_size
            )
            
            # Draw center dot for better visibility
            painter.setBrush(QBrush(crosshair_color))
            painter.drawEllipse(center_x - 2, center_y - 2, 4, 4)
        
        painter.end() 