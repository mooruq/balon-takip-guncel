#!/usr/bin/env python3
"""
Satranç Tahtası Deseni Oluşturucu
Kamera kalibrasyonu için yazdırılabilir satranç tahtası oluşturur

Kullanım:
python create_checkerboard.py

Gereksinimler:
pip install opencv-python numpy matplotlib
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

def create_checkerboard_opencv(rows=6, cols=9, square_size_px=50):
    """
    OpenCV ile satranç tahtası oluştur
    
    Args:
        rows: Satır sayısı (iç köşe)
        cols: Sütun sayısı (iç köşe)
        square_size_px: Kare boyutu (piksel)
    """
    # Toplam boyut (kenar kareler dahil)
    total_rows = rows + 1
    total_cols = cols + 1
    
    # Görüntü boyutu
    img_height = total_rows * square_size_px
    img_width = total_cols * square_size_px
    
    # Beyaz arka plan
    checkerboard = np.ones((img_height, img_width), dtype=np.uint8) * 255
    
    # Siyah kareler ekle
    for i in range(total_rows):
        for j in range(total_cols):
            # Satranç tahtası deseni: (i+j) çift ise siyah
            if (i + j) % 2 == 0:
                y1 = i * square_size_px
                y2 = (i + 1) * square_size_px
                x1 = j * square_size_px
                x2 = (j + 1) * square_size_px
                checkerboard[y1:y2, x1:x2] = 0
    
    return checkerboard

def create_checkerboard_matplotlib(rows=6, cols=9, square_size_mm=25, dpi=300):
    """
    Matplotlib ile yüksek kaliteli satranç tahtası oluştur
    
    Args:
        rows: Satır sayısı (iç köşe)
        cols: Sütun sayısı (iç köşe)
        square_size_mm: Kare boyutu (mm)
        dpi: Çözünürlük
    """
    # Toplam boyut (kenar kareler dahil)
    total_rows = rows + 1
    total_cols = cols + 1
    
    # Figür boyutu (inch cinsinden)
    fig_width_inch = (total_cols * square_size_mm) / 25.4  # mm to inch
    fig_height_inch = (total_rows * square_size_mm) / 25.4
    
    # Figür oluştur
    fig, ax = plt.subplots(1, 1, figsize=(fig_width_inch, fig_height_inch), dpi=dpi)
    
    # Arka planı beyaz yap
    ax.set_facecolor('white')
    
    # Siyah kareler ekle
    for i in range(total_rows):
        for j in range(total_cols):
            if (i + j) % 2 == 0:  # Siyah kare
                rect = Rectangle((j * square_size_mm, (total_rows - 1 - i) * square_size_mm), 
                               square_size_mm, square_size_mm, 
                               facecolor='black', edgecolor='none')
                ax.add_patch(rect)
    
    # Eksen ayarları
    ax.set_xlim(0, total_cols * square_size_mm)
    ax.set_ylim(0, total_rows * square_size_mm)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Kenar boşluklarını kaldır
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    
    return fig

def add_info_text(img, rows, cols, square_size_mm):
    """
    Görüntüye bilgi metni ekle
    """
    # Metin bilgileri
    info_lines = [
        f"Checkerboard Pattern for Camera Calibration",
        f"Inner corners: {cols} x {rows}",
        f"Square size: {square_size_mm} mm",
        f"Print at 100% scale - Do NOT scale to fit page",
        f"Mount on flat, rigid surface"
    ]
    
    # Metin alanı yüksekliği
    text_height = 100
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness = 1
    
    # Yeni görüntü oluştur (metin alanı ile)
    new_img = np.ones((img.shape[0] + text_height, img.shape[1]), dtype=np.uint8) * 255
    new_img[text_height:, :] = img
    
    # Metinleri ekle
    y_offset = 20
    for i, line in enumerate(info_lines):
        y_pos = y_offset + i * 18
        cv2.putText(new_img, line, (10, y_pos), font, font_scale, 0, thickness)
    
    return new_img

def main():
    """
    Ana fonksiyon - Farklı boyutlarda satranç tahtaları oluştur
    """
    print("Satranç Tahtası Deseni Oluşturucu")
    print("="*40)
    
    # Farklı konfigürasyonlar
    configs = [
        {"name": "Standard_9x6", "rows": 6, "cols": 9, "square_mm": 25},
        {"name": "Large_9x6", "rows": 6, "cols": 9, "square_mm": 30},
        {"name": "Small_7x5", "rows": 5, "cols": 7, "square_mm": 20},
    ]
    
    for config in configs:
        print(f"\nOluşturuluyor: {config['name']}")
        
        # OpenCV versiyonu (ekran görüntüleme için)
        checkerboard_cv = create_checkerboard_opencv(
            rows=config['rows'], 
            cols=config['cols'], 
            square_size_px=50
        )
        
        # Bilgi metni ekle
        checkerboard_with_info = add_info_text(
            checkerboard_cv, 
            config['rows'], 
            config['cols'], 
            config['square_mm']
        )
        
        # OpenCV görüntüsünü kaydet
        cv2.imwrite(f"checkerboard_{config['name']}_preview.png", checkerboard_with_info)
        
        # Matplotlib versiyonu (yüksek kalite yazdırma için)
        fig = create_checkerboard_matplotlib(
            rows=config['rows'],
            cols=config['cols'],
            square_size_mm=config['square_mm'],
            dpi=300
        )
        
        # PDF olarak kaydet (yazdırma için ideal)
        fig.savefig(f"checkerboard_{config['name']}_print.pdf", 
                   dpi=300, bbox_inches='tight', pad_inches=0)
        
        # PNG olarak da kaydet
        fig.savefig(f"checkerboard_{config['name']}_print.png", 
                   dpi=300, bbox_inches='tight', pad_inches=0)
        
        plt.close(fig)
        
        print(f"✓ {config['name']} oluşturuldu:")
        print(f"  - Preview: checkerboard_{config['name']}_preview.png")
        print(f"  - Print: checkerboard_{config['name']}_print.pdf")
        print(f"  - Print: checkerboard_{config['name']}_print.png")
    
    # Kullanım talimatları
    print("\n" + "="*50)
    print("KULLANIM TALİMATLARI")
    print("="*50)
    print("1. PDF dosyasını %100 ölçekte yazdırın (sayfa boyutuna sığdırmayın)")
    print("2. Düz, sert bir yüzeye yapıştırın (karton, tahta vb.)")
    print("3. Kırışıklık ve bükülme olmadığından emin olun")
    print("4. İyi aydınlatma altında kullanın")
    print("5. Kamera kalibrasyonu sırasında farklı açılardan fotoğraf çekin")
    
    # Önizleme göster
    print("\nÖnizleme gösteriliyor... (herhangi bir tuşa basın)")
    preview_img = cv2.imread("checkerboard_Standard_9x6_preview.png")
    if preview_img is not None:
        # Görüntüyü küçült (ekrana sığdır)
        height, width = preview_img.shape[:2]
        if height > 800:
            scale = 800 / height
            new_width = int(width * scale)
            new_height = int(height * scale)
            preview_img = cv2.resize(preview_img, (new_width, new_height))
        
        cv2.imshow('Checkerboard Preview', preview_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main() 