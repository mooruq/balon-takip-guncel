#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Teknofest Sidebar Component
--------------------------
Reusable sidebar component for the balon takip application.
Adapted from Teknofest project.
"""

import os
import math
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel, QHBoxLayout, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer, QSize, QPointF, QRect, QPoint
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QPainterPath, QPen, QBrush, QFont

class IconThemeManager:
    """Class for handling theme-aware icons."""
    
    @staticmethod
    def get_themed_icon(icon_path, is_dark_theme=True):
        """Get a themed icon with appropriate color based on current theme."""
        if not os.path.exists(icon_path):
            return QIcon()
            
        # Load the original icon
        pixmap = QPixmap(icon_path)
        
        # Create a transparent version
        result = QPixmap(pixmap.size())
        result.fill(Qt.transparent)
        
        # Create painter for the result
        painter = QPainter(result)
        
        # Set the color based on theme
        if is_dark_theme:
            # For dark theme, use white icons
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(result.rect(), QColor(255, 255, 255, 255))  # White
        else:
            # For light theme, use dark icons
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(result.rect(), QColor(33, 33, 33, 255))  # Dark gray/black
        
        # End painting
        painter.end()
        
        return QIcon(result)

class Sidebar(QWidget):
    """
    Reusable sidebar component.
    Implements the Strategy pattern for different sidebar behaviors.
    """
    # Signals
    animation_value_changed = pyqtSignal(int)
    
    def __init__(self, parent=None, position="left", width=250):
        super().__init__(parent)
        self.position = position
        self.target_width = width
        self.is_open = True
        
        # Set initial width to target width (always open for fixed layout)
        self.setFixedWidth(width)
        
        # Set background color
        self.setStyleSheet("background-color: #333333;")
        
        # Create layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # Initialize animation
        self.animation = QPropertyAnimation(self, b"minimumWidth")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.valueChanged.connect(self._on_animation_value_changed)
    
    def _on_animation_value_changed(self, value):
        """Handle animation value changes."""
        self.animation_value_changed.emit(value)
    

    
    def add_widget(self, widget):
        """Add a widget to the sidebar."""
        self.layout.addWidget(widget)
    
    def add_stretch(self):
        """Add a stretch to the sidebar layout."""
        self.layout.addStretch()


class LogSidebar(Sidebar):
    """Log sidebar implementation for Balon Takip system."""
    
    def __init__(self, parent=None):
        super().__init__(parent, position="left", width=250)  # %10 width for 1400px screen
        
        # Base directory for icons
        self.icon_base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "icons")
        
        # Track the number of displayed logs to avoid unnecessary refreshes
        self.displayed_log_count = 0
        
        # Add header label
        self.header_label = QLabel("Balon Takip Logları")
        self.header_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: white;
            padding: 5px;
            margin-bottom: 10px;
            background-color: transparent;
        """)
        self.add_widget(self.header_label)
        
        # Create log text area with enhanced styling
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.update_text_area_style(is_dark=True)  # Default to dark theme
        self.add_widget(self.log_text)
        
        # Set custom document handling to colorize log levels
        self.log_text.document().setDefaultStyleSheet("""
            .info { color: #2ecc71; }  /* Green */
            .warning { color: #f39c12; }  /* Orange/Yellow */
            .error { color: #e74c3c; }  /* Red */
            .timestamp { color: #3498db; font-weight: bold; }  /* Blue */
        """)
        
        # Setup timer to ensure logs are updated regularly
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_logs)
        self.refresh_timer.start(500)  # Refresh every 500ms
    
    def update_text_area_style(self, is_dark=True):
        """Update the text area style based on theme."""
        if is_dark:
            self.log_text.setStyleSheet("""
                QTextEdit {
                    background-color: #2c3e50;
                    color: #ecf0f1;
                    border: 1px solid #34495e;
                    border-radius: 5px;
                    padding: 8px;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 12px;
                    line-height: 1.4;
                }
                
                QTextEdit QScrollBar:vertical {
                    border: none;
                    background: #34495e;
                    width: 10px;
                    margin: 0px;
                }
                
                QTextEdit QScrollBar::handle:vertical {
                    background: #7f8c8d;
                    min-height: 30px;
                    border-radius: 5px;
                }
                
                QTextEdit QScrollBar::handle:vertical:hover {
                    background: #95a5a6;
                }
                
                QTextEdit QScrollBar::add-line:vertical, QTextEdit QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                
                QTextEdit QScrollBar::add-page:vertical, QTextEdit QScrollBar::sub-page:vertical {
                    background: none;
                }
            """)
            self.header_label.setStyleSheet("""
                font-size: 16px;
                font-weight: bold;
                color: white;
                padding: 5px;
                margin-bottom: 10px;
                background-color: transparent;
            """)
        else:
            self.log_text.setStyleSheet("""
                QTextEdit {
                    background-color: #f8f9fa;
                    color: #343a40;
                    border: 1px solid #ced4da;
                    border-radius: 5px;
                    padding: 8px;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 12px;
                    line-height: 1.4;
                }
                
                QTextEdit QScrollBar:vertical {
                    border: none;
                    background: #e9ecef;
                    width: 10px;
                    margin: 0px;
                }
                
                QTextEdit QScrollBar::handle:vertical {
                    background: #adb5bd;
                    min-height: 30px;
                    border-radius: 5px;
                }
                
                QTextEdit QScrollBar::handle:vertical:hover {
                    background: #868e96;
                }
                
                QTextEdit QScrollBar::add-line:vertical, QTextEdit QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                
                QTextEdit QScrollBar::add-page:vertical, QTextEdit QScrollBar::sub-page:vertical {
                    background: none;
                }
            """)
            self.header_label.setStyleSheet("""
                font-size: 16px;
                font-weight: bold;
                color: #343a40;
                padding: 5px;
                margin-bottom: 10px;
                background-color: transparent;
            """)
    
    def add_log(self, message):
        """Add a log message to the text area with colorized formatting."""
        # Format the message with HTML for colorization
        formatted_html = self.format_log_message(message)
        
        # Add the formatted message
        self.log_text.append(formatted_html)
        
        # Increment the displayed log count
        self.displayed_log_count += 1
        
        # Auto-scroll to the bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def format_log_message(self, message):
        """Format a log message with HTML styling based on log level."""
        try:
            # Extract parts of the log message
            timestamp_end = message.find(']') + 1
            if timestamp_end > 0 and '[' in message:
                timestamp = message[:timestamp_end]
                content = message[timestamp_end:].strip()
                
                # Determine log level
                level_class = 'info'
                if '[WARNING]' in timestamp:
                    level_class = 'warning'
                elif '[ERROR]' in timestamp:
                    level_class = 'error'
                
                # Format with HTML
                return f'<span class="timestamp">{timestamp}</span> <span class="{level_class}">{content}</span>'
            else:
                # Fallback for unformatted messages
                return message
        except Exception:
            # Fallback in case of parsing error
            return message
    
    def clear_logs(self):
        """Clear the log text area."""
        self.log_text.clear()
        self.displayed_log_count = 0
    
    def refresh_logs(self):
        """Ensure logs are displayed and updated by fetching the latest logs from LoggerService."""
        try:
            # Import here to avoid circular import
            from src.utils.logger import logger
            
            # Get all logs
            all_logs = logger.get_logs()
            
            # Check if there are new logs to display
            if len(all_logs) > self.displayed_log_count:
                # Save the current scroll position
                scrollbar = self.log_text.verticalScrollBar()
                was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 10  # Consider "at bottom" if within 10 pixels
                scroll_position = scrollbar.value()
                
                # Clear and refill the log view
                self.log_text.clear()
                for log in all_logs:
                    formatted_html = self.format_log_message(log)
                    self.log_text.append(formatted_html)
                
                # Update the displayed log count
                self.displayed_log_count = len(all_logs)
                
                # Restore scroll position or keep at bottom if it was at bottom
                if was_at_bottom:
                    scrollbar.setValue(scrollbar.maximum())
                else:
                    scrollbar.setValue(scroll_position)
            
            # Force update of the text edit
            self.log_text.update()
        except ImportError:
            # Logger not available yet during startup
            pass


