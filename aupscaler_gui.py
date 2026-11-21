import os
import sys
import io
import gc
import time
import threading
import queue
import ctypes
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List
import customtkinter as ctk
from PIL import Image, ImageTk, ImageOps, ImageDraw, ImageGrab
import cv2
import numpy as np

try:
    import windnd
    WINDND_AVAILABLE = True
except Exception:
    WINDND_AVAILABLE = False

try:
    import win32clipboard
    WIN32_CLIPBOARD_AVAILABLE = True
except Exception:
    WIN32_CLIPBOARD_AVAILABLE = False

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from backend.upscaler import UpscalerEngine, OperationCancelled

try:
    cv2.setNumThreads(os.cpu_count() or 4)
    cv2.setUseOptimized(True)
except Exception:
    pass


def register_custom_fonts():
    try:
        font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
        if not os.path.isdir(font_dir) and hasattr(sys, "_MEIPASS"):
            font_dir = os.path.join(sys._MEIPASS, "assets", "fonts")
        nafis_path = os.path.join(font_dir, "A Nafis.ttf")
        if os.path.isfile(nafis_path):
            ctypes.windll.gdi32.AddFontResourceExW(os.path.abspath(nafis_path), 0x10, 0)
    except Exception:
        pass


register_custom_fonts()

THEME_COLORS = {
    "bg_root": ("#f4f6f9", "#0e1015"),
    "bg_header": ("#ffffff", "#14171f"),
    "bg_sidebar": ("#f9fafb", "#14171f"),
    "bg_card": ("#ffffff", "#1c202b"),
    "bg_card_sub": ("#f3f4f6", "#151922"),
    "border": ("#e5e7eb", "#2a3040"),
    "border_active": ("#2563eb", "#60a5fa"),
    "accent": ("#2563eb", "#3b82f6"),
    "accent_hover": ("#1d4ed8", "#2563eb"),
    "accent_soft": ("#eff6ff", "#1e293b"),
    "seg_selected": ("#dbeafe", "#3b82f6"),
    "seg_selected_hover": ("#bfdbfe", "#2563eb"),
    "accent_success": ("#059669", "#10b981"),
    "accent_success_hover": ("#047857", "#059669"),
    "danger": ("#dc2626", "#f87171"),
    "danger_hover": ("#fee2e2", "#3b1d24"),
    "text_primary": ("#111827", "#f3f4f6"),
    "text_secondary": ("#4b5563", "#a1a9ba"),
    "text_muted": ("#6b7280", "#6e778a"),
    "canvas_bg_hex": {"light": "#e8ecf2", "dark": "#090b10"},
    "btn_secondary": ("#ffffff", "#1f2430"),
    "btn_secondary_hover": ("#f3f4f6", "#2a3142"),
    "opt_bg": ("#ffffff", "#1f2430"),
    "opt_btn": ("#f3f4f6", "#2a3142"),
    "opt_btn_hover": ("#e5e7eb", "#374151"),
    "scrollbar": ("#cbd5e1", "#2e3648"),
    "scrollbar_hover": ("#94a3b8", "#475569")
}

ALGO_CHOICES = [
    ("Balanced (Fast Neural)", "espcn", "Fast, sharp neural upscaling for most photos and art"),
    ("High Detail (Deep Neural)", "fsrcnn", "Richer textures for portraits and detailed photos"),
    ("Photo & Art (Lanczos)", "lanczos", "Crisp mathematical scaling with zero neural styling"),
    ("Pixel Art (No Blur)", "nearest", "Hard pixel edges preserved for retro sprites and icons")
]