class MenuSidebar(Sidebar):
    """Menu sidebar implementation for Balon Takip system."""
    
    def __init__(self, parent=None):
        super().__init__(parent, position="right", width=250)
        
        # Flag to track current theme
        self.is_dark_theme = True
        
        # Base directory for icons
        self.icon_base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "icons")
        
        # Create simplified menu for Balon Takip system
        self.create_balon_takip_menu()
        
    def create_balon_takip_menu(self):
        """Create simplified menu for Balon Takip system."""
        
        # Top buttons (theme, settings, exit)
        moon_icon_path = os.path.join(self.icon_base_dir, "moon.png")
        self.theme_button = self.create_icon_button("", moon_icon_path, icon_only=True)
        self.settings_button = self.create_icon_button("", os.path.join(self.icon_base_dir, "settings.png"), icon_only=True)
        self.exit_button = self.create_icon_button("", os.path.join(self.icon_base_dir, "exit.png"), icon_only=True)
        
        # Create top buttons layout
        self.top_buttons_layout = QHBoxLayout()
        self.top_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.top_buttons_layout.setSpacing(5)
        self.top_buttons_layout.addWidget(self.theme_button)
        self.top_buttons_layout.addWidget(self.settings_button)
        self.top_buttons_layout.addWidget(self.exit_button)
        
        self.top_buttons_widget = QWidget()
        self.top_buttons_widget.setLayout(self.top_buttons_layout)
        self.top_buttons_widget.setStyleSheet("""
            background-color: transparent;
            border-radius: 8px;
            padding: 5px;
            margin-bottom: 10px;
        """)
        
        # Hedef tracking button
        balloon_icon = self.create_balloon_icon()
        self.balloon_tracking_button = self.create_icon_button("Hedef Takip ve İmha\n(ByteTracker AI)", 
                                              balloon_icon, checkable=True)
        
        # Save and controls
        self.save_button = self.create_icon_button("", os.path.join(self.icon_base_dir, "save.png"), icon_only=True)
        self.save_button.setToolTip("Kaydet")
        
        # Motor control buttons
        self.motor_connect_button = self.create_icon_button("🔌 Motor Bağlan", None, checkable=False)
        self.motor_connect_button.setStyleSheet("""
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
            QPushButton:pressed {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        
        self.motor_tracking_button = self.create_icon_button("🎯 Motor Tracking", None, checkable=True)
        self.motor_tracking_button.setStyleSheet("""
            QPushButton {
                background-color: #2980b9;
                color: white;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-radius: 8px;
                padding: 8px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #3498db;
            }
            QPushButton:pressed {
                background-color: #1f618d;
            }
            QPushButton:checked {
                background-color: #e67e22;
                border: 2px solid #d35400;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        
        # Initially disable motor tracking
        self.motor_tracking_button.setEnabled(False)
        
        # Emergency stop button
        self.emergency_stop_button = QPushButton("🚨 ACİL STOP")
        self.emergency_stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border: none;
                border-radius: 8px;
                padding: 12px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        
        # Bottom buttons layout
        self.bottom_buttons_layout = QHBoxLayout()
        self.bottom_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.bottom_buttons_layout.setSpacing(5)
        self.bottom_buttons_layout.addWidget(self.save_button)
        
        self.bottom_buttons_widget = QWidget()
        self.bottom_buttons_widget.setLayout(self.bottom_buttons_layout)
        self.bottom_buttons_widget.setStyleSheet("""
            background-color: transparent;
            border-radius: 8px;
            padding: 5px;
            margin-top: 10px;
        """)
        
        # Add widgets to sidebar
        self.add_widget(self.top_buttons_widget)
        self.add_widget(self.create_divider())
        
        # Main tracking section - moved to top
        tracking_title = QLabel("1.aşama")
        tracking_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: white;
            text-align: center;
            padding: 10px;
            background-color: transparent;
        """)
        tracking_title.setAlignment(Qt.AlignCenter)
        self.add_widget(tracking_title)
        
        self.add_widget(self.balloon_tracking_button)
        
        # Motor control section
        motor_title = QLabel("Motor Kontrol")
        motor_title.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: white;
            text-align: center;
            padding: 5px;
            margin-top: 10px;
            background-color: transparent;
        """)
        motor_title.setAlignment(Qt.AlignCenter)
        self.add_widget(motor_title)
        
        self.add_widget(self.motor_connect_button)
        self.add_widget(self.motor_tracking_button)
        
        self.add_stretch()
        self.add_widget(self.emergency_stop_button)
        self.add_widget(self.bottom_buttons_widget)
        
        # Store buttons for theme updates
        self.buttons = [
            self.theme_button, self.settings_button, self.exit_button,
            self.save_button, self.balloon_tracking_button, self.emergency_stop_button,
            self.motor_connect_button, self.motor_tracking_button
        ]
    
    def create_divider(self):
        """Create a visual divider."""
        divider = QLabel()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #555555; margin: 10px 0px;")
        return divider
    
    def create_balloon_icon(self):
        """Create a balloon icon programmatically."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw balloon circle
        painter.setBrush(QBrush(QColor(76, 175, 80)))  # Green
        painter.setPen(QPen(QColor(56, 142, 60), 2))
        painter.drawEllipse(6, 4, 20, 20)
        
        # Draw string
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawLine(16, 24, 16, 28)
        
        painter.end()
        return QIcon(pixmap)
    
    def create_icon_button(self, text, icon_path_or_icon, checkable=False, icon_only=False):
        """Create a button with icon and optional text."""
        button = QPushButton(text)
        button.setCheckable(checkable)
        
        # Set icon
        if isinstance(icon_path_or_icon, str) and os.path.exists(icon_path_or_icon):
            themed_icon = IconThemeManager.get_themed_icon(icon_path_or_icon, is_dark_theme=self.is_dark_theme)
            button.setIcon(themed_icon)
        elif isinstance(icon_path_or_icon, QIcon):
            button.setIcon(icon_path_or_icon)
        
        # Configure button appearance
        if icon_only:
            button.setFixedSize(36, 36)
            button.setIconSize(QSize(20, 20))  # Slightly smaller for better centering
            button.setToolTip(text)
            # Force center alignment for icon-only buttons
            button.setStyleSheet(button.styleSheet() + """
                QPushButton {
                    qproperty-iconSize: 20px 20px;
                }
            """)
        else:
            button.setMinimumHeight(60)
            button.setIconSize(QSize(24, 24))
            # For text+icon buttons, ensure proper spacing
            button.setContentsMargins(4, 4, 4, 4)
        
        # Set base style with centered icons
        if icon_only:
            # Icon-only buttons - center the icon perfectly
            button.setStyleSheet("""
                QPushButton {
                    background-color: #444444;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 0px;
                    margin: 2px;
                    text-align: center;
                    qproperty-iconSize: 24px 24px;
                }
                QPushButton:hover {
                    background-color: #555555;
                }
                QPushButton:pressed {
                    background-color: #666666;
                }
                QPushButton:checked {
                    background-color: #2196F3;
                    border: 2px solid #1976D2;
                }
            """)
        else:
            # Icon + text buttons - align icon and text properly
            button.setStyleSheet("""
                QPushButton {
                    background-color: #444444;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px;
                    margin: 2px;
                    text-align: center;
                    font-size: 12px;
                    qproperty-iconSize: 24px 24px;
                }
                QPushButton:hover {
                    background-color: #555555;
                }
                QPushButton:pressed {
                    background-color: #666666;
                }
                QPushButton:checked {
                    background-color: #2196F3;
                    border: 2px solid #1976D2;
                }
            """)
        
        return button
    
    def update_theme(self, is_dark=True):
        """Update theme for all buttons."""
        self.is_dark_theme = is_dark
        
        # Update button icons based on theme
        for button in self.buttons:
            if hasattr(button, 'icon_path'):
                themed_icon = IconThemeManager.get_themed_icon(button.icon_path, is_dark_theme=is_dark)
                button.setIcon(themed_icon) 