TRANSLATIONS = {
    "en": {
        "title": "Aupscaler",
        "tab_single": "Single",
        "tab_batch": "Batch",
        "btn_browse": "Open",
        "btn_paste": "Paste",
        "btn_sample": "Sample",
        "btn_clear": "Clear",
        "card_source": "Source",
        "card_scale": "Scale",
        "custom_scale": "Custom",
        "target_dim": "Output",
        "est_ram": "RAM",
        "card_quality": "Quality Mode",
        "card_enhancements": "Enhancements",
        "btn_reset_effects": "Reset",
        "feat_deblur": "Sharpen & Deblur",
        "feat_denoise": "Reduce Noise",
        "feat_hdr": "Balance Tone & Color",
        "feat_bg": "Remove Background",
        "card_format": "Format",
        "btn_upscale": "Upscale Image",
        "btn_enhance_only": "Apply Enhancements",
        "btn_save": "Export",
        "btn_copy": "Copy",
        "btn_compare": "Compare",
        "btn_fit": "Fit",
        "btn_cancel": "Cancel",
        "status_ready": "Ready",
        "status_loading": "Loading image...",
        "status_processing": "Processing...",
        "status_done": "Upscale complete",
        "status_cancelled": "Cancelled",
        "status_preview_busy": "Updating preview...",
        "status_preview_ready": "Live preview ready — click Upscale for full resolution",
        "before_tag": "Original",
        "after_tag": "Preview",
        "after_final_tag": "Result",
        "save_success": "Image exported successfully",
        "copied_clipboard": "Copied to clipboard",
        "batch_add_files": "Add Images",
        "batch_add_folder": "Add Folder",
        "batch_clear": "Clear Queue",
        "batch_out_dir": "Output",
        "batch_start": "Start Batch",
        "no_image": "Please open an image first.",
        "loading_title": "Processing Image",
        "loading_subtitle": "Enhancing resolution...",
        "empty_title": "Drop an image here, click to open, or press Ctrl+V",
        "empty_sub": "Supports PNG, JPG, WEBP, BMP, TIFF",
        "theme_light": "☀ Light",
        "theme_dark": "🌙 Dark"
    },
    "es": {
        "title": "Aupscaler",
        "tab_single": "Individual",
        "tab_batch": "Lotes",
        "btn_browse": "Abrir",
        "btn_paste": "Pegar",
        "btn_sample": "Muestra",
        "btn_clear": "Limpiar",
        "card_source": "Origen",
        "card_scale": "Escala",
        "custom_scale": "Personalizada",
        "target_dim": "Salida",
        "est_ram": "RAM",
        "card_quality": "Modo de Calidad",
        "card_enhancements": "Mejoras",
        "btn_reset_effects": "Restablecer",
        "feat_deblur": "Enfocar y Nitidez",
        "feat_denoise": "Reducir Ruido",
        "feat_hdr": "Equilibrio de Tono y Color",
        "feat_bg": "Quitar Fondo",
        "card_format": "Formato",
        "btn_upscale": "Escalar Imagen",
        "btn_enhance_only": "Aplicar Mejoras",
        "btn_save": "Exportar",
        "btn_copy": "Copiar",
        "btn_compare": "Comparar",
        "btn_fit": "Ajustar",
        "btn_cancel": "Cancelar",
        "status_ready": "Listo",
        "status_loading": "Cargando imagen...",
        "status_processing": "Procesando...",
        "status_done": "Escalado completo",
        "status_cancelled": "Cancelado",
        "status_preview_busy": "Actualizando vista previa...",
        "status_preview_ready": "Vista previa lista — pulsa Escalar para resolución completa",
        "before_tag": "Original",
        "after_tag": "Vista previa",
        "after_final_tag": "Resultado",
        "save_success": "Imagen exportada correctamente",
        "copied_clipboard": "Copiada al portapapeles",
        "batch_add_files": "Añadir Imágenes",
        "batch_add_folder": "Añadir Carpeta",
        "batch_clear": "Limpiar Cola",
        "batch_out_dir": "Destino",
        "batch_start": "Iniciar Lote",
        "no_image": "Por favor abre una imagen primero.",
        "loading_title": "Procesando Imagen",
        "loading_subtitle": "Mejorando resolución...",
        "empty_title": "Arrastra una imagen, haz clic para abrir o Ctrl+V",
        "empty_sub": "Compatible con PNG, JPG, WEBP, BMP, TIFF",
        "theme_light": "☀ Claro",
        "theme_dark": "🌙 Oscuro"
    },
    "fr": {
        "title": "Aupscaler",
        "tab_single": "Unique",
        "tab_batch": "Lots",
        "btn_browse": "Ouvrir",
        "btn_paste": "Coller",
        "btn_sample": "Exemple",
        "btn_clear": "Effacer",
        "card_source": "Source",
        "card_scale": "Échelle",
        "custom_scale": "Libre",
        "target_dim": "Sortie",
        "est_ram": "RAM",
        "card_quality": "Qualité",
        "card_enhancements": "Améliorations",
        "btn_reset_effects": "Réinitialiser",
        "feat_deblur": "Netteté et Défloutage",
        "feat_denoise": "Réduire le Bruit",
        "feat_hdr": "Équilibre Ton & Couleur",
        "feat_bg": "Supprimer l'Arrière-Plan",
        "card_format": "Format",
        "btn_upscale": "Agrandir l'Image",
        "btn_enhance_only": "Appliquer les Améliorations",
        "btn_save": "Exporter",
        "btn_copy": "Copier",
        "btn_compare": "Comparer",
        "btn_fit": "Ajuster",
        "btn_cancel": "Annuler",
        "status_ready": "Prêt",
        "status_loading": "Chargement...",
        "status_processing": "Traitement...",
        "status_done": "Traitement terminé",
        "status_cancelled": "Annulé",
        "status_preview_busy": "Aperçu en cours...",
        "status_preview_ready": "Aperçu prêt — cliquez sur Agrandir pour la pleine résolution",
        "before_tag": "Original",
        "after_tag": "Aperçu",
        "after_final_tag": "Résultat",
        "save_success": "Image exportée avec succès",
        "copied_clipboard": "Copiée dans le presse-papiers",
        "batch_add_files": "Ajouter Images",
        "batch_add_folder": "Ajouter Dossier",
        "batch_clear": "Vider",
        "batch_out_dir": "Sortie",
        "batch_start": "Démarrer le Lot",
        "no_image": "Veuillez d'abord ouvrir une image.",
        "loading_title": "Traitement en cours",
        "loading_subtitle": "Amélioration de la résolution...",
        "empty_title": "Déposez une image ici, cliquez ou appuyez sur Ctrl+V",
        "empty_sub": "Formats PNG, JPG, WEBP, BMP, TIFF",
        "theme_light": "☀ Clair",
        "theme_dark": "🌙 Sombre"
    },
    "de": {
        "title": "Aupscaler",
        "tab_single": "Einzeln",
        "tab_batch": "Stapel",
        "btn_browse": "Öffnen",
        "btn_paste": "Einfügen",
        "btn_sample": "Beispiel",
        "btn_clear": "Löschen",
        "card_source": "Quelle",
        "card_scale": "Faktor",
        "custom_scale": "Eigen",
        "target_dim": "Ausgabe",
        "est_ram": "RAM",
        "card_quality": "Qualitätsmodus",
        "card_enhancements": "Optimierungen",
        "btn_reset_effects": "Zurücksetzen",
        "feat_deblur": "Schärfen & Entschärfen",
        "feat_denoise": "Rauschen reduzieren",
        "feat_hdr": "Ton & Farbe ausgleichen",
        "feat_bg": "Hintergrund entfernen",
        "card_format": "Format",
        "btn_upscale": "Bild vergrößern",
        "btn_enhance_only": "Optimierungen anwenden",
        "btn_save": "Exportieren",
        "btn_copy": "Kopieren",
        "btn_compare": "Vergleich",
        "btn_fit": "Einpassen",
        "btn_cancel": "Abbrechen",
        "status_ready": "Bereit",
        "status_loading": "Bild wird geladen...",
        "status_processing": "Verarbeitung...",
        "status_done": "Fertiggestellt",
        "status_cancelled": "Abgebrochen",
        "status_preview_busy": "Vorschau wird aktualisiert...",
        "status_preview_ready": "Vorschau bereit — für volle Auflösung vergrößern",
        "before_tag": "Original",
        "after_tag": "Vorschau",
        "after_final_tag": "Ergebnis",
        "save_success": "Bild erfolgreich exportiert",
        "copied_clipboard": "In Zwischenablage kopiert",
        "batch_add_files": "Bilder hinzufügen",
        "batch_add_folder": "Ordner hinzufügen",
        "batch_clear": "Leeren",
        "batch_out_dir": "Ziel",
        "batch_start": "Stapel starten",
        "no_image": "Bitte zuerst ein Bild öffnen.",
        "loading_title": "Bild wird verarbeitet",
        "loading_subtitle": "Auflösung wird erhöht...",
        "empty_title": "Bild hierher ziehen, klicken oder Strg+V drücken",
        "empty_sub": "Unterstützt PNG, JPG, WEBP, BMP, TIFF",
        "theme_light": "☀ Hell",
        "theme_dark": "🌙 Dunkel"
    },
    "ja": {
        "title": "Aupscaler",
        "tab_single": "単一画像",
        "tab_batch": "一括処理",
        "btn_browse": "開く",
        "btn_paste": "貼り付け",
        "btn_sample": "サンプル",
        "btn_clear": "クリア",
        "card_source": "ソース",
        "card_scale": "拡大率",
        "custom_scale": "カスタム",
        "target_dim": "出力サイズ",
        "est_ram": "メモリ",
        "card_quality": "画質モード",
        "card_enhancements": "画質補正",
        "btn_reset_effects": "リセット",
        "feat_deblur": "シャープ＆ボケ補正",
        "feat_denoise": "ノイズ除去",
        "feat_hdr": "トーン＆色補正",
        "feat_bg": "背景透過",
        "card_format": "形式",
        "btn_upscale": "画像を拡大",
        "btn_enhance_only": "補正を適用",
        "btn_save": "書き出し",
        "btn_copy": "コピー",
        "btn_compare": "比較",
        "btn_fit": "全体",
        "btn_cancel": "中止",
        "status_ready": "準備完了",
        "status_loading": "読み込み中...",
        "status_processing": "処理中...",
        "status_done": "完了しました",
        "status_cancelled": "キャンセル済み",
        "status_preview_busy": "プレビュー更新中...",
        "status_preview_ready": "プレビュー完了 — フル解像度には拡大を実行",
        "before_tag": "元画像",
        "after_tag": "プレビュー",
        "after_final_tag": "結果",
        "save_success": "画像を保存しました",
        "copied_clipboard": "クリップボードにコピーしました",
        "batch_add_files": "画像追加",
        "batch_add_folder": "フォルダ追加",
        "batch_clear": "クリア",
        "batch_out_dir": "出力先",
        "batch_start": "一括開始",
        "no_image": "先に画像を開いてください。",
        "loading_title": "画像を処理中",
        "loading_subtitle": "高解像度化を実行中...",
        "empty_title": "画像をドロップ、クリックして開く、または Ctrl+V",
        "empty_sub": "PNG, JPG, WEBP, BMP, TIFF 対応",
        "theme_light": "☀ ライト",
        "theme_dark": "🌙 ダーク"
    },
    "zh": {
        "title": "Aupscaler",
        "tab_single": "单张",
        "tab_batch": "批量",
        "btn_browse": "打开",
        "btn_paste": "粘贴",
        "btn_sample": "示例",
        "btn_clear": "清空",
        "card_source": "图像源",
        "card_scale": "缩放倍率",
        "custom_scale": "自定义",
        "target_dim": "输出尺寸",
        "est_ram": "内存",
        "card_quality": "画质模式",
        "card_enhancements": "画质增强",
        "btn_reset_effects": "重置",
        "feat_deblur": "锐化去模糊",
        "feat_denoise": "降噪处理",
        "feat_hdr": "色调与色彩平衡",
        "feat_bg": "移除背景",
        "card_format": "格式",
        "btn_upscale": "放大图像",
        "btn_enhance_only": "应用增强",
        "btn_save": "导出",
        "btn_copy": "复制",
        "btn_compare": "对比",
        "btn_fit": "适应",
        "btn_cancel": "取消",
        "status_ready": "就绪",
        "status_loading": "正在加载...",
        "status_processing": "处理中...",
        "status_done": "放大完成",
        "status_cancelled": "已取消",
        "status_preview_busy": "正在生成预览...",
        "status_preview_ready": "实时预览已就绪 — 点击放大获取完整分辨率",
        "before_tag": "原图",
        "after_tag": "预览",
        "after_final_tag": "结果",
        "save_success": "图片导出成功",
        "copied_clipboard": "已复制到剪贴板",
        "batch_add_files": "添加图片",
        "batch_add_folder": "添加文件夹",
        "batch_clear": "清空列表",
        "batch_out_dir": "输出目录",
        "batch_start": "开始批量",
        "no_image": "请先打开一张图片。",
        "loading_title": "正在处理图像",
        "loading_subtitle": "正在提升图像分辨率...",
        "empty_title": "拖放图片到此处、点击打开或按 Ctrl+V 粘贴",
        "empty_sub": "支持 PNG, JPG, WEBP, BMP, TIFF",
        "theme_light": "☀ 浅色",
        "theme_dark": "🌙 深色"
    },
    "fa": {
        "title": "Aupscaler",
        "tab_single": "تک تصویر",
        "tab_batch": "گروهی",
        "btn_browse": "باز کردن",
        "btn_paste": "چسباندن",
        "btn_sample": "نمونه",
        "btn_clear": "پاک کردن",
        "card_source": "تصویر ورودی",
        "card_scale": "مقیاس",
        "custom_scale": "دلخواه",
        "target_dim": "خروجی",
        "est_ram": "رم",
        "card_quality": "حالت کیفیت",
        "card_enhancements": "بهینه‌سازی",
        "btn_reset_effects": "بازنشانی",
        "feat_deblur": "شفاف‌سازی و رفع تاری",
        "feat_denoise": "کاهش نویز",
        "feat_hdr": "تعادل نور و رنگ",
        "feat_bg": "حذف پس‌زمینه",
        "card_format": "فرمت",
        "btn_upscale": "افزایش کیفیت",
        "btn_enhance_only": "اعمال تغییرات",
        "btn_save": "ذخیره",
        "btn_copy": "کپی",
        "btn_compare": "مقایسه",
        "btn_fit": "تناسب",
        "btn_cancel": "لغو",
        "status_ready": "آماده",
        "status_loading": "در حال بارگذاری...",
        "status_processing": "در حال پردازش...",
        "status_done": "پردازش تکمیل شد",
        "status_cancelled": "لغو شد",
        "status_preview_busy": "به‌روزرسانی پیش‌نمایش...",
        "status_preview_ready": "پیش‌نمایش آماده است — برای خروجی کامل دکمه اجرا را بزنید",
        "before_tag": "اصلی",
        "after_tag": "پیش‌نمایش",
        "after_final_tag": "نتیجه",
        "save_success": "تصویر با موفقیت ذخیره شد",
        "copied_clipboard": "در کلیپ‌بورد کپی شد",
        "batch_add_files": "افزودن تصاویر",
        "batch_add_folder": "افزودن پوشه",
        "batch_clear": "پاکسازی لیست",
        "batch_out_dir": "پوشه خروجی",
        "batch_start": "شروع پردازش",
        "no_image": "لطفاً ابتدا یک تصویر باز کنید.",
        "loading_title": "در حال پردازش تصویر",
        "loading_subtitle": "در حال ارتقای رزولوشن...",
        "empty_title": "تصویر را بکشید، کلیک کنید یا Ctrl+V بزنید",
        "empty_sub": "پشتیبانی از PNG, JPG, WEBP, BMP, TIFF",
        "theme_light": "☀ روشن",
        "theme_dark": "🌙 تیره"
    },
    "ar": {
        "title": "Aupscaler",
        "tab_single": "فردي",
        "tab_batch": "دفعي",
        "btn_browse": "فتح",
        "btn_paste": "لصق",
        "btn_sample": "عينة",
        "btn_clear": "مسح",
        "card_source": "المصدر",
        "card_scale": "المقياس",
        "custom_scale": "مخصص",
        "target_dim": "المخرج",
        "est_ram": "الذاكرة",
        "card_quality": "وضع الجودة",
        "card_enhancements": "التحسينات",
        "btn_reset_effects": "إعادة ضبط",
        "feat_deblur": "توضيح وإزالة الضبابية",
        "feat_denoise": "تقليل الضوضاء",
        "feat_hdr": "توازن الإضاءة والألوان",
        "feat_bg": "إزالة الخلفية",
        "card_format": "الصيغة",
        "btn_upscale": "تكبير الصورة",
        "btn_enhance_only": "تطبيق التحسينات",
        "btn_save": "تصدير",
        "btn_copy": "نسخ",
        "btn_compare": "مقارنة",
        "btn_fit": "ملاءمة",
        "btn_cancel": "إلغاء",
        "status_ready": "جاهز",
        "status_loading": "جار التحميل...",
        "status_processing": "جار المعالجة...",
        "status_done": "اكتمل التكبير",
        "status_cancelled": "تم الإلغاء",
        "status_preview_busy": "تحديث المعاينة...",
        "status_preview_ready": "المعاينة جاهزة — اضغط تكبير للدقة الكاملة",
        "before_tag": "الأصلية",
        "after_tag": "معاينة",
        "after_final_tag": "النتيجة",
        "save_success": "تم تصدير الصورة بنجاح",
        "copied_clipboard": "تم النسخ إلى الحافظة",
        "batch_add_files": "إضافة صور",
        "batch_add_folder": "إضافة مجلد",
        "batch_clear": "مسح القائمة",
        "batch_out_dir": "الإخراج",
        "batch_start": "بدء الدفعة",
        "no_image": "يرجى فتح صورة أولاً.",
        "loading_title": "جار معالجة الصورة",
        "loading_subtitle": "جار تحسين الدقة...",
        "empty_title": "اسحب صورة هنا، انقر للفتح، أو اضغط Ctrl+V",
        "empty_sub": "يدعم PNG, JPG, WEBP, BMP, TIFF",
        "theme_light": "☀ فاتح",
        "theme_dark": "🌙 داكن"
    },
    "ru": {
        "title": "Aupscaler",
        "tab_single": "Фото",
        "tab_batch": "Пакет",
        "btn_browse": "Открыть",
        "btn_paste": "Вставить",
        "btn_sample": "Пример",
        "btn_clear": "Очистить",
        "card_source": "Исходник",
        "card_scale": "Масштаб",
        "custom_scale": "Свой",
        "target_dim": "Выход",
        "est_ram": "ОЗУ",
        "card_quality": "Режим качества",
        "card_enhancements": "Улучшения",
        "btn_reset_effects": "Сброс",
        "feat_deblur": "Резкость и четкость",
        "feat_denoise": "Уменьшение шума",
        "feat_hdr": "Баланс тона и цвета",
        "feat_bg": "Удалить фон",
        "card_format": "Формат",
        "btn_upscale": "Увеличить",
        "btn_enhance_only": "Применить эффекты",
        "btn_save": "Экспорт",
        "btn_copy": "Копия",
        "btn_compare": "Сравнить",
        "btn_fit": "Вписать",
        "btn_cancel": "Отмена",
        "status_ready": "Готов",
        "status_loading": "Загрузка...",
        "status_processing": "Обработка...",
        "status_done": "Готово",
        "status_cancelled": "Отменено",
        "status_preview_busy": "Обновление превью...",
        "status_preview_ready": "Превью готово — нажмите Увеличить для полного результата",
        "before_tag": "Оригинал",
        "after_tag": "Превью",
        "after_final_tag": "Результат",
        "save_success": "Изображение экспортировано",
        "copied_clipboard": "Скопировано в буфер",
        "batch_add_files": "Добавить фото",
        "batch_add_folder": "Добавить папку",
        "batch_clear": "Очистить",
        "batch_out_dir": "Папка",
        "batch_start": "Запустить",
        "no_image": "Сначала откройте изображение.",
        "loading_title": "Обработка изображения",
        "loading_subtitle": "Повышение разрешения...",
        "empty_title": "Перетащите фото сюда, нажмите или Ctrl+V",
        "empty_sub": "PNG, JPG, WEBP, BMP, TIFF",
        "theme_light": "☀ Светлая",
        "theme_dark": "🌙 Тёмная"
    },
    "pt": {
        "title": "Aupscaler",
        "tab_single": "Única",
        "tab_batch": "Lote",
        "btn_browse": "Abrir",
        "btn_paste": "Colar",
        "btn_sample": "Exemplo",
        "btn_clear": "Limpar",
        "card_source": "Origem",
        "card_scale": "Escala",
        "custom_scale": "Livre",
        "target_dim": "Saída",
        "est_ram": "RAM",
        "card_quality": "Modo de Qualidade",
        "card_enhancements": "Aprimoramentos",
        "btn_reset_effects": "Redefinir",
        "feat_deblur": "Nitidez e Desfoque",
        "feat_denoise": "Reduzir Ruído",
        "feat_hdr": "Equilíbrio de Tom e Cor",
        "feat_bg": "Remover Fundo",
        "card_format": "Formato",
        "btn_upscale": "Ampliar Imagem",
        "btn_enhance_only": "Aplicar Melhorias",
        "btn_save": "Exportar",
        "btn_copy": "Copiar",
        "btn_compare": "Comparar",
        "btn_fit": "Ajustar",
        "btn_cancel": "Cancelar",
        "status_ready": "Pronto",
        "status_loading": "Carregando...",
        "status_processing": "Processando...",
        "status_done": "Ampliação concluída",
        "status_cancelled": "Cancelado",
        "status_preview_busy": "Atualizando prévia...",
        "status_preview_ready": "Prévia pronta — clique em Ampliar para resolução total",
        "before_tag": "Original",
        "after_tag": "Prévia",
        "after_final_tag": "Resultado",
        "save_success": "Imagem exportada com sucesso",
        "copied_clipboard": "Copiada para a área de transferência",
        "batch_add_files": "Adicionar Imagens",
        "batch_add_folder": "Adicionar Pasta",
        "batch_clear": "Limpar Fila",
        "batch_out_dir": "Saída",
        "batch_start": "Iniciar Lote",
        "no_image": "Por favor, abra uma imagem primeiro.",
        "loading_title": "Processando Imagem",
        "loading_subtitle": "Melhorando resolução...",
        "empty_title": "Solte uma imagem, clique para abrir ou Ctrl+V",
        "empty_sub": "PNG, JPG, WEBP, BMP, TIFF",
        "theme_light": "☀ Claro",
        "theme_dark": "🌙 Escuro"
    }
}


class AupscalerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.current_theme = "dark"
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title("Aupscaler")
        self.geometry("1360x880")
        self.minsize(1060, 700)

        self.setup_window_icon()

        self.current_lang = "en"
        self.workspace_mode = "single"
        self.current_pil_img = None
        self.preview_src = None
        self.upscaled_pil_img = None
        self.final_pil_img = None
        self.active_filename = "image.png"
        self.image_epoch = 0

        self.cached_disp_w = 0
        self.cached_disp_h = 0
        self.view_key = None
        self.view_before = None
        self.view_after = None
        self.checker_key = None
        self.checker_image = None
        self.render_after_id = None
        self.tk_canvas_img = None

        self.orig_w = 0
        self.orig_h = 0
        self.scale_type = "multiplier"
        self.scale_val = 2.0
        self.split_ratio = 0.5
        self.hold_space_active = False
        self._canvas_press_x = 0
        self._canvas_moved = False

        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.pan_start_x = 0
        self.pan_start_y = 0

        self.is_processing = False
        self.cancel_event = threading.Event()
        self.load_token = 0
        self.preview_gen = 0
        self.preview_busy = False
        self.preview_after_id = None
        self.theme_animating = False
        self.loading_start_time = 0.0
        self.loading_timer_id = None
        self.batch_file_list: List[str] = []
        self.batch_output_dir = os.path.join(os.path.expanduser("~"), "Pictures", "aupscaler_output")
        self._main_queue = queue.Queue()
        self._poll_id = None
        self._poll_main_queue()

        self.preset_btn_map = {}

        self.setup_ui()
        self.setup_crashproof_drag_and_drop()
        self.setup_keyboard_shortcuts()
        self.update_translations()
        self.update_stats()

        threading.Thread(target=UpscalerEngine.warm_up, daemon=True).start()

    def post_to_main(self, func, *args, **kwargs):
        self._main_queue.put((func, args, kwargs))

    def _drain_main_queue(self):
        while True:
            try:
                func, args, kwargs = self._main_queue.get_nowait()
            except queue.Empty:
                break
            try:
                func(*args, **kwargs)
            except Exception:
                pass

    def _poll_main_queue(self):
        self._drain_main_queue()
        try:
            self._poll_id = self.after(16, self._poll_main_queue)
        except Exception:
            pass

    def update(self):
        self._drain_main_queue()
        return super().update()

    def destroy(self):
        self.cancel_event.set()
        self.cancel_preview()
        if self._poll_id is not None:
            try:
                self.after_cancel(self._poll_id)
            except Exception:
                pass
            self._poll_id = None
        super().destroy()

    def get_ui_font(self, size: int = 12, weight: str = "normal") -> ctk.CTkFont:
        if self.current_lang in ("fa", "ar"):
            family = "A Nafis"
            size = size + 3
        else:
            family = "Segoe UI"
        return ctk.CTkFont(family=family, size=size, weight=weight)

    def _theme_label(self, theme: str) -> str:
        return self.t("theme_light") if theme == "light" else self.t("theme_dark")

    def on_theme_switch(self, selected: str):
        target = "light" if selected == self.t("theme_light") else "dark"
        self.set_theme(target)

    def set_theme(self, target_theme: str):
        if target_theme not in ("light", "dark") or target_theme == self.current_theme or self.theme_animating:
            if hasattr(self, "theme_switch"):
                self.theme_switch.set(self._theme_label(self.current_theme))
            return
        self.theme_animating = True
        self._pending_theme = target_theme
        self._fade_step(1.0, 0.85, -0.04, self._apply_theme_switch)

    def toggle_theme(self):
        target = "light" if self.current_theme == "dark" else "dark"
        self.set_theme(target)

    def _fade_step(self, value, limit, delta, on_done):
        value += delta
        reached = value <= limit if delta < 0 else value >= limit
        if reached:
            value = limit
        try:
            self.attributes("-alpha", value)
        except tk.TclError:
            on_done()
            return
        if reached:
            on_done()
        else:
            self.after(12, self._fade_step, value, limit, delta, on_done)

    def _apply_theme_switch(self):
        target_theme = getattr(self, "_pending_theme", "light" if self.current_theme == "dark" else "dark")
        self.current_theme = target_theme

        ctk.set_appearance_mode("Dark" if target_theme == "dark" else "Light")
        if hasattr(self, "theme_switch"):
            self.theme_switch.set(self._theme_label(target_theme))
        self.canvas.configure(bg=THEME_COLORS["canvas_bg_hex"][target_theme])

        self.view_key = None
        self.checker_key = None
        self.update_idletasks()
        self.schedule_redraw()
        self._fade_step(0.85, 1.0, 0.04, self._finish_theme_animation)

    def _finish_theme_animation(self):
        self.theme_animating = False

    def toggle_compare_view(self):
        if self.current_pil_img is None:
            return
        self.hold_space_active = not self.hold_space_active
        self._sync_compare_button()
        self.redraw_comparison()

    def _sync_compare_button(self):
        if not hasattr(self, "btn_compare") or not self.btn_compare.winfo_exists():
            return
        if self.hold_space_active:
            self.btn_compare.configure(
                fg_color=THEME_COLORS["accent"],
                hover_color=THEME_COLORS["accent_hover"],
                text_color="#ffffff",
                border_color=THEME_COLORS["accent"]
            )
        else:
            self.btn_compare.configure(
                fg_color=THEME_COLORS["btn_secondary"],
                hover_color=THEME_COLORS["btn_secondary_hover"],
                text_color=THEME_COLORS["text_primary"],
                border_color=THEME_COLORS["border"]
            )

    def reset_effects(self):
        for switch in (self.switch_deblur, self.switch_denoise, self.switch_hdr, self.switch_bg):
            switch.deselect()
        self.on_settings_changed()

    def on_bg_toggled(self):
        if self.switch_bg.get() == 1:
            self.fmt_selector.set("PNG")
        self.on_tool_toggled()

    def on_settings_changed(self):
        self.invalidate_final_result()
        self.request_preview()

    def _set_export_enabled(self, enabled: bool):
        if enabled:
            self.btn_save.configure(
                state="normal",
                fg_color=THEME_COLORS["accent"],
                hover_color=THEME_COLORS["accent_hover"],
                text_color="#ffffff",
                border_width=0
            )
        else:
            self.btn_save.configure(
                state="disabled",
                fg_color=THEME_COLORS["bg_card_sub"],
                text_color_disabled=THEME_COLORS["text_muted"],
                border_width=1,
                border_color=THEME_COLORS["border"]
            )

    def invalidate_final_result(self):
        if self.final_pil_img is None:
            return
        self.final_pil_img = None
        self._set_export_enabled(False)
        self.btn_copy.configure(state="disabled")

    def setup_window_icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
        png_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.isfile(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
        if os.path.isfile(png_path):
            try:
                img = Image.open(png_path)
                self.tk_icon = ImageTk.PhotoImage(img)
                self.iconphoto(False, self.tk_icon)
            except Exception:
                pass

    def setup_crashproof_drag_and_drop(self):
        if not WINDND_AVAILABLE:
            return

        def _windnd_callback(files):
            try:
                if not files:
                    return
                decoded_paths = []
                for raw in files:
                    try:
                        if isinstance(raw, bytes):
                            try:
                                p = raw.decode("utf-8")
                            except UnicodeDecodeError:
                                p = raw.decode(sys.getfilesystemencoding(), errors="replace")
                        else:
                            p = str(raw)
                        p = os.path.abspath(p.strip().strip('"'))
                        if os.path.exists(p):
                            decoded_paths.append(p)
                    except Exception:
                        pass

                if not decoded_paths:
                    return

                self.post_to_main(self._safe_handle_dropped_paths, decoded_paths)
            except Exception:
                pass

        try:
            windnd.hook_dropfiles(self, func=_windnd_callback)
        except Exception:
            pass

    def _safe_handle_dropped_paths(self, paths: List[str]):
        try:
            expanded_files = []
            for p in paths:
                if os.path.isdir(p):
                    for root, _, files in os.walk(p):
                        for f in files:
                            ext = os.path.splitext(f)[1].lower()
                            if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"]:
                                expanded_files.append(os.path.join(root, f))
                elif os.path.isfile(p):
                    ext = os.path.splitext(p)[1].lower()
                    if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"]:
                        expanded_files.append(p)

            if not expanded_files:
                return

            if len(expanded_files) == 1:
                self.switch_workspace_mode("single")
                self.load_image_from_path(expanded_files[0])
            else:
                self.switch_workspace_mode("batch")
                self.add_paths_to_batch_queue(expanded_files)
        except Exception:
            pass

    def setup_keyboard_shortcuts(self):
        self.bind("<Control-v>", self._shortcut_paste)
        self.bind("<Control-V>", self._shortcut_paste)
        self.bind("<Control-c>", self._shortcut_copy)
        self.bind("<Control-C>", self._shortcut_copy)
        self.bind("<Control-o>", lambda e: self.browse_file())
        self.bind("<Control-O>", lambda e: self.browse_file())
        self.bind("<Control-s>", lambda e: self.save_image())
        self.bind("<Control-S>", lambda e: self.save_image())

        self.bind("<KeyPress-space>", self.on_space_press)
        self.bind("<KeyRelease-space>", self.on_space_release)

    def _text_input_focused(self) -> bool:
        try:
            widget = self.focus_get()
        except KeyError:
            return False
        return isinstance(widget, (tk.Entry, tk.Text))

    def _shortcut_paste(self, event=None):
        if not self._text_input_focused():
            self.paste_from_clipboard()

    def _shortcut_copy(self, event=None):
        if not self._text_input_focused():
            self.copy_to_clipboard()

    def on_space_press(self, event):
        if self.hold_space_active or self.current_pil_img is None or self._text_input_focused():
            return
        self.hold_space_active = True
        self._sync_compare_button()
        self.redraw_comparison()

    def on_space_release(self, event):
        if self.hold_space_active:
            self.hold_space_active = False
            self._sync_compare_button()
            self.redraw_comparison()

    def t(self, key: str) -> str:
        lang_dict = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["en"])
        return lang_dict.get(key, TRANSLATIONS["en"].get(key, key))

    def setup_ui(self):
        self.configure(fg_color=THEME_COLORS["bg_root"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        self.setup_header_bar()

        self.workspace_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.workspace_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.workspace_frame.grid_rowconfigure(0, weight=1)
        self.workspace_frame.grid_columnconfigure(0, weight=0)
        self.workspace_frame.grid_columnconfigure(1, weight=1)

        self.setup_sidebar()
        self.setup_main_panel()

    def setup_header_bar(self):
        self.header_bar = ctk.CTkFrame(
            self, height=54, corner_radius=0,
            fg_color=THEME_COLORS["bg_header"],
            border_width=1, border_color=THEME_COLORS["border"]
        )
        self.header_bar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.header_bar.grid_propagate(False)

        header_left = ctk.CTkFrame(self.header_bar, fg_color="transparent")
        header_left.pack(side="left", padx=(14, 10), pady=8)

        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.isfile(logo_path):
            try:
                pil_logo = Image.open(logo_path).resize((24, 24), Image.Resampling.LANCZOS)
                self.header_logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(24, 24))
                self.header_logo_lbl = ctk.CTkLabel(header_left, image=self.header_logo_img, text="")
                self.header_logo_lbl.pack(side="left", padx=(0, 8))
            except Exception:
                pass

        self.app_title_lbl = ctk.CTkLabel(
            header_left, text="Aupscaler", font=self.get_ui_font(16, "bold"),
            text_color=THEME_COLORS["text_primary"], anchor="w"
        )
        self.app_title_lbl.pack(side="left", padx=(0, 14))

        self.mode_switch = ctk.CTkSegmentedButton(
            header_left,
            values=[self.t("tab_single"), self.t("tab_batch")],
            command=self.on_mode_switch,
            height=30,
            corner_radius=8,
            fg_color=THEME_COLORS["bg_card_sub"],
            selected_color=THEME_COLORS["seg_selected"],
            selected_hover_color=THEME_COLORS["seg_selected_hover"],
            unselected_color=THEME_COLORS["bg_card_sub"],
            unselected_hover_color=THEME_COLORS["btn_secondary_hover"],
            text_color=THEME_COLORS["text_primary"],
            font=self.get_ui_font(12, "bold")
        )
        self.mode_switch.set(self.t("tab_single"))
        self.mode_switch.pack(side="left")

        header_center = ctk.CTkFrame(self.header_bar, fg_color="transparent")
        header_center.pack(side="left", padx=16, fill="x", expand=True)

        self.status_lbl = ctk.CTkLabel(
            header_center, text="Ready", font=self.get_ui_font(11),
            text_color=THEME_COLORS["text_secondary"], anchor="center"
        )
        self.status_lbl.pack(side="left", expand=True, fill="x")

        self.progress_bar = ctk.CTkProgressBar(
            header_center, width=120, height=5,
            progress_color=THEME_COLORS["accent"],
            fg_color=THEME_COLORS["bg_card_sub"]
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(side="right", padx=(8, 0))

        header_right = ctk.CTkFrame(self.header_bar, fg_color="transparent")
        header_right.pack(side="right", padx=(10, 14), pady=8)

        self.theme_switch = ctk.CTkSegmentedButton(
            header_right,
            values=[self.t("theme_light"), self.t("theme_dark")],
            command=self.on_theme_switch,
            height=30,
            corner_radius=8,
            fg_color=THEME_COLORS["bg_card_sub"],
            selected_color=THEME_COLORS["seg_selected"],
            selected_hover_color=THEME_COLORS["seg_selected_hover"],
            unselected_color=THEME_COLORS["bg_card_sub"],
            unselected_hover_color=THEME_COLORS["btn_secondary_hover"],
            text_color=THEME_COLORS["text_primary"],
            font=self.get_ui_font(11, "bold")
        )
        self.theme_switch.set(self._theme_label(self.current_theme))
        self.theme_switch.pack(side="left", padx=(0, 8))

        self.lang_menu = ctk.CTkOptionMenu(
            header_right,
            values=[
                "English (en)", "فارسی (fa)", "العربية (ar)", "Español (es)", "Français (fr)",
                "Deutsch (de)", "日本語 (ja)", "中文 (zh)", "Русский (ru)", "Português (pt)"
            ],
            command=self.on_lang_changed,
            width=112, height=30,
            fg_color=THEME_COLORS["opt_bg"],
            button_color=THEME_COLORS["opt_btn"],
            button_hover_color=THEME_COLORS["opt_btn_hover"],
            dropdown_fg_color=THEME_COLORS["opt_bg"],
            dropdown_text_color=THEME_COLORS["text_primary"],
            text_color=THEME_COLORS["text_primary"],
            font=self.get_ui_font(11), corner_radius=8,
            dropdown_font=self.get_ui_font(11)
        )
        self.lang_menu.pack(side="left", padx=(0, 8))

        self.btn_browse = ctk.CTkButton(
            header_right, text="+ Open", command=self._on_header_open_click,
            width=82, height=30, fg_color=THEME_COLORS["btn_secondary"],
            hover_color=THEME_COLORS["btn_secondary_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text_primary"], font=self.get_ui_font(12, "bold"), corner_radius=8
        )
        self.btn_browse.pack(side="left", padx=(0, 6))

        self.btn_save = ctk.CTkButton(
            header_right, text="Export", command=self.save_image,
            width=86, height=30, fg_color=THEME_COLORS["bg_card_sub"],
            hover_color=THEME_COLORS["accent_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color="#ffffff", text_color_disabled=THEME_COLORS["text_muted"],
            font=self.get_ui_font(12, "bold"), corner_radius=8,
            state="disabled"
        )
        self.btn_save.pack(side="left")
        self._set_export_enabled(False)

    def _on_header_open_click(self):
        if self.workspace_mode == "batch":
            self.batch_browse_files()
        else:
            self.browse_file()

    def on_mode_switch(self, value: str):
        target = "batch" if value == self.t("tab_batch") else "single"
        self.switch_workspace_mode(target)

    def switch_workspace_mode(self, mode: str):
        self.workspace_mode = "batch" if mode == "batch" else "single"
        if self.workspace_mode == "batch":
            self.single_view_frame.grid_forget()
            self.batch_view_frame.grid(row=0, column=0, sticky="nsew")
            self.mode_switch.set(self.t("tab_batch"))
        else:
            self.batch_view_frame.grid_forget()
            self.single_view_frame.grid(row=0, column=0, sticky="nsew")
            self.mode_switch.set(self.t("tab_single"))

    def setup_sidebar(self):
        self.sidebar = ctk.CTkScrollableFrame(
            self.workspace_frame, width=286, corner_radius=0,
            fg_color=THEME_COLORS["bg_sidebar"],
            border_width=1, border_color=THEME_COLORS["border"],
            scrollbar_button_color=THEME_COLORS["scrollbar"],
            scrollbar_button_hover_color=THEME_COLORS["scrollbar_hover"]
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.source_card = self._create_card(self.sidebar)
        src_hdr = ctk.CTkFrame(self.source_card, fg_color="transparent")
        src_hdr.pack(fill="x", padx=12, pady=(10, 4))
        self.source_sec_lbl = ctk.CTkLabel(
            src_hdr, text=self.t("card_source"), font=self.get_ui_font(12, "bold"),
            text_color=THEME_COLORS["text_primary"], anchor="w"
        )
        self.source_sec_lbl.pack(side="left")

        self.img_info_lbl = ctk.CTkLabel(
            self.source_card, text="No image loaded", font=self.get_ui_font(11),
            text_color=THEME_COLORS["text_muted"], justify="left", anchor="w", wraplength=246
        )
        self.img_info_lbl.pack(fill="x", padx=12, pady=(0, 8))

        src_btns = ctk.CTkFrame(self.source_card, fg_color="transparent")
        src_btns.pack(fill="x", padx=10, pady=(0, 10))
        src_btns.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_paste = ctk.CTkButton(
            src_btns, text="Paste", command=self.paste_from_clipboard,
            height=28, fg_color=THEME_COLORS["btn_secondary"],
            hover_color=THEME_COLORS["btn_secondary_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text_primary"], font=self.get_ui_font(11), corner_radius=6
        )
        self.btn_paste.grid(row=0, column=0, padx=2, sticky="ew")

        self.btn_sample = ctk.CTkButton(
            src_btns, text="Sample", command=self.load_sample_image,
            height=28, fg_color=THEME_COLORS["btn_secondary"],
            hover_color=THEME_COLORS["btn_secondary_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text_primary"], font=self.get_ui_font(11), corner_radius=6
        )
        self.btn_sample.grid(row=0, column=1, padx=2, sticky="ew")

        self.btn_clear = ctk.CTkButton(
            src_btns, text="Clear", command=self.clear_image,
            height=28, fg_color=THEME_COLORS["btn_secondary"],
            hover_color=THEME_COLORS["danger_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["danger"], font=self.get_ui_font(11), corner_radius=6
        )
        self.btn_clear.grid(row=0, column=2, padx=2, sticky="ew")

        self.scale_card = self._create_card(self.sidebar)
        scale_hdr = ctk.CTkFrame(self.scale_card, fg_color="transparent")
        scale_hdr.pack(fill="x", padx=12, pady=(10, 6))

        self.scale_sec_lbl = ctk.CTkLabel(
            scale_hdr, text=self.t("card_scale"), font=self.get_ui_font(12, "bold"),
            text_color=THEME_COLORS["text_primary"], anchor="w"
        )
        self.scale_sec_lbl.pack(side="left")

        self.target_dim_lbl = ctk.CTkLabel(
            scale_hdr, text="—",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=THEME_COLORS["accent"], anchor="e"
        )
        self.target_dim_lbl.pack(side="right")

        mult_row = ctk.CTkFrame(self.scale_card, fg_color="transparent")
        mult_row.pack(fill="x", padx=10, pady=(0, 8))
        mult_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

        for idx, val in enumerate((1, 2, 3, 4)):
            btn = ctk.CTkButton(
                mult_row, text=f"{val}×", height=34,
                fg_color=THEME_COLORS["accent"] if val == 2 else THEME_COLORS["btn_secondary"],
                hover_color=THEME_COLORS["accent"],
                border_width=1,
                border_color=THEME_COLORS["accent"] if val == 2 else THEME_COLORS["border"],
                text_color="#ffffff" if val == 2 else THEME_COLORS["text_primary"],
                font=self.get_ui_font(12, "bold"), corner_radius=8,
                command=lambda v=val: self.select_preset(v)
            )
            btn.grid(row=0, column=idx, padx=2, sticky="ew")
            self.preset_btn_map[f"mult_{val}"] = btn

        custom_row = ctk.CTkFrame(self.scale_card, fg_color="transparent")
        custom_row.pack(fill="x", padx=12, pady=(0, 10))

        self.custom_scale_lbl = ctk.CTkLabel(
            custom_row, text="Custom:", font=self.get_ui_font(11),
            text_color=THEME_COLORS["text_secondary"]
        )
        self.custom_scale_lbl.pack(side="left", padx=(0, 6))

        self.custom_entry = ctk.CTkEntry(
            custom_row, height=28, width=56,
            fg_color=THEME_COLORS["bg_card_sub"], border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text_primary"], font=self.get_ui_font(11), corner_radius=6
        )
        self.custom_entry.insert(0, "2")
        self.custom_entry.pack(side="left")
        self.custom_entry.bind("<KeyRelease>", lambda e: self.on_custom_scale_changed(clamp_entry=False))
        self.custom_entry.bind("<FocusOut>", lambda e: self.on_custom_scale_changed(clamp_entry=True))
        self.custom_entry.bind("<Return>", lambda e: self.on_custom_scale_changed(clamp_entry=True))

        ctk.CTkLabel(
            custom_row, text="× (1–8)", font=self.get_ui_font(10),
            text_color=THEME_COLORS["text_muted"]
        ).pack(side="left", padx=(5, 0))

        self.est_ram_lbl = ctk.CTkLabel(
            custom_row, text="", font=self.get_ui_font(10),
            text_color=THEME_COLORS["text_muted"], anchor="e"
        )
        self.est_ram_lbl.pack(side="right")

        self.quality_card = self._create_card(self.sidebar)
        self.algo_lbl = ctk.CTkLabel(
            self.quality_card, text=self.t("card_quality"), font=self.get_ui_font(12, "bold"),
            text_color=THEME_COLORS["text_primary"], anchor="w"
        )
        self.algo_lbl.pack(fill="x", padx=12, pady=(10, 6))

        self.algo_menu = ctk.CTkOptionMenu(
            self.quality_card,
            values=[item[0] for item in ALGO_CHOICES],
            command=self._on_algo_changed,
            height=32,
            fg_color=THEME_COLORS["opt_bg"],
            button_color=THEME_COLORS["opt_btn"],
            button_hover_color=THEME_COLORS["opt_btn_hover"],
            dropdown_fg_color=THEME_COLORS["opt_bg"],
            dropdown_text_color=THEME_COLORS["text_primary"],
            text_color=THEME_COLORS["text_primary"],
            font=self.get_ui_font(11, "bold"), corner_radius=8
        )
        self.algo_menu.set(ALGO_CHOICES[0][0])
        self.algo_menu.pack(fill="x", padx=12, pady=(0, 6))

        self.algo_desc_lbl = ctk.CTkLabel(
            self.quality_card, text=ALGO_CHOICES[0][2], font=self.get_ui_font(10),
            text_color=THEME_COLORS["text_muted"], anchor="w", justify="left", wraplength=242
        )
        self.algo_desc_lbl.pack(fill="x", padx=12, pady=(0, 10))

        self.enhance_card = self._create_card(self.sidebar)
        enh_hdr = ctk.CTkFrame(self.enhance_card, fg_color="transparent")
        enh_hdr.pack(fill="x", padx=12, pady=(10, 6))

        self.pro_sec_lbl = ctk.CTkLabel(
            enh_hdr, text=self.t("card_enhancements"), font=self.get_ui_font(12, "bold"),
            text_color=THEME_COLORS["text_primary"], anchor="w"
        )
        self.pro_sec_lbl.pack(side="left")

        self.btn_reset_fx_sidebar = ctk.CTkButton(
            enh_hdr, text=self.t("btn_reset_effects"), width=56, height=24,
            fg_color=THEME_COLORS["btn_secondary"], hover_color=THEME_COLORS["btn_secondary_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text_secondary"], font=self.get_ui_font(10, "bold"), corner_radius=6,
            command=self.reset_effects
        )
        self.btn_reset_fx_sidebar.pack(side="right")

        self.switch_deblur = ctk.CTkSwitch(
            self.enhance_card, text=self.t("feat_deblur"), font=self.get_ui_font(12),
            text_color=THEME_COLORS["text_primary"], progress_color=THEME_COLORS["accent"],
            command=self.on_tool_toggled
        )
        self.switch_deblur.pack(fill="x", padx=12, pady=(2, 8))

        self.switch_denoise = ctk.CTkSwitch(
            self.enhance_card, text=self.t("feat_denoise"), font=self.get_ui_font(12),
            text_color=THEME_COLORS["text_primary"], progress_color=THEME_COLORS["accent"],
            command=self.on_tool_toggled
        )
        self.switch_denoise.pack(fill="x", padx=12, pady=(0, 8))

        self.switch_hdr = ctk.CTkSwitch(
            self.enhance_card, text=self.t("feat_hdr"), font=self.get_ui_font(12),
            text_color=THEME_COLORS["text_primary"], progress_color=THEME_COLORS["accent"],
            command=self.on_tool_toggled
        )
        self.switch_hdr.pack(fill="x", padx=12, pady=(0, 8))

        self.switch_bg = ctk.CTkSwitch(
            self.enhance_card, text=self.t("feat_bg"), font=self.get_ui_font(12),
            text_color=THEME_COLORS["text_primary"], progress_color=THEME_COLORS["accent"],
            command=self.on_bg_toggled
        )
        self.switch_bg.pack(fill="x", padx=12, pady=(0, 12))

        self.format_card = self._create_card(self.sidebar)
        fmt_row = ctk.CTkFrame(self.format_card, fg_color="transparent")
        fmt_row.pack(fill="x", padx=12, pady=10)

        self.fmt_label = ctk.CTkLabel(
            fmt_row, text=self.t("card_format"), font=self.get_ui_font(12, "bold"),
            text_color=THEME_COLORS["text_primary"], anchor="w"
        )
        self.fmt_label.pack(side="left")

        self.fmt_selector = ctk.CTkSegmentedButton(
            fmt_row,
            values=["PNG", "JPG", "WEBP"],
            height=28,
            corner_radius=6,
            fg_color=THEME_COLORS["bg_card_sub"],
            selected_color=THEME_COLORS["seg_selected"],
            selected_hover_color=THEME_COLORS["seg_selected_hover"],
            unselected_color=THEME_COLORS["bg_card_sub"],
            unselected_hover_color=THEME_COLORS["btn_secondary_hover"],
            text_color=THEME_COLORS["text_primary"],
            font=self.get_ui_font(11, "bold")
        )
        self.fmt_selector.set("PNG")
        self.fmt_selector.pack(side="right")
        self.fmt_menu = self.fmt_selector

        self.btn_upscale = ctk.CTkButton(
            self.sidebar, text="Upscale Image (2×)", height=44,
            fg_color=THEME_COLORS["accent"], hover_color=THEME_COLORS["accent_hover"],
            text_color="#ffffff", font=self.get_ui_font(14, "bold"), corner_radius=10,
            command=self.start_upscaling
        )
        self.btn_upscale.pack(fill="x", padx=6, pady=(4, 10))

    def _create_card(self, parent) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent, fg_color=THEME_COLORS["bg_card"], corner_radius=10,
            border_width=1, border_color=THEME_COLORS["border"]
        )
        card.pack(fill="x", padx=6, pady=(0, 8))
        return card

    def _on_algo_changed(self, selected: str):
        for label, _, desc in ALGO_CHOICES:
            if label == selected:
                self.algo_desc_lbl.configure(text=desc)
                break
        self.on_tool_toggled()

    def setup_main_panel(self):
        self.main_panel = ctk.CTkFrame(self.workspace_frame, fg_color="transparent", corner_radius=0)
        self.main_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_panel.grid_columnconfigure(0, weight=1)
        self.main_panel.grid_rowconfigure(0, weight=1)

        self.single_view_frame = ctk.CTkFrame(self.main_panel, fg_color="transparent", corner_radius=0)
        self.batch_view_frame = ctk.CTkFrame(self.main_panel, fg_color="transparent", corner_radius=0)
        self.single_view_frame.grid(row=0, column=0, sticky="nsew")

        self.setup_single_viewport()
        self.setup_batch_viewport()
        self.setup_loading_overlay()

    def setup_single_viewport(self):
        self.single_view_frame.grid_columnconfigure(0, weight=1)
        self.single_view_frame.grid_rowconfigure(0, weight=1)

        self.canvas_frame = ctk.CTkFrame(self.single_view_frame, fg_color="transparent", corner_radius=0)
        self.canvas_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        self.canvas_frame.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self.canvas_frame,
            bg=THEME_COLORS["canvas_bg_hex"][self.current_theme],
            highlightthickness=0
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.v_scrollbar = ctk.CTkScrollbar(
            self.canvas_frame, orientation="vertical", command=self.on_v_scroll,
            fg_color="transparent",
            button_color=THEME_COLORS["scrollbar"],
            button_hover_color=THEME_COLORS["scrollbar_hover"]
        )
        self.v_scrollbar.grid(row=0, column=1, sticky="ns", padx=(2, 4), pady=4)

        self.h_scrollbar = ctk.CTkScrollbar(
            self.canvas_frame, orientation="horizontal", command=self.on_h_scroll,
            fg_color="transparent",
            button_color=THEME_COLORS["scrollbar"],
            button_hover_color=THEME_COLORS["scrollbar_hover"]
        )
        self.h_scrollbar.grid(row=1, column=0, sticky="ew", padx=4, pady=(2, 4))

        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<MouseWheel>", self.on_canvas_wheel)
        self.canvas.bind("<Shift-MouseWheel>", self.on_canvas_shift_wheel)
        self.canvas.bind("<Button-3>", self.on_right_click_pan_start)
        self.canvas.bind("<B3-Motion>", self.on_right_click_pan_move)
        self.canvas.bind("<Configure>", lambda e: self.update_display_cache())

        self.bottom_left_dock = ctk.CTkFrame(
            self.single_view_frame, fg_color=THEME_COLORS["bg_card"],
            corner_radius=16, border_width=1, border_color=THEME_COLORS["border"],
            height=34
        )
        self.bottom_left_dock.place(relx=0.02, rely=0.95, anchor="sw")

        self.canvas_res_lbl = ctk.CTkLabel(
            self.bottom_left_dock, text="No image loaded",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=THEME_COLORS["text_secondary"]
        )
        self.canvas_res_lbl.pack(padx=12, pady=5)

        self.bottom_dock = ctk.CTkFrame(
            self.single_view_frame, fg_color=THEME_COLORS["bg_card"],
            corner_radius=20, border_width=1, border_color=THEME_COLORS["border"],
            height=40
        )
        self.bottom_dock.place(relx=0.5, rely=0.95, anchor="s")

        self.btn_zoom_out = ctk.CTkButton(
            self.bottom_dock, text="−", width=30, height=30, corner_radius=15,
            fg_color="transparent", hover_color=THEME_COLORS["btn_secondary_hover"],
            text_color=THEME_COLORS["text_primary"], font=self.get_ui_font(14, "bold"),
            command=lambda: self.change_zoom(0.8)
        )
        self.btn_zoom_out.pack(side="left", padx=(6, 2), pady=5)

        self.zoom_pct_lbl = ctk.CTkLabel(
            self.bottom_dock, text="100%", width=46,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=THEME_COLORS["text_primary"]
        )
        self.zoom_pct_lbl.pack(side="left", padx=2, pady=5)

        self.btn_zoom_in = ctk.CTkButton(
            self.bottom_dock, text="+", width=30, height=30, corner_radius=15,
            fg_color="transparent", hover_color=THEME_COLORS["btn_secondary_hover"],
            text_color=THEME_COLORS["text_primary"], font=self.get_ui_font(14, "bold"),
            command=lambda: self.change_zoom(1.25)
        )
        self.btn_zoom_in.pack(side="left", padx=2, pady=5)

        self.btn_actual_size = ctk.CTkButton(
            self.bottom_dock, text="1:1", width=36, height=30, corner_radius=15,
            fg_color="transparent", hover_color=THEME_COLORS["btn_secondary_hover"],
            text_color=THEME_COLORS["text_primary"], font=self.get_ui_font(11, "bold"),
            command=self.set_actual_pixels_view
        )
        self.btn_actual_size.pack(side="left", padx=2, pady=5)

        self.btn_fit = ctk.CTkButton(
            self.bottom_dock, text="Fit", width=38, height=30, corner_radius=15,
            fg_color="transparent", hover_color=THEME_COLORS["btn_secondary_hover"],
            text_color=THEME_COLORS["text_primary"], font=self.get_ui_font(11, "bold"),
            command=self.reset_viewport
        )
        self.btn_fit.pack(side="left", padx=2, pady=5)

        self.btn_copy = ctk.CTkButton(
            self.bottom_dock, text="Copy", width=48, height=30, corner_radius=15,
            fg_color="transparent", hover_color=THEME_COLORS["btn_secondary_hover"],
            text_color=THEME_COLORS["text_primary"], font=self.get_ui_font(11, "bold"),
            command=self.copy_to_clipboard, state="disabled"
        )
        self.btn_copy.pack(side="left", padx=(2, 6), pady=5)

        self.bottom_right_dock = ctk.CTkFrame(self.single_view_frame, fg_color="transparent")
        self.bottom_right_dock.place(relx=0.98, rely=0.95, anchor="se")

        self.btn_compare = ctk.CTkButton(
            self.bottom_right_dock, text="Compare", height=34, width=96, corner_radius=17,
            fg_color=THEME_COLORS["btn_secondary"], hover_color=THEME_COLORS["btn_secondary_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text_primary"], font=self.get_ui_font(11, "bold"),
            command=self.toggle_compare_view
        )
        self.btn_compare.pack(side="left")

    def update_zoom_label(self):
        if hasattr(self, "zoom_pct_lbl") and self.zoom_pct_lbl.winfo_exists():
            pct = int(round(self.zoom_level * 100))
            self.zoom_pct_lbl.configure(text=f"{pct}%")

    def setup_loading_overlay(self):
        self.loading_overlay = ctk.CTkFrame(
            self.canvas_frame, fg_color=THEME_COLORS["bg_card"], corner_radius=16,
            border_width=1, border_color=THEME_COLORS["border"], width=380, height=240
        )

        logo_img_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.isfile(logo_path := logo_img_path):
            try:
                pil_logo = Image.open(logo_path).resize((40, 40), Image.Resampling.LANCZOS)
                self.modal_logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(40, 40))
                self.modal_logo_lbl = ctk.CTkLabel(self.loading_overlay, image=self.modal_logo_img, text="")
                self.modal_logo_lbl.pack(pady=(18, 6))
            except Exception:
                pass

        self.loading_title_lbl = ctk.CTkLabel(
            self.loading_overlay, text=self.t("loading_title"),
            font=self.get_ui_font(15, "bold"),
            text_color=THEME_COLORS["text_primary"]
        )
        self.loading_title_lbl.pack(padx=20, pady=(2, 2))

        self.loading_sub_lbl = ctk.CTkLabel(
            self.loading_overlay, text=self.t("loading_subtitle"),
            font=self.get_ui_font(12),
            text_color=THEME_COLORS["text_secondary"]
        )
        self.loading_sub_lbl.pack(padx=20, pady=(2, 10))

        self.loading_pbar = ctk.CTkProgressBar(
            self.loading_overlay, width=300, height=8,
            progress_color=THEME_COLORS["accent"], fg_color=THEME_COLORS["bg_card_sub"]
        )
        self.loading_pbar.set(0.1)
        self.loading_pbar.pack(pady=4)

        self.loading_time_lbl = ctk.CTkLabel(
            self.loading_overlay, text="0.0s",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=THEME_COLORS["accent"]
        )
        self.loading_time_lbl.pack(pady=(4, 10))

        self.btn_cancel_job = ctk.CTkButton(
            self.loading_overlay, text=self.t("btn_cancel"), width=100, height=30,
            fg_color=THEME_COLORS["btn_secondary"], hover_color=THEME_COLORS["danger_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["danger"], font=self.get_ui_font(11, "bold"), corner_radius=8,
            command=self.cancel_current_job
        )
        self.btn_cancel_job.pack(pady=(0, 16))

    def cancel_current_job(self):
        if self.is_processing:
            self.cancel_event.set()
            self.status_lbl.configure(text=self.t("btn_cancel") + "...")
            if hasattr(self, "btn_cancel_job") and self.btn_cancel_job.winfo_exists():
                self.btn_cancel_job.configure(state="disabled")
            if hasattr(self, "btn_batch_cancel") and self.btn_batch_cancel.winfo_exists():
                self.btn_batch_cancel.configure(state="disabled")

    def show_loading_screen(self, title: str = None, subtitle: str = None):
        self.loading_title_lbl.configure(text=title or self.t("loading_title"))
        self.loading_sub_lbl.configure(text=subtitle or self.t("loading_subtitle"))
        self.btn_cancel_job.configure(state="normal")
        self.loading_pbar.set(0.1)
        self.loading_start_time = time.time()
        self.loading_overlay.place(relx=0.5, rely=0.5, anchor="center")
        self._update_loading_timer()

    def hide_loading_screen(self):
        if self.loading_timer_id:
            self.after_cancel(self.loading_timer_id)
            self.loading_timer_id = None
        self.loading_overlay.place_forget()

    def _update_loading_timer(self):
        if self.is_processing:
            elapsed = time.time() - self.loading_start_time
            self.loading_time_lbl.configure(text=f"{elapsed:.1f}s")
            self.loading_timer_id = self.after(100, self._update_loading_timer)

    def on_v_scroll(self, action, value, *args):
        c_h = self.canvas.winfo_height()
        disp_h = self.cached_disp_h
        if action != "moveto" or disp_h <= c_h:
            return
        max_pan = (disp_h - c_h) // 2
        target = (disp_h - c_h) / 2.0 - float(value) * disp_h
        self.pan_y = int(max(-max_pan, min(max_pan, target)))
        self.update_scrollbars()
        self.schedule_redraw()

    def on_h_scroll(self, action, value, *args):
        c_w = self.canvas.winfo_width()
        disp_w = self.cached_disp_w
        if action != "moveto" or disp_w <= c_w:
            return
        max_pan = (disp_w - c_w) // 2
        target = (disp_w - c_w) / 2.0 - float(value) * disp_w
        self.pan_x = int(max(-max_pan, min(max_pan, target)))
        self.update_scrollbars()
        self.schedule_redraw()

    def update_scrollbars(self):
        c_w = self.canvas.winfo_width()
        c_h = self.canvas.winfo_height()
        disp_w = self.cached_disp_w
        disp_h = self.cached_disp_h

        if disp_w > c_w and disp_w > 0:
            disp_x = (c_w - disp_w) // 2 + self.pan_x
            first_x = max(0.0, min(1.0, -disp_x / float(disp_w)))
            last_x = max(0.0, min(1.0, (-disp_x + c_w) / float(disp_w)))
            self.h_scrollbar.set(first_x, last_x)
        else:
            self.h_scrollbar.set(0.0, 1.0)

        if disp_h > c_h and disp_h > 0:
            disp_y = (c_h - disp_h) // 2 + self.pan_y
            first_y = max(0.0, min(1.0, -disp_y / float(disp_h)))
            last_y = max(0.0, min(1.0, (-disp_y + c_h) / float(disp_h)))
            self.v_scrollbar.set(first_y, last_y)
        else:
            self.v_scrollbar.set(0.0, 1.0)

    def on_canvas_shift_wheel(self, event):
        c_w = self.canvas.winfo_width()
        disp_w = self.cached_disp_w
        if disp_w > c_w:
            delta = 35 if event.delta > 0 else -35
            max_pan = (disp_w - c_w) // 2
            self.pan_x = max(-max_pan, min(max_pan, self.pan_x + delta))
            self.update_scrollbars()
            self.schedule_redraw()

    def setup_batch_viewport(self):
        self.batch_view_frame.grid_columnconfigure(0, weight=1)
        self.batch_view_frame.grid_rowconfigure(1, weight=1)

        self.batch_top_bar = ctk.CTkFrame(self.batch_view_frame, fg_color="transparent")
        self.batch_top_bar.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))

        self.btn_batch_add_files = ctk.CTkButton(
            self.batch_top_bar, text="Add Images", height=34,
            fg_color=THEME_COLORS["accent"], hover_color=THEME_COLORS["accent_hover"],
            text_color="#ffffff", font=self.get_ui_font(12, "bold"), corner_radius=8,
            command=self.batch_browse_files
        )
        self.btn_batch_add_files.pack(side="left", padx=(0, 6))

        self.btn_batch_add_folder = ctk.CTkButton(
            self.batch_top_bar, text="Add Folder", height=34,
            fg_color=THEME_COLORS["btn_secondary"], hover_color=THEME_COLORS["btn_secondary_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text_primary"], font=self.get_ui_font(12), corner_radius=8,
            command=self.batch_browse_folder
        )
        self.btn_batch_add_folder.pack(side="left", padx=4)

        self.btn_batch_clear = ctk.CTkButton(
            self.batch_top_bar, text="Clear Queue", height=34,
            fg_color=THEME_COLORS["btn_secondary"], hover_color=THEME_COLORS["danger_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["danger"], font=self.get_ui_font(12), corner_radius=8,
            command=self.batch_clear_queue
        )
        self.btn_batch_clear.pack(side="left", padx=4)

        self.btn_batch_run = ctk.CTkButton(
            self.batch_top_bar, text="Start Batch", height=34,
            fg_color=THEME_COLORS["accent_success"], hover_color=THEME_COLORS["accent_success_hover"],
            text_color="#ffffff", font=self.get_ui_font(12, "bold"), corner_radius=8,
            command=self.start_batch_upscale
        )
        self.btn_batch_run.pack(side="right", padx=(6, 0))

        self.btn_batch_cancel = ctk.CTkButton(
            self.batch_top_bar, text="Cancel", height=34, width=82,
            fg_color=THEME_COLORS["btn_secondary"], hover_color=THEME_COLORS["danger_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["danger"], font=self.get_ui_font(12), corner_radius=8,
            command=self.cancel_current_job, state="disabled"
        )
        self.btn_batch_cancel.pack(side="right", padx=4)

        self.batch_listbox_frame = ctk.CTkScrollableFrame(
            self.batch_view_frame, fg_color=THEME_COLORS["bg_card"], corner_radius=10,
            border_width=1, border_color=THEME_COLORS["border"]
        )
        self.batch_listbox_frame.grid(row=1, column=0, sticky="nsew", padx=14, pady=6)

        self.batch_empty_lbl = ctk.CTkLabel(
            self.batch_listbox_frame,
            text="No images in batch queue.\nDrag & drop files or click Add Images.",
            font=self.get_ui_font(13), text_color=THEME_COLORS["text_muted"]
        )
        self.batch_empty_lbl.pack(pady=80)

        self.batch_bottom_bar = ctk.CTkFrame(self.batch_view_frame, fg_color="transparent")
        self.batch_bottom_bar.grid(row=2, column=0, sticky="ew", padx=14, pady=(6, 12))

        self.batch_out_lbl = ctk.CTkLabel(
            self.batch_bottom_bar, text=f"Output: {self.batch_output_dir}",
            font=self.get_ui_font(11), text_color=THEME_COLORS["text_secondary"], anchor="w"
        )
        self.batch_out_lbl.pack(side="left", fill="x", expand=True, padx=4)

        self.btn_batch_change_dir = ctk.CTkButton(
            self.batch_bottom_bar, text="Change Folder", width=116, height=28,
            fg_color=THEME_COLORS["btn_secondary"], hover_color=THEME_COLORS["btn_secondary_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text_primary"], font=self.get_ui_font(11), corner_radius=6,
            command=self.batch_change_output_dir
        )
        self.btn_batch_change_dir.pack(side="right")

    def on_tool_toggled(self):
        if self.current_pil_img is not None:
            self.on_settings_changed()

    def on_lang_changed(self, selected_lang_str: str):
        code_map = {
            "English (en)": "en", "فارسی (fa)": "fa", "العربية (ar)": "ar", "Español (es)": "es",
            "Français (fr)": "fr", "Deutsch (de)": "de", "日本語 (ja)": "ja", "中文 (zh)": "zh",
            "Русский (ru)": "ru", "Português (pt)": "pt"
        }
        self.current_lang = code_map.get(selected_lang_str, "en")
        self.update_translations()

    def update_translations(self):
        self.app_title_lbl.configure(text=self.t("title"), font=self.get_ui_font(16, "bold"))
        self.mode_switch.configure(values=[self.t("tab_single"), self.t("tab_batch")], font=self.get_ui_font(12, "bold"))
        self.mode_switch.set(self.t("tab_batch") if self.workspace_mode == "batch" else self.t("tab_single"))
        self.theme_switch.configure(values=[self.t("theme_light"), self.t("theme_dark")], font=self.get_ui_font(11, "bold"))
        self.theme_switch.set(self._theme_label(self.current_theme))
        self.btn_browse.configure(text=f"+ {self.t('btn_browse')}", font=self.get_ui_font(12, "bold"))
        self.btn_save.configure(text=self.t("btn_save"), font=self.get_ui_font(12, "bold"))
        self.source_sec_lbl.configure(text=self.t("card_source"), font=self.get_ui_font(12, "bold"))
        self.btn_paste.configure(text=self.t("btn_paste"), font=self.get_ui_font(11))
        self.btn_sample.configure(text=self.t("btn_sample"), font=self.get_ui_font(11))
        self.btn_clear.configure(text=self.t("btn_clear"), font=self.get_ui_font(11))
        self.scale_sec_lbl.configure(text=self.t("card_scale"), font=self.get_ui_font(12, "bold"))
        self.custom_scale_lbl.configure(text=self.t("custom_scale") + ":", font=self.get_ui_font(11))
        self.algo_lbl.configure(text=self.t("card_quality"), font=self.get_ui_font(12, "bold"))
        self.pro_sec_lbl.configure(text=self.t("card_enhancements"), font=self.get_ui_font(12, "bold"))
        self.btn_reset_fx_sidebar.configure(text=self.t("btn_reset_effects"), font=self.get_ui_font(10, "bold"))
        self.switch_deblur.configure(text=self.t("feat_deblur"), font=self.get_ui_font(12))
        self.switch_denoise.configure(text=self.t("feat_denoise"), font=self.get_ui_font(12))
        self.switch_hdr.configure(text=self.t("feat_hdr"), font=self.get_ui_font(12))
        self.switch_bg.configure(text=self.t("feat_bg"), font=self.get_ui_font(12))
        self.fmt_label.configure(text=self.t("card_format"), font=self.get_ui_font(12, "bold"))
        self.btn_fit.configure(text=self.t("btn_fit"), font=self.get_ui_font(11, "bold"))
        self.btn_copy.configure(text=self.t("btn_copy"), font=self.get_ui_font(11, "bold"))
        self.btn_compare.configure(text=self.t("btn_compare"), font=self.get_ui_font(11, "bold"))
        self.btn_cancel_job.configure(text=self.t("btn_cancel"), font=self.get_ui_font(11, "bold"))
        self.btn_batch_cancel.configure(text=self.t("btn_cancel"), font=self.get_ui_font(12))
        self.btn_batch_add_files.configure(text=self.t("batch_add_files"), font=self.get_ui_font(12, "bold"))
        self.btn_batch_add_folder.configure(text=self.t("batch_add_folder"), font=self.get_ui_font(12))
        self.btn_batch_clear.configure(text=self.t("batch_clear"), font=self.get_ui_font(12))
        self.btn_batch_run.configure(text=self.t("batch_start"), font=self.get_ui_font(12, "bold"))
        self.loading_title_lbl.configure(text=self.t("loading_title"), font=self.get_ui_font(15, "bold"))
        self.loading_sub_lbl.configure(text=self.t("loading_subtitle"), font=self.get_ui_font(12))
        if not self.is_processing and self.current_pil_img is None:
            self.status_lbl.configure(text=self.t("status_ready"), font=self.get_ui_font(11))

        self.lang_menu.configure(font=self.get_ui_font(11), dropdown_font=self.get_ui_font(11))
        self.algo_menu.configure(font=self.get_ui_font(11, "bold"), dropdown_font=self.get_ui_font(11))

        self.update_stats()
        self.redraw_comparison()

    def select_preset(self, val: float):
        self.scale_val = max(1.0, min(8.0, float(val)))
        self.custom_entry.delete(0, "end")
        self.custom_entry.insert(0, str(int(self.scale_val) if self.scale_val.is_integer() else self.scale_val))
        self._highlight_preset(self.scale_val)
        self.update_stats()
        self.on_settings_changed()

    def _highlight_preset(self, val):
        active_key = f"mult_{int(val)}" if val is not None and float(val).is_integer() else None
        for key, btn in self.preset_btn_map.items():
            if key == active_key:
                btn.configure(
                    fg_color=THEME_COLORS["accent"],
                    border_color=THEME_COLORS["accent"],
                    text_color="#ffffff"
                )
            else:
                btn.configure(
                    fg_color=THEME_COLORS["btn_secondary"],
                    border_color=THEME_COLORS["border"],
                    text_color=THEME_COLORS["text_primary"]
                )

    def on_custom_scale_changed(self, clamp_entry: bool = False):
        text = self.custom_entry.get().strip()
        try:
            raw = float(text)
        except ValueError:
            if not clamp_entry:
                return
            raw = 1.0

        value = min(8.0, max(1.0, raw))
        if clamp_entry and value != raw:
            self.custom_entry.delete(0, "end")
            self.custom_entry.insert(0, str(int(value) if value.is_integer() else value))
        elif not clamp_entry and raw < 1.0:
            return

        if value == self.scale_val:
            return

        self.scale_val = value
        self._highlight_preset(value)
        self.update_stats()
        self.on_settings_changed()

    def update_stats(self):
        scale_label = f"{self.scale_val:.0f}×" if self.scale_val.is_integer() else f"{self.scale_val:.2g}×"
        if abs(self.scale_val - 1.0) < 1e-6:
            self.btn_upscale.configure(text=self.t("btn_enhance_only"))
        else:
            self.btn_upscale.configure(text=f"{self.t('btn_upscale')} ({scale_label})")

        if not self.orig_w or not self.orig_h:
            self.target_dim_lbl.configure(text="—")
            self.est_ram_lbl.configure(text="")
            if hasattr(self, "canvas_res_lbl") and self.canvas_res_lbl.winfo_exists():
                self.canvas_res_lbl.configure(text="No image loaded")
            return

        out_w, out_h, eff_factor = UpscalerEngine.calculate_target_size(
            self.orig_w, self.orig_h, self.scale_type, self.scale_val
        )
        ram_mb = (out_w * out_h * 4) / (1024 * 1024)
        self.target_dim_lbl.configure(text=f"→ {out_w:,} × {out_h:,}")
        self.est_ram_lbl.configure(text=f"~{ram_mb:.0f} MB")

        if hasattr(self, "canvas_res_lbl") and self.canvas_res_lbl.winfo_exists():
            stage = self.t("after_final_tag") if self.final_pil_img is not None else self.t("after_tag")
            f_txt = f"{eff_factor:.0f}×" if abs(eff_factor - round(eff_factor)) < 0.01 else f"{eff_factor:.2g}×"
            self.canvas_res_lbl.configure(
                text=f"{self.orig_w:,} × {self.orig_h:,} → {out_w:,} × {out_h:,} ({f_txt}) • {stage}"
            )

    def browse_file(self):
        path = filedialog.askopenfilename(
            title="Open Image",
            filetypes=[
                ("Image Files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tiff;*.tif"),
                ("All Files", "*.*")
            ]
        )
        if path:
            self.load_image_from_path(path)

    def paste_from_clipboard(self):
        try:
            clip = ImageGrab.grabclipboard()
        except Exception as exc:
            messagebox.showerror("Clipboard Error", f"Could not paste from clipboard: {exc}")
            return

        if isinstance(clip, Image.Image):
            self.switch_workspace_mode("single")
            self._begin_load(clip, "clipboard_image.png")
        elif isinstance(clip, list) and clip and os.path.isfile(clip[0]):
            self.switch_workspace_mode("single")
            self.load_image_from_path(clip[0])
        else:
            messagebox.showinfo("Clipboard", "No image found on clipboard. Copy an image first.")

    def copy_to_clipboard(self):
        target_img = self.final_pil_img
        if target_img is None:
            return

        if not WIN32_CLIPBOARD_AVAILABLE:
            messagebox.showwarning("Clipboard", "Copying images requires pywin32.")
            return

        try:
            output = io.BytesIO()
            target_img.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            finally:
                win32clipboard.CloseClipboard()
        except Exception as exc:
            messagebox.showerror("Clipboard Error", f"Could not copy image: {exc}")
            return

        self.status_lbl.configure(text=self.t("copied_clipboard"))

    def load_image_from_path(self, path: str):
        self._begin_load(path, os.path.basename(path))

    def load_sample_image(self):
        img = Image.new("RGB", (320, 220), color=(248, 250, 252))
        draw = ImageDraw.Draw(img)

        for r in range(90, 10, -16):
            color = (37, 99, 235) if r % 32 == 0 else (16, 185, 129)
            draw.ellipse([160 - r, 110 - r, 160 + r, 110 + r], outline=color, width=2)

        draw.text((120, 96), "Aupscaler", fill=(17, 24, 39))
        draw.text((104, 116), "Resolution Sample", fill=(75, 85, 99))

        self.switch_workspace_mode("single")
        self._begin_load(img, "sample_test.png")

    def load_image_bytes(self, img_bytes: bytes, filename: str):
        self._begin_load(img_bytes, filename)

    @staticmethod
    def _normalize_image_mode(image: Image.Image) -> Image.Image:
        has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
        target_mode = "RGBA" if has_alpha else "RGB"
        return image if image.mode == target_mode else image.convert(target_mode)

    def _begin_load(self, source, filename: str):
        self.cancel_preview()
        self.load_token += 1
        token = self.load_token
        self.status_lbl.configure(text=self.t("status_loading"))
        threading.Thread(target=self._load_worker, args=(source, filename, token), daemon=True).start()

    def _load_worker(self, source, filename: str, token: int):
        try:
            if isinstance(source, Image.Image):
                opened = source
            elif isinstance(source, (bytes, bytearray)):
                opened = Image.open(io.BytesIO(source))
            else:
                opened = Image.open(source)
            image = ImageOps.exif_transpose(opened)
            image.load()
            image = self._normalize_image_mode(image)
            preview_src = UpscalerEngine.prepare_preview_source(image)
        except Exception as exc:
            self.post_to_main(self._on_load_failed, str(exc), token)
            return
        self.post_to_main(self._on_image_loaded, image, preview_src, filename, token)

    def _on_load_failed(self, message: str, token: int):
        if token != self.load_token:
            return
        self.status_lbl.configure(text=self.t("status_ready"))
        messagebox.showerror("Error", f"Could not load image: {message}")

    def _on_image_loaded(self, image: Image.Image, preview_src: Image.Image, filename: str, token: int):
        if token != self.load_token:
            return

        self.active_filename = filename
        self.current_pil_img = image
        self.preview_src = preview_src
        self.upscaled_pil_img = None
        self.final_pil_img = None
        self.hold_space_active = False
        self._sync_compare_button()
        self.image_epoch += 1
        self.orig_w, self.orig_h = image.size

        mp = (self.orig_w * self.orig_h) / 1_000_000.0
        self.img_info_lbl.configure(text=f"{filename}\n{self.orig_w:,} × {self.orig_h:,} px  •  {mp:.2f} MP")
        self._set_export_enabled(False)
        self.btn_copy.configure(state="disabled")
        self.status_lbl.configure(text=self.t("status_ready"))
        self.update_stats()
        self.reset_viewport()
        self.request_preview(delay=40)

    def clear_image(self):
        self.load_token += 1
        self.cancel_preview()
        self.current_pil_img = None
        self.preview_src = None
        self.upscaled_pil_img = None
        self.final_pil_img = None
        self.hold_space_active = False
        self._sync_compare_button()
        self.image_epoch += 1
        self.view_key = None
        self.orig_w = 0
        self.orig_h = 0
        self.img_info_lbl.configure(text="No image loaded")
        self._set_export_enabled(False)
        self.btn_copy.configure(state="disabled")
        self.status_lbl.configure(text=self.t("status_ready"))
        self.update_stats()
        self.update_display_cache()

    def set_actual_pixels_view(self):
        if not self.current_pil_img:
            return
        c_w = self.canvas.winfo_width()
        c_h = self.canvas.winfo_height()
        if c_w <= 10 or c_h <= 10:
            return
        img_w, img_h = self.current_pil_img.size
        base_scale = min((c_w - 40) / img_w, (c_h - 40) / img_h)
        if base_scale > 0:
            self.zoom_level = 1.0 / base_scale
        self.pan_x = 0
        self.pan_y = 0
        self.cached_disp_w = 0
        self.update_display_cache()

    def _geometry(self):
        if self.current_pil_img is None:
            return None
        c_w = self.canvas.winfo_width()
        c_h = self.canvas.winfo_height()
        if c_w <= 10 or c_h <= 10:
            return None

        img_w, img_h = self.current_pil_img.size
        base_scale = min((c_w - 40) / img_w, (c_h - 40) / img_h)
        if base_scale <= 0:
            return None

        eff_scale = base_scale * self.zoom_level
        disp_w = max(1, int(round(img_w * eff_scale)))
        disp_h = max(1, int(round(img_h * eff_scale)))
        disp_x = (c_w - disp_w) // 2 + self.pan_x
        disp_y = (c_h - disp_h) // 2 + self.pan_y
        return c_w, c_h, disp_w, disp_h, disp_x, disp_y

    def update_display_cache(self):
        self.update_zoom_label()
        geo = self._geometry()
        if geo is None:
            self.cached_disp_w = 0
            self.cached_disp_h = 0
            self.update_scrollbars()
            self.schedule_redraw()
            return

        c_w, c_h, disp_w, disp_h, _, _ = geo
        max_pan_x = max(0, (disp_w - c_w) // 2)
        max_pan_y = max(0, (disp_h - c_h) // 2)
        self.pan_x = max(-max_pan_x, min(max_pan_x, self.pan_x))
        self.pan_y = max(-max_pan_y, min(max_pan_y, self.pan_y))

        self.cached_disp_w = disp_w
        self.cached_disp_h = disp_h
        self.update_scrollbars()
        self.schedule_redraw()

    def schedule_redraw(self):
        if self.render_after_id is None:
            self.render_after_id = self.after(10, self._run_scheduled_redraw)

    def _run_scheduled_redraw(self):
        self.render_after_id = None
        self.redraw_comparison()

    def _get_checker(self, width: int, height: int, offset_x: int, offset_y: int) -> Image.Image:
        key = (width, height, offset_x % 32, offset_y % 32, self.current_theme)
        if key == self.checker_key and self.checker_image is not None:
            return self.checker_image

        cell = 16
        rows = (np.arange(height) + offset_y) // cell
        cols = (np.arange(width) + offset_x) // cell
        parity = ((rows[:, None] + cols[None, :]) % 2)[..., None]
        if self.current_theme == "dark":
            light_cell, dark_cell = (28, 33, 46, 255), (15, 18, 26, 255)
        else:
            light_cell, dark_cell = (255, 255, 255, 255), (226, 232, 240, 255)
        pixels = np.where(parity == 0, np.array(dark_cell, np.uint8), np.array(light_cell, np.uint8))

        self.checker_image = Image.fromarray(pixels.astype(np.uint8))
        self.checker_key = key
        return self.checker_image

    def _render_view(self, image: Image.Image, disp_w: int, disp_h: int, x0: int, y0: int, vw: int, vh: int, pixelated: bool) -> Image.Image:
        img_w, img_h = image.size
        sx = img_w / float(disp_w)
        sy = img_h / float(disp_h)
        box = (
            max(0.0, x0 * sx),
            max(0.0, y0 * sy),
            min(float(img_w), (x0 + vw) * sx),
            min(float(img_h), (y0 + vh) * sy)
        )

        magnifying = disp_w > img_w
        if pixelated and disp_w > img_w * 1.5:
            resample = Image.Resampling.NEAREST
        else:
            resample = Image.Resampling.BICUBIC

        tile = image.resize(
            (vw, vh), resample, box=box, reducing_gap=None if magnifying else 2.0
        )

        if tile.mode == "RGBA":
            backdrop = self._get_checker(vw, vh, x0, y0)
            return Image.alpha_composite(backdrop, tile).convert("RGB")
        return tile if tile.mode == "RGB" else tile.convert("RGB")

    def on_canvas_click(self, event):
        self._canvas_press_x = event.x
        self._canvas_moved = False
        if self.current_pil_img is not None:
            self.update_split(event.x)

    def on_canvas_drag(self, event):
        if abs(event.x - self._canvas_press_x) > 3:
            self._canvas_moved = True
        if self.current_pil_img is not None:
            self.update_split(event.x)

    def on_canvas_release(self, event):
        if self.current_pil_img is None and not self._canvas_moved:
            self.browse_file()

    def update_split(self, x: int):
        c_w = self.canvas.winfo_width()
        if c_w > 0:
            self.split_ratio = max(0.0, min(1.0, x / float(c_w)))
            self.schedule_redraw()

    def change_zoom(self, factor: float):
        self.zoom_level = max(0.2, min(30.0, self.zoom_level * factor))
        self.update_display_cache()

    def reset_viewport(self):
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.split_ratio = 0.5
        self.cached_disp_w = 0
        self.update_display_cache()

    def on_canvas_wheel(self, event):
        c_h = self.canvas.winfo_height()
        disp_h = self.cached_disp_h
        if disp_h > c_h:
            delta = 35 if event.delta > 0 else -35
            max_pan = (disp_h - c_h) // 2
            self.pan_y = max(-max_pan, min(max_pan, self.pan_y + delta))
            self.update_scrollbars()
            self.schedule_redraw()
        else:
            self.change_zoom(1.15 if event.delta > 0 else 0.85)

    def on_right_click_pan_start(self, event):
        self.pan_start_x = event.x - self.pan_x
        self.pan_start_y = event.y - self.pan_y

    def on_right_click_pan_move(self, event):
        c_w = self.canvas.winfo_width()
        c_h = self.canvas.winfo_height()

        max_pan_x = max(0, (self.cached_disp_w - c_w) // 2)
        max_pan_y = max(0, (self.cached_disp_h - c_h) // 2)

        self.pan_x = max(-max_pan_x, min(max_pan_x, event.x - self.pan_start_x))
        self.pan_y = max(-max_pan_y, min(max_pan_y, event.y - self.pan_start_y))
        self.update_scrollbars()
        self.schedule_redraw()

    def _draw_canvas_pill(self, x: int, y: int, text: str, anchor: str, fill_bg: str, outline: str, text_fill: str, font_spec):
        tid = self.canvas.create_text(x, y, anchor=anchor, text=text, fill=text_fill, font=font_spec)
        bbox = self.canvas.bbox(tid)
        if bbox is not None:
            pad_x, pad_y = 10, 4
            rect = self.canvas.create_rectangle(
                bbox[0] - pad_x, bbox[1] - pad_y, bbox[2] + pad_x, bbox[3] + pad_y,
                fill=fill_bg, outline=outline, width=1
            )
            self.canvas.tag_raise(tid, rect)

    def _draw_placeholder(self):
        self.canvas.delete("all")
        c_w = self.canvas.winfo_width() or 700
        c_h = self.canvas.winfo_height() or 500
        dark = self.current_theme == "dark"
        card_bg = "#14171f" if dark else "#ffffff"
        border = "#2a3040" if dark else "#cbd5e1"
        title_col = "#f3f4f6" if dark else "#111827"
        sub_col = "#9ca3af" if dark else "#6b7280"
        accent_col = "#3b82f6" if dark else "#2563eb"

        box_w = min(460, c_w - 60)
        box_h = 160
        cx, cy = c_w // 2, (c_h // 2) - 18
        if box_w > 220 and c_h > 220:
            self.canvas.create_rectangle(
                cx - box_w // 2, cy - box_h // 2, cx + box_w // 2, cy + box_h // 2,
                fill=card_bg, outline=border, width=1, dash=(6, 4)
            )

        is_rtl = self.current_lang in ("fa", "ar")
        font_family = "A Nafis" if is_rtl else "Segoe UI"
        self.canvas.create_text(cx, cy - 28, text="⤢", fill=accent_col, font=(font_family, 24, "bold"))
        self.canvas.create_text(
            cx, cy + 8, text=self.t("empty_title"),
            fill=title_col, font=(font_family, 13 if not is_rtl else 15, "bold")
        )
        self.canvas.create_text(
            cx, cy + 34, text=self.t("empty_sub"),
            fill=sub_col, font=(font_family, 10 if not is_rtl else 12)
        )

    def redraw_comparison(self):
        geo = self._geometry()
        if geo is None:
            self._draw_placeholder()
            return

        c_w, c_h, disp_w, disp_h, disp_x, disp_y = geo
        x0 = max(0, -disp_x)
        y0 = max(0, -disp_y)
        vw = min(disp_w, c_w - disp_x) - x0
        vh = min(disp_h, c_h - disp_y) - y0
        if vw <= 0 or vh <= 0:
            self.canvas.delete("all")
            return

        after_source = self.upscaled_pil_img if self.upscaled_pil_img is not None else self.current_pil_img
        key = (self.image_epoch, disp_w, disp_h, x0, y0, vw, vh, self.current_theme)
        if key != self.view_key:
            self.view_before = self._render_view(self.current_pil_img, disp_w, disp_h, x0, y0, vw, vh, True)
            self.view_after = self._render_view(after_source, disp_w, disp_h, x0, y0, vw, vh, False)
            self.view_key = key

        is_rtl = self.current_lang in ("fa", "ar")
        font_family = "A Nafis" if is_rtl else "Segoe UI"
        font_size = 12 if is_rtl else 10

        split_canvas_x = int(c_w * self.split_ratio)
        local_split = max(0, min(vw, split_canvas_x - (disp_x + x0)))

        if self.hold_space_active or local_split <= 0:
            frame = self.view_before
        elif local_split >= vw:
            frame = self.view_after
        else:
            frame = self.view_after.copy()
            frame.paste(self.view_before.crop((local_split, 0, vw, vh)), (local_split, 0))

        self.tk_canvas_img = ImageTk.PhotoImage(frame)
        self.canvas.delete("all")
        self.canvas.create_image(disp_x + x0, disp_y + y0, anchor="nw", image=self.tk_canvas_img)

        dark = self.current_theme == "dark"
        pill_bg = "#14171f" if dark else "#ffffff"
        pill_border = "#2a3040" if dark else "#cbd5e1"
        pill_text = "#f3f4f6" if dark else "#111827"
        tag_accent = "#60a5fa" if dark else "#2563eb"
        divider_color = "#ffffff" if dark else "#111827"

        if self.hold_space_active:
            self._draw_canvas_pill(
                c_w // 2, 24, self.t("before_tag"), "n",
                pill_bg, tag_accent, tag_accent, (font_family, font_size, "bold")
            )
            return

        self.canvas.create_line(split_canvas_x, 0, split_canvas_x, c_h, fill=divider_color, width=2)

        knob_y = c_h // 2
        r = 15
        self.canvas.create_oval(
            split_canvas_x - r, knob_y - r, split_canvas_x + r, knob_y + r,
            fill=pill_bg, outline=divider_color, width=2
        )
        self.canvas.create_text(
            split_canvas_x, knob_y, text="◂ ▸", fill=divider_color, font=("Segoe UI", 9, "bold")
        )

        after_label = self.t("after_final_tag") if self.final_pil_img is not None else self.t("after_tag")
        self._draw_canvas_pill(
            24, 24, after_label, "w",
            pill_bg, pill_border, tag_accent, (font_family, font_size, "bold")
        )
        self._draw_canvas_pill(
            c_w - 24, 24, self.t("before_tag"), "e",
            pill_bg, pill_border, pill_text, (font_family, font_size, "bold")
        )

        self.update_stats()

    def get_selected_algo_code(self) -> str:
        text = self.algo_menu.get().lower()
        for label, code, _ in ALGO_CHOICES:
            if label.lower() == text:
                return code
        if "fsrcnn" in text or "high detail" in text:
            return "fsrcnn"
        if "lanczos" in text or "photo" in text:
            return "lanczos"
        if "nearest" in text or "pixel" in text:
            return "nearest"
        return "espcn"

    def start_upscaling(self):
        if self.current_pil_img is None:
            messagebox.showwarning("No Image", self.t("no_image"))
            return
        if self.is_processing:
            return

        self.cancel_preview()
        self.cancel_event.clear()
        self.is_processing = True
        self.btn_upscale.configure(state="disabled")
        self.progress_bar.set(0.05)
        self.status_lbl.configure(text=self.t("status_processing"))

        settings = self._collect_settings()
        out_w, out_h, factor = UpscalerEngine.calculate_target_size(
            self.orig_w, self.orig_h, settings["scale_type"], settings["scale_val"]
        )
        self.show_loading_screen(
            title=f"{self.t('loading_title')} ({factor:.2g}×)",
            subtitle=f"{out_w:,} × {out_h:,} px"
        )

        def on_progress(pct: float, step_name: str):
            self.post_to_main(self._on_progress_ui, pct, step_name)

        threading.Thread(
            target=self._run_upscaling_job,
            args=(self.current_pil_img, settings, on_progress),
            daemon=True
        ).start()

    def _on_progress_ui(self, pct: float, step_name: str):
        if not self.is_processing:
            return
        self.progress_bar.set(pct)
        self.loading_pbar.set(pct)
        self.loading_sub_lbl.configure(text=step_name)
        self.status_lbl.configure(text=step_name)

    def _collect_settings(self) -> dict:
        return {
            "scale_type": self.scale_type,
            "scale_val": self.scale_val,
            "algorithm": self.get_selected_algo_code(),
            "remove_bg": self.switch_bg.get() == 1,
            "deblur": self.switch_deblur.get() == 1,
            "denoise_level": 3 if self.switch_denoise.get() == 1 else 0,
            "auto_hdr": self.switch_hdr.get() == 1
        }

    def _run_upscaling_job(self, source, settings, progress_callback):
        started = time.time()
        try:
            result, meta = UpscalerEngine.run_pipeline(
                source,
                progress_callback=progress_callback,
                cancel_check=self.cancel_event.is_set,
                **settings
            )
        except OperationCancelled:
            self.post_to_main(self._on_upscale_cancelled)
            return
        except Exception as exc:
            self.post_to_main(self._on_upscale_error, str(exc))
            return
        meta["elapsed_sec"] = round(time.time() - started, 2)
        gc.collect()
        self.post_to_main(self._on_upscale_success, result, meta)

    def _on_upscale_cancelled(self):
        self.is_processing = False
        self.hide_loading_screen()
        self.btn_upscale.configure(state="normal")
        self.progress_bar.set(0)
        self.status_lbl.configure(text=self.t("status_cancelled"))

    def _on_upscale_success(self, result: Image.Image, meta: dict):
        self.is_processing = False
        self.hide_loading_screen()
        self.btn_upscale.configure(state="normal")
        self._set_export_enabled(True)
        self.btn_copy.configure(state="normal")
        self.progress_bar.set(1.0)

        self.final_pil_img = result
        self.upscaled_pil_img = result
        self.image_epoch += 1
        self.status_lbl.configure(
            text=f"{self.t('status_done')} ({meta['target_width']:,}×{meta['target_height']:,} px in {meta['elapsed_sec']}s)"
        )
        self.update_stats()
        self.schedule_redraw()

    def _on_upscale_error(self, err_msg: str):
        self.is_processing = False
        self.hide_loading_screen()
        self.btn_upscale.configure(state="normal")
        self.progress_bar.set(0)
        self.status_lbl.configure(text=f"Error: {err_msg}")
        messagebox.showerror("Processing Error", err_msg)

    def request_preview(self, delay: int = 220):
        if self.preview_src is None or self.is_processing:
            return
        if self.preview_after_id is not None:
            self.after_cancel(self.preview_after_id)
        self.preview_gen += 1
        self.preview_after_id = self.after(delay, self._start_preview)

    def cancel_preview(self):
        if self.preview_after_id is not None:
            self.after_cancel(self.preview_after_id)
            self.preview_after_id = None
        self.preview_gen += 1

    def _start_preview(self):
        self.preview_after_id = None
        if self.preview_src is None or self.is_processing or self.preview_busy:
            return

        self.preview_busy = True
        self.status_lbl.configure(text=self.t("status_preview_busy"))
        threading.Thread(
            target=self._preview_worker,
            args=(self.preview_gen, self.preview_src, self._collect_settings()),
            daemon=True
        ).start()

    def _preview_worker(self, gen: int, source: Image.Image, settings: dict):
        def is_stale() -> bool:
            return gen != self.preview_gen

        try:
            result = UpscalerEngine.generate_preview(source, cancel_check=is_stale, **settings)
        except OperationCancelled:
            self.post_to_main(self._preview_finished, gen, None, None)
            return
        except Exception as exc:
            self.post_to_main(self._preview_finished, gen, None, str(exc))
            return
        self.post_to_main(self._preview_finished, gen, result, None)

    def _preview_finished(self, gen: int, result, error):
        self.preview_busy = False
        if gen != self.preview_gen:
            if self.preview_after_id is None:
                self._start_preview()
            return

        if error is not None:
            self.status_lbl.configure(text=f"Preview failed: {error}")
            return
        if result is None:
            return

        self.upscaled_pil_img = result
        self.image_epoch += 1
        self.status_lbl.configure(text=self.t("status_preview_ready"))
        self.schedule_redraw()

    def save_image(self):
        if self.final_pil_img is None:
            messagebox.showwarning("No Result", "Process the image first, then export the result.")
            return

        fmt = self.fmt_selector.get().lower()
        ext = "jpg" if fmt == "jpeg" else fmt

        base_name = os.path.splitext(self.active_filename)[0]
        out_w, out_h = self.final_pil_img.size
        factor = out_w / float(self.orig_w) if self.orig_w else 1.0
        default_filename = f"{base_name}_aupscaled_{factor:.2g}x_{out_w}x{out_h}.{ext}"

        save_path = filedialog.asksaveasfilename(
            title="Export Image",
            defaultextension=f".{ext}",
            filetypes=[
                (f"{fmt.upper()} Image (*.{ext})", f"*.{ext}"),
                ("PNG Image (*.png)", "*.png"),
                ("JPEG Image (*.jpg;*.jpeg)", "*.jpg;*.jpeg"),
                ("WEBP Image (*.webp)", "*.webp"),
                ("All Files (*.*)", "*.*")
            ],
            initialfile=default_filename
        )
        if not save_path:
            return

        target_ext = os.path.splitext(save_path)[1].lower().lstrip(".")
        self._set_export_enabled(False)
        self.status_lbl.configure(text=f"Exporting {os.path.basename(save_path)}...")
        threading.Thread(
            target=self._save_worker, args=(self.final_pil_img, save_path, target_ext), daemon=True
        ).start()

    def _save_worker(self, image: Image.Image, path: str, fmt: str):
        try:
            UpscalerEngine.write_image(image, path, fmt)
        except Exception as exc:
            self.post_to_main(self._on_save_done, path, str(exc))
            return
        self.post_to_main(self._on_save_done, path, None)

    def _on_save_done(self, path: str, error):
        self._set_export_enabled(self.final_pil_img is not None)
        if error is not None:
            self.status_lbl.configure(text="Export failed")
            messagebox.showerror("Export Error", f"Failed to export image: {error}")
            return
        self.status_lbl.configure(text=f"Exported: {os.path.basename(path)}")
        messagebox.showinfo("Exported", f"Image saved to:\n{path}")

    def batch_browse_files(self):
        files = filedialog.askopenfilenames(
            title="Select Images for Batch Processing",
            filetypes=[
                ("Image Files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tiff;*.tif"),
                ("All Files", "*.*")
            ]
        )
        if files:
            self.switch_workspace_mode("batch")
            self.add_paths_to_batch_queue(list(files))

    def batch_browse_folder(self):
        folder = filedialog.askdirectory(title="Select Folder with Images")
        if folder:
            self._safe_handle_dropped_paths([folder])

    def add_paths_to_batch_queue(self, file_paths: List[str]):
        for p in file_paths:
            if p not in self.batch_file_list:
                self.batch_file_list.append(p)
        self.refresh_batch_list_ui()

    def batch_clear_queue(self):
        self.batch_file_list.clear()
        self.refresh_batch_list_ui()

    def batch_change_output_dir(self):
        dir_choice = filedialog.askdirectory(title="Select Output Folder")
        if dir_choice:
            self.batch_output_dir = dir_choice
            self.batch_out_lbl.configure(text=f"Output: {self.batch_output_dir}")

    def refresh_batch_list_ui(self):
        for widget in self.batch_listbox_frame.winfo_children():
            widget.destroy()

        if not self.batch_file_list:
            self.batch_empty_lbl = ctk.CTkLabel(
                self.batch_listbox_frame,
                text="No images in batch queue.\nDrag & drop files or click Add Images.",
                font=self.get_ui_font(13), text_color=THEME_COLORS["text_muted"]
            )
            self.batch_empty_lbl.pack(pady=80)
            return

        for idx, fpath in enumerate(self.batch_file_list):
            row_frame = ctk.CTkFrame(self.batch_listbox_frame, fg_color=THEME_COLORS["bg_card_sub"], height=34, corner_radius=6)
            row_frame.pack(fill="x", padx=4, pady=3)

            size_txt = ""
            try:
                with Image.open(fpath) as im:
                    size_txt = f" ({im.width}×{im.height})"
            except Exception:
                pass

            fname_lbl = ctk.CTkLabel(
                row_frame, text=f"{idx + 1}. {os.path.basename(fpath)}{size_txt}",
                font=self.get_ui_font(11), text_color=THEME_COLORS["text_primary"], anchor="w"
            )
            fname_lbl.pack(side="left", padx=10, fill="x", expand=True)

            del_btn = ctk.CTkButton(
                row_frame, text="✕", width=26, height=24, fg_color="transparent",
                hover_color=THEME_COLORS["danger_hover"], text_color=THEME_COLORS["danger"],
                font=self.get_ui_font(11),
                command=lambda p=fpath: self.remove_batch_item(p)
            )
            del_btn.pack(side="right", padx=6, pady=4)

    def remove_batch_item(self, path: str):
        if path in self.batch_file_list:
            self.batch_file_list.remove(path)
            self.refresh_batch_list_ui()

    def start_batch_upscale(self):
        if not self.batch_file_list:
            messagebox.showwarning("Queue Empty", "Add images to the batch queue first.")
            return

        if self.is_processing:
            return

        os.makedirs(self.batch_output_dir, exist_ok=True)
        self.cancel_preview()
        self.cancel_event.clear()
        self.is_processing = True
        self.btn_batch_run.configure(state="disabled")
        self.btn_batch_cancel.configure(state="normal")
        self.progress_bar.set(0.0)

        threading.Thread(
            target=self._run_batch_worker,
            args=(
                list(self.batch_file_list),
                self.batch_output_dir,
                self._collect_settings(),
                self.fmt_selector.get().upper()
            ),
            daemon=True
        ).start()

    def _run_batch_worker(self, files, out_dir, settings, fmt):
        total = len(files)
        success_count = 0
        failures = []
        cancelled = False
        extension = "jpg" if fmt in ("JPEG", "JPG") else fmt.lower()

        for idx, fpath in enumerate(files):
            if self.cancel_event.is_set():
                cancelled = True
                break
            name = os.path.basename(fpath)
            self.post_to_main(self._on_batch_progress_ui, idx / total, idx + 1, total, name)

            try:
                with Image.open(fpath) as opened:
                    image = ImageOps.exif_transpose(opened)
                    image.load()

                result, _ = UpscalerEngine.run_pipeline(
                    image, cancel_check=self.cancel_event.is_set, **settings
                )

                base_name = os.path.splitext(name)[0]
                dest_path = os.path.join(out_dir, f"{base_name}_aupscaled.{extension}")
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(out_dir, f"{base_name}_aupscaled_{counter}.{extension}")
                    counter += 1

                UpscalerEngine.write_image(result, dest_path, fmt)
                success_count += 1
            except OperationCancelled:
                cancelled = True
                break
            except Exception as exc:
                failures.append(f"{name}: {exc}")

            gc.collect()

        self.post_to_main(self._on_batch_complete, success_count, total, out_dir, failures, cancelled)

    def _on_batch_progress_ui(self, p: float, i: int, total: int, fn: str):
        self.progress_bar.set(p)
        self.status_lbl.configure(text=f"Batch ({i}/{total}): {fn}")

    def _on_batch_complete(self, count: int, total: int, out_dir: str, failures, cancelled: bool = False):
        self.is_processing = False
        self.btn_batch_run.configure(state="normal")
        self.btn_batch_cancel.configure(state="disabled")
        if cancelled:
            self.progress_bar.set(0.0)
            self.status_lbl.configure(text=f"{self.t('status_cancelled')} ({count}/{total} completed)")
            return

        self.progress_bar.set(1.0)
        self.status_lbl.configure(text=f"Batch complete: {count}/{total} exported")

        message = f"Processed {count} of {total} images.\nSaved to:\n{out_dir}"
        if failures:
            shown = "\n".join(failures[:5])
            extra = f"\n...and {len(failures) - 5} more" if len(failures) > 5 else ""
            message += f"\n\nFailed:\n{shown}{extra}"
            messagebox.showwarning("Batch Finished With Errors", message)
        else:
            messagebox.showinfo("Batch Complete", message)


if __name__ == "__main__":
    app = AupscalerApp()
    app.mainloop()
