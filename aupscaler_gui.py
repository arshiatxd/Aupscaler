import os
import sys
import io
import math
import time
import threading
import ctypes
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk, ImageOps, ImageDraw, ImageFont, ImageGrab
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
from backend.upscaler import UpscalerEngine

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
    "bg_root": ("#f8fafc", "#0b0f19"),
    "bg_sidebar": ("#ffffff", "#111827"),
    "bg_card": ("#ffffff", "#1e293b"),
    "bg_card_sub": ("#f8fafc", "#0f172a"),
    "bg_metric": ("#f8fafc", "#0f172a"),
    "border": ("#e2e8f0", "#334155"),
    "border_active": ("#cbd5e1", "#475569"),
    "accent": ("#2563eb", "#3b82f6"),
    "accent_hover": ("#1d4ed8", "#2563eb"),
    "accent_cyan": ("#0284c7", "#38bdf8"),
    "accent_success": ("#10b981", "#10b981"),
    "text_primary": ("#0f172a", "#f8fafc"),
    "text_secondary": ("#334155", "#cbd5e1"),
    "text_muted": ("#64748b", "#94a3b8"),
    "canvas_bg_hex": {"light": "#f1f5f9", "dark": "#0b0f19"},
    "btn_secondary": ("#ffffff", "#1e293b"),
    "btn_secondary_hover": ("#f1f5f9", "#334155"),
    "opt_bg": ("#ffffff", "#1e293b"),
    "opt_btn": ("#f1f5f9", "#334155"),
    "opt_btn_hover": ("#e2e8f0", "#475569")
}

TRANSLATIONS = {
    "en": {
        "title": "aupscaler",
        "subtitle": "Deep Learning Super-Resolution",
        "tab_single": "Single Image",
        "tab_batch": "Batch Queue",
        "drop_hint": "Drag & Drop Image or Click Select",
        "btn_browse": "Select Image",
        "btn_paste": "Paste",
        "btn_sample": "Sample",
        "btn_clear": "Clear",
        "sec_scale": "Scale Multiplier",
        "presets_mult": "Scale Presets",
        "custom_scale": "Custom Scale",
        "target_dim": "Target Output:",
        "est_ram": "Estimated RAM:",
        "pro_features": "Enhancement Tools",
        "btn_reset_effects": "Reset",
        "feat_deblur": "Clarity & Focus Deblur",
        "feat_denoise": "Deep Denoise & JPEG Cleaner",
        "feat_hdr": "Natural HDR & Color Balance",
        "feat_bg": "Deep Learning Background Cutout (PNG)",
        "algo_label": "Deep Learning Engine",
        "fmt_label": "Format:",
        "btn_upscale": "Upscale Image",
        "btn_preview": "Update Live Preview",
        "btn_save": "Save Image",
        "btn_copy": "Copy",
        "slider_instr": "Drag divider or hold Spacebar to compare",
        "status_ready": "Ready",
        "status_processing": "Deep Learning neural inference in progress...",
        "status_done": "Deep Learning Upscaling complete!",
        "reset_zoom": "Fit View",
        "actual_size": "1:1 (100%)",
        "zoom_200": "200%",
        "before_tag": "Original (Low-Res)",
        "after_tag": "Upscaled Image",
        "save_success": "Image saved successfully!",
        "copied_clipboard": "Image copied to clipboard!",
        "batch_add_files": "Add Images",
        "batch_add_folder": "Add Folder",
        "batch_clear": "Clear Queue",
        "batch_out_dir": "Output Folder:",
        "batch_start": "Start Batch Upscaling",
        "batch_status_ready": "Batch queue ready",
        "no_image": "Please load an image first.",
        "loading_title": "Deep Learning Super-Resolution Active",
        "loading_subtitle": "Reconstructing high-frequency textures with Deep CNN..."
    },
    "es": {
        "title": "aupscaler",
        "subtitle": "Super-Resolución con Deep Learning",
        "tab_single": "Imagen Individual",
        "tab_batch": "Cola por Lotes",
        "drop_hint": "Arrastra una imagen o selecciona un archivo",
        "btn_browse": "Seleccionar",
        "btn_paste": "Pegar",
        "btn_sample": "Muestra",
        "btn_clear": "Limpiar",
        "sec_scale": "Multiplicador de Escala",
        "presets_mult": "Preajustes de Escala",
        "custom_scale": "Escala Personalizada",
        "target_dim": "Dimensiones Finales:",
        "est_ram": "RAM Estimada:",
        "pro_features": "Herramientas de Mejora",
        "btn_reset_effects": "Restablecer",
        "feat_deblur": "Claridad y Enfoque",
        "feat_denoise": "Eliminar Ruido y Bloques JPEG",
        "feat_hdr": "HDR Natural y Balance de Color",
        "feat_bg": "Recorte de Fondo Deep Learning (PNG)",
        "algo_label": "Motor Deep Learning",
        "fmt_label": "Formato:",
        "btn_upscale": "Escalar Imagen",
        "btn_preview": "Actualizar Vista Previa",
        "btn_save": "Guardar Imagen",
        "btn_copy": "Copiar",
        "slider_instr": "Arrastra la barra o presiona Espacio para comparar",
        "status_ready": "Listo",
        "status_processing": "Inferencia Deep Learning en curso...",
        "status_done": "¡Escalado completado con éxito!",
        "reset_zoom": "Ajustar",
        "actual_size": "1:1 (100%)",
        "zoom_200": "200%",
        "before_tag": "Original (Baja)",
        "after_tag": "Imagen Escalada",
        "save_success": "¡Imagen guardada correctamente!",
        "copied_clipboard": "¡Imagen copiada al portapapeles!",
        "batch_add_files": "Añadir Imágenes",
        "batch_add_folder": "Añadir Carpeta",
        "batch_clear": "Limpiar Cola",
        "batch_out_dir": "Carpeta de Salida:",
        "batch_start": "Iniciar Lote",
        "batch_status_ready": "Cola de lote lista",
        "no_image": "Por favor carga una imagen primero.",
        "loading_title": "Super-Resolución Deep Learning Activa",
        "loading_subtitle": "Reconstruyendo texturas con Redes Neuronales..."
    },
    "fr": {
        "title": "aupscaler",
        "subtitle": "Super-Résolution par Deep Learning",
        "tab_single": "Image Unique",
        "tab_batch": "File par Lots",
        "drop_hint": "Glissez une image ou cliquez sur Sélectionner",
        "btn_browse": "Sélectionner",
        "btn_paste": "Coller",
        "btn_sample": "Exemple",
        "btn_clear": "Effacer",
        "sec_scale": "Facteur d'Agrandissement",
        "presets_mult": "Préréglages d'Échelle",
        "custom_scale": "Échelle Personnalisée",
        "target_dim": "Dimensions Cibles:",
        "est_ram": "RAM Estimée:",
        "pro_features": "Outils d'Amélioration",
        "btn_reset_effects": "Réinitialiser",
        "feat_deblur": "Netteté et Déflouage",
        "feat_denoise": "Suppression du Bruit & JPEG",
        "feat_hdr": "HDR Naturel & Équilibre Couleur",
        "feat_bg": "Détourage Fond Deep Learning (PNG)",
        "algo_label": "Moteur Deep Learning",
        "fmt_label": "Format:",
        "btn_upscale": "Agrandir l'Image",
        "btn_preview": "Actualiser l'Aperçu",
        "btn_save": "Enregistrer",
        "btn_copy": "Copier",
        "slider_instr": "Glissez le séparateur ou maintenez Espace pour comparer",
        "status_ready": "Prêt",
        "status_processing": "Inférence Deep Learning en cours...",
        "status_done": "Agrandissement réussi !",
        "reset_zoom": "Ajuster",
        "actual_size": "1:1 (100%)",
        "zoom_200": "200%",
        "before_tag": "Original",
        "after_tag": "Image Agrandie",
        "save_success": "Image enregistrée avec succès !",
        "copied_clipboard": "Image copiée dans le presse-papiers !",
        "batch_add_files": "Ajouter Fichiers",
        "batch_add_folder": "Ajouter Dossier",
        "batch_clear": "Vider la File",
        "batch_out_dir": "Dossier de Sortie:",
        "batch_start": "Démarrer le Traitement",
        "batch_status_ready": "File par lots prête",
        "no_image": "Veuillez d'abord charger une image.",
        "loading_title": "Super-Résolution Deep Learning en cours",
        "loading_subtitle": "Synthèse neuronale des détails..."
    },
    "de": {
        "title": "aupscaler",
        "subtitle": "Deep Learning Superauflösung",
        "tab_single": "Einzelbild",
        "tab_batch": "Stapelverarbeitung",
        "drop_hint": "Bild hierher ziehen oder Auswählen klicken",
        "btn_browse": "Auswählen",
        "btn_paste": "Einfügen",
        "btn_sample": "Beispiel",
        "btn_clear": "Löschen",
        "sec_scale": "Skalierungsfaktor",
        "presets_mult": "Skalierungs-Presets",
        "custom_scale": "Eigener Maßstab",
        "target_dim": "Ziel-Auflösung:",
        "est_ram": "Geschätzter RAM:",
        "pro_features": "Verbesserungs-Werkzeuge",
        "btn_reset_effects": "Zurücksetzen",
        "feat_deblur": "Klarheit & Entschärfen",
        "feat_denoise": "Rausch- & JPEG-Bereinigung",
        "feat_hdr": "Natürliches HDR & Farbbalance",
        "feat_bg": "Deep Learning Freistellen (PNG)",
        "algo_label": "Deep Learning Engine",
        "fmt_label": "Format:",
        "btn_upscale": "Bild Hochskalieren",
        "btn_preview": "Vorschau aktualisieren",
        "btn_save": "Speichern",
        "btn_copy": "Kopieren",
        "slider_instr": "Trennlinie ziehen oder Leertaste halten zum Vergleich",
        "status_ready": "Bereit",
        "status_processing": "Neuronale Deep Learning Berechnung...",
        "status_done": "Skalierung erfolgreich!",
        "reset_zoom": "Einpassen",
        "actual_size": "1:1 (100%)",
        "zoom_200": "200%",
        "before_tag": "Original",
        "after_tag": "Hochskaliertes Bild",
        "save_success": "Bild erfolgreich gespeichert!",
        "copied_clipboard": "In die Zwischenablage kopiert!",
        "batch_add_files": "Dateien hinzufügen",
        "batch_add_folder": "Ordner hinzufügen",
        "batch_clear": "Liste leeren",
        "batch_out_dir": "Zielordner:",
        "batch_start": "Stapelverarbeitung starten",
        "batch_status_ready": "Warteschlange bereit",
        "no_image": "Bitte zuerst ein Bild laden.",
        "loading_title": "Deep Learning Superauflösung aktiv",
        "loading_subtitle": "Neuronales Netzwerk rekonstruiert Kanten..."
    },
    "ja": {
        "title": "aupscaler",
        "subtitle": "ディープラーニング超解像",
        "tab_single": "個別処理",
        "tab_batch": "一括処理キュー",
        "drop_hint": "画像をドラッグ＆ドロップ または 選択",
        "btn_browse": "選択",
        "btn_paste": "貼り付け",
        "btn_sample": "サンプル",
        "btn_clear": "クリア",
        "sec_scale": "拡大倍率の設定",
        "presets_mult": "倍率プリセット",
        "custom_scale": "カスタム倍率",
        "target_dim": "出力解像度:",
        "est_ram": "推定RAM使用量:",
        "pro_features": "高画質化ツール",
        "btn_reset_effects": "リセット",
        "feat_deblur": "鮮明化・ボケ補正",
        "feat_denoise": "高度ノイズ＆ブロック除去",
        "feat_hdr": "自然なHDR＆カラーバランス",
        "feat_bg": "ディープラーニング背景切抜 (PNG)",
        "algo_label": "深層学習エンジン",
        "fmt_label": "形式:",
        "btn_upscale": "高解像度化を実行",
        "btn_preview": "プレビュー更新",
        "btn_save": "画像を保存",
        "btn_copy": "コピー",
        "slider_instr": "仕切り線を動かすかスペースキー長押しで比較",
        "status_ready": "準備完了",
        "status_processing": "深層学習ニューラル推論を実行中...",
        "status_done": "処理が完了しました！",
        "reset_zoom": "全体表示",
        "actual_size": "等倍 (1:1)",
        "zoom_200": "200%",
        "before_tag": "元画像 (低画質)",
        "after_tag": "高画質化画像",
        "save_success": "画像を正常に保存しました！",
        "copied_clipboard": "クリップボードにコピーしました！",
        "batch_add_files": "画像を追加",
        "batch_add_folder": "フォルダ追加",
        "batch_clear": "キューをクリア",
        "batch_out_dir": "保存先フォルダ:",
        "batch_start": "一括処理を開始",
        "batch_status_ready": "一括キュー準備完了",
        "no_image": "最初に画像を読み込んでください。",
        "loading_title": "深層学習ニューラル超解像処理中",
        "loading_subtitle": "CNNが高周波テクスチャを復元しています..."
    },
    "zh": {
        "title": "aupscaler",
        "subtitle": "深度学习图像超分辨率与画质增强",
        "tab_single": "单张处理",
        "tab_batch": "批量队列",
        "drop_hint": "拖拽图片至此处 或 点击选择文件",
        "btn_browse": "选择图片",
        "btn_paste": "粘贴",
        "btn_sample": "示例",
        "btn_clear": "清空",
        "sec_scale": "缩放倍率设置",
        "presets_mult": "倍率快捷预设",
        "custom_scale": "自定义缩放",
        "target_dim": "目标输出尺寸:",
        "est_ram": "预计内存消耗:",
        "pro_features": "画质增强工具",
        "btn_reset_effects": "重置增强",
        "feat_deblur": "清晰去模糊与轮廓重塑",
        "feat_denoise": "深度降噪与消除 JPEG 伪影",
        "feat_hdr": "自然 HDR 与色彩平衡",
        "feat_bg": "深度学习智能去背景抠图 (PNG)",
        "algo_label": "深度学习神经网络",
        "fmt_label": "格式:",
        "btn_upscale": "执行超分辨率放大",
        "btn_preview": "更新实时预览",
        "btn_save": "保存图片",
        "btn_copy": "复制",
        "slider_instr": "左右拖动分界线 或 长按空格键对比画质",
        "status_ready": "就绪",
        "status_processing": "深度学习神经网络推理中...",
        "status_done": "超分辨率放大完成！",
        "reset_zoom": "适应窗口",
        "actual_size": "1:1 原图大小",
        "zoom_200": "200%",
        "before_tag": "原始图像 (模糊)",
        "after_tag": "超分辨率放大图",
        "save_success": "高清图像保存成功！",
        "copied_clipboard": "已复制到剪贴板！",
        "batch_add_files": "添加图片",
        "batch_add_folder": "添加文件夹",
        "batch_clear": "清空队列",
        "batch_out_dir": "导出目录:",
        "batch_start": "开始批量放大",
        "batch_status_ready": "批量队列就绪",
        "no_image": "请先选择一张图片。",
        "loading_title": "深度学习神经网络超分辨率渲染中",
        "loading_subtitle": "CNN 正在高精度重构图像边缘与微观细节..."
    },
    "fa": {
        "title": "aupscaler",
        "subtitle": "ارتقای رزولوشن با یادگیری عمیق",
        "tab_single": "پردازش تصویر",
        "tab_batch": "پردازش گروهی",
        "drop_hint": "تصویر را اینجا رها کنید یا فایل را انتخاب نمایید",
        "btn_browse": "انتخاب تصویر",
        "btn_paste": "چسباندن",
        "btn_sample": "نمونه",
        "btn_clear": "پاکسازی",
        "sec_scale": "میزان افزایش رزولوشن",
        "presets_mult": "ضرایب آماده",
        "custom_scale": "مقدار دلخواه",
        "target_dim": "ابعاد خروجی نهایی:",
        "est_ram": "رم مورد نیاز:",
        "pro_features": "ابزارهای ارتقای کیفیت",
        "btn_reset_effects": "بازنشانی فیلترها",
        "feat_deblur": "شفافیت و رفع تاری",
        "feat_denoise": "حذف نویز عمیق و دانه‌های تصویر",
        "feat_hdr": "کنتراست طبیعی HDR و رنگ",
        "feat_bg": "حذف خودکار پس‌زمینه (PNG)",
        "algo_label": "موتور یادگیری عمیق",
        "fmt_label": "فرمت خروجی:",
        "btn_upscale": "ارتقای کیفیت تصویر",
        "btn_preview": "پیش‌نمایش زنده",
        "btn_save": "ذخیره تصویر",
        "btn_copy": "کپی",
        "slider_instr": "اسلایدر را بکشید یا دکمه Space را نگه دارید",
        "status_ready": "آماده به کار",
        "status_processing": "در حال پردازش با شبکه عصبی یادگیری عمیق...",
        "status_done": "ارتقای کیفیت با موفقیت انجام شد!",
        "reset_zoom": "تناسب با صفحه",
        "actual_size": "اندازه ۱:۱",
        "zoom_200": "۲۰۰%",
        "before_tag": "تصویر اصلی (کیفیت پایین)",
        "after_tag": "تصویر ارتقا یافته",
        "save_success": "تصویر با موفقیت ذخیره شد!",
        "copied_clipboard": "تصویر در کلیپ‌بورد کپی شد!",
        "batch_add_files": "افزودن تصاویر",
        "batch_add_folder": "افزودن پوشه",
        "batch_clear": "پاکسازی لیست",
        "batch_out_dir": "پوشه مقصد:",
        "batch_start": "شروع پردازش گروهی",
        "batch_status_ready": "صف پردازش آماده است",
        "no_image": "لطفاً ابتدا یک تصویر انتخاب کنید.",
        "loading_title": "شبکه عصبی ارتقای رزولوشن در حال اجرا است",
        "loading_subtitle": "در حال بازسازی بافت‌ها با شبکه عمیق CNN..."
    },
    "ar": {
        "title": "aupscaler",
        "subtitle": "ترقية الدقة بالتعلم العميق",
        "tab_single": "صورة فردية",
        "tab_batch": "المعالجة الدفعية",
        "drop_hint": "اسحب الصورة إلى هنا أو اختر ملفاً",
        "btn_browse": "اختيار الصورة",
        "btn_paste": "لصق",
        "btn_sample": "تجربة",
        "btn_clear": "مسح",
        "sec_scale": "مقياس التكبير",
        "presets_mult": "مضاعفات سريعة",
        "custom_scale": "مقياس مخصص",
        "target_dim": "الأبعاد المستهدفة:",
        "est_ram": "الذاكرة المقدرة:",
        "pro_features": "أدوات التحسين",
        "btn_reset_effects": "إعادة ضبط",
        "feat_deblur": "إزالة الضبابية وتحسين الوضوح",
        "feat_denoise": "إزالة التشويش والضوضاء العمیقة",
        "feat_hdr": "تباين HDR طبيعي وتوازن الألوان",
        "feat_bg": "إزالة الخلفية بالتعلم العميق (PNG)",
        "algo_label": "محرك التعلم العميق",
        "fmt_label": "الصيغة:",
        "btn_upscale": "ترقية الصورة",
        "btn_preview": "تحديث المعاينة",
        "btn_save": "حفظ الصورة",
        "btn_copy": "نسخ",
        "slider_instr": "اسحب الفاصل أو اضغط مسافة للمقارنة",
        "status_ready": "جاهز",
        "status_processing": "جار المعالجة بالشبكات العصبية العمیقة...",
        "status_done": "تمت الترقية بنجاح!",
        "reset_zoom": "ملاءمة الشاشة",
        "actual_size": "حجم 1:1",
        "zoom_200": "200%",
        "before_tag": "الأصلية (منخفضة)",
        "after_tag": "الصورة فائقة الدقة",
        "save_success": "تم حفظ الصورة بنجاح!",
        "copied_clipboard": "تم نسخ الصورة إلى الحافظة!",
        "batch_add_files": "إضافة صور",
        "batch_add_folder": "إضافة مجلد",
        "batch_clear": "مسح القائمة",
        "batch_out_dir": "مجلد الإخراج:",
        "batch_start": "بدء المعالجة الدفعية",
        "batch_status_ready": "قائمة المعالجة جاهزة",
        "no_image": "يرجى اختيار صورة أولاً.",
        "loading_title": "محرك الترقية بالتعلم العميق يعمل الآن",
        "loading_subtitle": "جار إعادة بناء الحواف بالشبكة العصبية CNN..."
    },
    "ru": {
        "title": "aupscaler",
        "subtitle": "Супер-разрешение на базе Deep Learning",
        "tab_single": "Одно фото",
        "tab_batch": "Пакетная очередь",
        "drop_hint": "Перетащите изображение сюда или выберите файл",
        "btn_browse": "Выбрать",
        "btn_paste": "Вставить",
        "btn_sample": "Пример",
        "btn_clear": "Очистить",
        "sec_scale": "Масштаб увеличения",
        "presets_mult": "Быстрые масштабы",
        "custom_scale": "Свой множитель",
        "target_dim": "Целевой размер:",
        "est_ram": "Оценка ОЗУ:",
        "pro_features": "Инструменты улучшения",
        "btn_reset_effects": "Сбросить",
        "feat_deblur": "Устранение размытия и резкость",
        "feat_denoise": "Глубокое удаление шума и артефактов",
        "feat_hdr": "Естественный HDR и цветовой баланс",
        "feat_bg": "Удаление фона Deep Learning (PNG)",
        "algo_label": "Нейросеть Deep Learning",
        "fmt_label": "Формат:",
        "btn_upscale": "Увеличить изображение",
        "btn_preview": "Обновить превью",
        "btn_save": "Сохранить",
        "btn_copy": "Копировать",
        "slider_instr": "Перемещайте разделитель или удерживайте Пробел",
        "status_ready": "Готов",
        "status_processing": "Инференс глубокой нейросети...",
        "status_done": "Масштабирование завершено!",
        "reset_zoom": "По размеру окна",
        "actual_size": "Масштаб 1:1",
        "zoom_200": "200%",
        "before_tag": "Исходное (Низкое)",
        "after_tag": "Увеличенное изображение",
        "save_success": "Изображение успешно сохранено!",
        "copied_clipboard": "Скопировано в буфер обмена!",
        "batch_add_files": "Добавить файлы",
        "batch_add_folder": "Добавить папку",
        "batch_clear": "Очистить очередь",
        "batch_out_dir": "Папка сохранения:",
        "batch_start": "Запустить пакет",
        "batch_status_ready": "Очередь готова",
        "no_image": "Пожалуйста, сначала загрузите изображение.",
        "loading_title": "Нейросеть Deep Learning активна",
        "loading_subtitle": "Реконструкция текстур глубокой моделью CNN..."
    },
    "pt": {
        "title": "aupscaler",
        "subtitle": "Super-Resolução por Deep Learning",
        "tab_single": "Imagem Única",
        "tab_batch": "Fila em Lote",
        "drop_hint": "Arraste uma imagem ou clique em Selecionar",
        "btn_browse": "Selecionar",
        "btn_paste": "Colar",
        "btn_sample": "Exemplo",
        "btn_clear": "Limpar",
        "sec_scale": "Multiplicador de Escala",
        "presets_mult": "Multiplicadores",
        "custom_scale": "Escala Personalizada",
        "target_dim": "Dimensões Finais:",
        "est_ram": "RAM Estimada:",
        "pro_features": "Recursos de Aprimoramento",
        "btn_reset_effects": "Redefinir",
        "feat_deblur": "Nitidez e Desfoque",
        "feat_denoise": "Limpeza Profunda de Ruído e JPEG",
        "feat_hdr": "HDR Natural e Equilíbrio de Cores",
        "feat_bg": "Remover Fundo Deep Learning (PNG)",
        "algo_label": "Motor Deep Learning",
        "fmt_label": "Formato:",
        "btn_upscale": "Ampliar Imagem",
        "btn_preview": "Atualizar Prévia",
        "btn_save": "Salvar",
        "btn_copy": "Copiar",
        "slider_instr": "Arraste para comparar ou segure Espaço",
        "status_ready": "Pronto",
        "status_processing": "Inferência de rede neural em andamento...",
        "status_done": "Ampliação concluída com sucesso!",
        "reset_zoom": "Ajustar à Tela",
        "actual_size": "Tamanho Real (1:1)",
        "zoom_200": "200%",
        "before_tag": "Original (Baixa)",
        "after_tag": "Imagem Ampliada",
        "save_success": "Imagem salva com sucesso!",
        "copied_clipboard": "Imagem copiada para a área de transferência!",
        "batch_add_files": "Adicionar Imagens",
        "batch_add_folder": "Adicionar Pasta",
        "batch_clear": "Limpar Fila",
        "batch_out_dir": "Pasta de Destino:",
        "batch_start": "Iniciar Processamento",
        "batch_status_ready": "Fila pronta",
        "no_image": "Por favor, carregue uma imagem primeiro.",
        "loading_title": "Super-Resolução Deep Learning em Execução",
        "loading_subtitle": "Rede Neural CNN reconstruindo texturas..."
    }
}


class AupscalerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.current_theme = "light"
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")

        self.title("aupscaler - Deep Learning Super-Resolution")
        self.geometry("1420x920")
        self.minsize(1120, 740)

        self.setup_window_icon()

        self.current_lang = "en"
        self.current_img_bytes = None
        self.current_pil_img = None
        self.upscaled_bytes = None
        self.upscaled_pil_img = None
        self.active_filename = "image.png"

        self.cached_disp_w = 0
        self.cached_disp_h = 0
        self.cached_before_thumb = None
        self.cached_after_thumb = None

        self.orig_w = 0
        self.orig_h = 0
        self.scale_type = "multiplier"
        self.scale_val = 2.0
        self.split_ratio = 0.5
        self.hold_space_active = False

        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.pan_start_x = 0
        self.pan_start_y = 0

        self.is_processing = False
        self.preview_pending = False
        self.loading_start_time = 0.0
        self.loading_timer_id = None
        self.batch_file_list: List[str] = []
        self.batch_output_dir = os.path.join(os.path.expanduser("~"), "Pictures", "aupscaler_output")

        self.setup_ui()
        self.setup_crashproof_drag_and_drop()
        self.setup_keyboard_shortcuts()
        self.update_translations()
        self.update_stats()

    def get_ui_font(self, size: int = 12, weight: str = "normal") -> ctk.CTkFont:
        if self.current_lang in ("fa", "ar"):
            family = "A Nafis"
            size = size + 3
        else:
            family = "Segoe UI"
        return ctk.CTkFont(family=family, size=size, weight=weight)

    def toggle_theme(self):
        target_theme = "dark" if self.current_theme == "light" else "light"
        self.current_theme = target_theme

        target_mode = "Dark" if target_theme == "dark" else "Light"
        ctk.set_appearance_mode(target_mode)
        self.theme_btn.configure(text="☀️" if target_theme == "dark" else "🌙")

        canvas_bg = THEME_COLORS["canvas_bg_hex"][target_theme]
        self.canvas.configure(bg=canvas_bg)

        self.select_preset(self.scale_val)
        self.cached_disp_w = 0
        self.update_display_cache()

    def reset_effects(self):
        self.switch_deblur.deselect()
        self.switch_denoise.deselect()
        self.switch_hdr.deselect()
        self.switch_bg.deselect()
        if self.current_img_bytes:
            self.trigger_live_preview()

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

                self.after(10, lambda paths=decoded_paths: self._safe_handle_dropped_paths(paths))
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
                self.tab_view.set(self.t("tab_single"))
                self.load_image_from_path(expanded_files[0])
            else:
                self.tab_view.set(self.t("tab_batch"))
                self.add_paths_to_batch_queue(expanded_files)
        except Exception:
            pass

    def setup_keyboard_shortcuts(self):
        self.bind("<Control-v>", lambda e: self.paste_from_clipboard())
        self.bind("<Control-V>", lambda e: self.paste_from_clipboard())
        self.bind("<Control-c>", lambda e: self.copy_to_clipboard())
        self.bind("<Control-C>", lambda e: self.copy_to_clipboard())
        self.bind("<Control-s>", lambda e: self.save_image())
        self.bind("<Control-S>", lambda e: self.save_image())

        self.bind("<KeyPress-space>", self.on_space_press)
        self.bind("<KeyRelease-space>", self.on_space_release)

    def on_space_press(self, event):
        if not self.hold_space_active and self.current_pil_img:
            self.hold_space_active = True
            self.redraw_comparison()

    def on_space_release(self, event):
        if self.hold_space_active:
            self.hold_space_active = False
            self.redraw_comparison()

    def t(self, key: str) -> str:
        lang_dict = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["en"])
        return lang_dict.get(key, TRANSLATIONS["en"].get(key, key))

    def setup_ui(self):
        self.configure(fg_color=THEME_COLORS["bg_root"])
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkScrollableFrame(
            self, width=430, corner_radius=0,
            fg_color=THEME_COLORS["bg_sidebar"],
            border_width=1, border_color=THEME_COLORS["border"]
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.header_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=16, pady=(14, 6))

        logo_img_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.isfile(logo_img_path):
            try:
                pil_logo = Image.open(logo_img_path).resize((42, 42), Image.Resampling.LANCZOS)
                self.header_logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(42, 42))
                self.logo_widget = ctk.CTkLabel(self.header_frame, image=self.header_logo_img, text="")
                self.logo_widget.pack(side="left", padx=(0, 10))
            except Exception:
                self.logo_widget = ctk.CTkLabel(
                    self.header_frame, text="au", font=self.get_ui_font(18, "bold"),
                    width=42, height=42, fg_color=THEME_COLORS["accent"], corner_radius=10, text_color="#ffffff"
                )
                self.logo_widget.pack(side="left", padx=(0, 10))
        else:
            self.logo_widget = ctk.CTkLabel(
                self.header_frame, text="au", font=self.get_ui_font(18, "bold"),
                width=42, height=42, fg_color=THEME_COLORS["accent"], corner_radius=10, text_color="#ffffff"
            )
            self.logo_widget.pack(side="left", padx=(0, 10))

        self.title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.title_box.pack(side="left", fill="both", expand=True)

        self.app_title_lbl = ctk.CTkLabel(
            self.title_box, text="aupscaler", font=self.get_ui_font(20, "bold"),
            text_color=THEME_COLORS["text_primary"], anchor="w"
        )
        self.app_title_lbl.pack(anchor="w")

        self.app_sub_lbl = ctk.CTkLabel(
            self.title_box, text="Deep Learning Super-Resolution", font=self.get_ui_font(11),
            text_color=THEME_COLORS["text_muted"], anchor="w"
        )
        self.app_sub_lbl.pack(anchor="w")

        self.theme_btn = ctk.CTkButton(
            self.header_frame, text="🌙", width=38, height=38, corner_radius=10,
            fg_color=THEME_COLORS["btn_secondary"],
            hover_color=THEME_COLORS["btn_secondary_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text_primary"], font=ctk.CTkFont(size=14),
            command=self.toggle_theme
        )
        self.theme_btn.pack(side="right", padx=(6, 0))

        self.lang_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=[
                "English (en)", "فارسی (fa)", "العربية (ar)", "Español (es)", "Français (fr)",
                "Deutsch (de)", "日本語 (ja)", "中文 (zh)", "Русский (ru)", "Português (pt)"
            ],
            command=self.on_lang_changed,
            height=34,
            fg_color=THEME_COLORS["opt_bg"],
            button_color=THEME_COLORS["opt_btn"],
            button_hover_color=THEME_COLORS["opt_btn_hover"],
            dropdown_fg_color=THEME_COLORS["opt_bg"],
            dropdown_text_color=THEME_COLORS["text_primary"],
            dropdown_hover_color=THEME_COLORS["opt_btn"],
            text_color=THEME_COLORS["text_primary"],
            font=self.get_ui_font(12), corner_radius=8,
            dropdown_font=self.get_ui_font(12)
        )
        self.lang_menu.pack(fill="x", padx=16, pady=(4, 10))

        self.file_card = ctk.CTkFrame(
            self.sidebar, fg_color=THEME_COLORS["bg_card"], corner_radius=12,
            border_width=1, border_color=THEME_COLORS["border"]
        )
        self.file_card.pack(fill="x", padx=16, pady=4)

        self.drop_hint_lbl = ctk.CTkLabel(
            self.file_card, text="Drag & Drop Image or Click Select",
            font=self.get_ui_font(11, "bold"), text_color=THEME_COLORS["accent_cyan"]
        )
        self.drop_hint_lbl.pack(fill="x", padx=12, pady=(10, 4))

        self.file_btn_row = ctk.CTkFrame(self.file_card, fg_color="transparent")
        self.file_btn_row.pack(fill="x", padx=12, pady=(4, 6))

        self.btn_browse = ctk.CTkButton(
            self.file_btn_row, text="Select Image", command=self.browse_file,
            height=34, fg_color=THEME_COLORS["accent"], hover_color=THEME_COLORS["accent_hover"],
            font=self.get_ui_font(12, "bold"), corner_radius=8
        )
        self.btn_browse.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_paste = ctk.CTkButton(
            self.file_btn_row, text="Paste", command=self.paste_from_clipboard,
            width=62, height=34, fg_color=THEME_COLORS["btn_secondary"],
            hover_color=THEME_COLORS["btn_secondary_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text_primary"], font=self.get_ui_font(12), corner_radius=8
        )
        self.btn_paste.pack(side="left", padx=2)

        self.btn_sample = ctk.CTkButton(
            self.file_btn_row, text="Sample", command=self.load_sample_image,
            width=62, height=34, fg_color=THEME_COLORS["btn_secondary"],
            hover_color=THEME_COLORS["btn_secondary_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text_primary"], font=self.get_ui_font(12), corner_radius=8
        )
        self.btn_sample.pack(side="left", padx=2)

        self.btn_clear = ctk.CTkButton(
            self.file_btn_row, text="Clear", command=self.clear_image,
            width=50, height=34, fg_color=THEME_COLORS["btn_secondary"],
            hover_color="#fee2e2", border_width=1, border_color=THEME_COLORS["border"],
            text_color="#ef4444", font=self.get_ui_font(12), corner_radius=8
        )
        self.btn_clear.pack(side="left", padx=(2, 0))

        self.img_info_lbl = ctk.CTkLabel(
            self.file_card, text="No image loaded. Drop image or paste from clipboard.",
            font=self.get_ui_font(11), text_color=THEME_COLORS["text_muted"], justify="left"
        )
        self.img_info_lbl.pack(fill="x", padx=12, pady=(0, 10))

        self.scale_card = ctk.CTkFrame(
            self.sidebar, fg_color=THEME_COLORS["bg_card"], corner_radius=12,
            border_width=1, border_color=THEME_COLORS["border"]
        )
        self.scale_card.pack(fill="x", padx=16, pady=6)

        self.scale_sec_lbl = ctk.CTkLabel(
            self.scale_card, text="Scale Multiplier", font=self.get_ui_font(13, "bold"),
            text_color=THEME_COLORS["text_primary"], anchor="w"
        )
        self.scale_sec_lbl.pack(fill="x", padx=12, pady=(10, 4))

        self.mult_grid = ctk.CTkFrame(self.scale_card, fg_color="transparent")
        self.mult_grid.pack(fill="x", padx=12, pady=2)
        self.preset_btn_map = {}

        mult_values = [2, 4, 8, 16, 40]
        for idx, m in enumerate(mult_values):
            btn = ctk.CTkButton(
                self.mult_grid, text=f"{m}×", width=62, height=32,
                fg_color=THEME_COLORS["accent"] if m == 2 else THEME_COLORS["btn_secondary"],
                hover_color=THEME_COLORS["accent"],
                border_width=1, border_color=THEME_COLORS["border"],
                text_color=("#ffffff", "#ffffff") if m == 2 else THEME_COLORS["text_primary"],
                font=self.get_ui_font(12, "bold"), corner_radius=8,
                command=lambda val=m: self.select_preset(val)
            )
            btn.grid(row=0, column=idx, padx=2, pady=2, sticky="ew")
            self.preset_btn_map[f"mult_{m}"] = btn

        self.custom_row = ctk.CTkFrame(self.scale_card, fg_color="transparent")
        self.custom_row.pack(fill="x", padx=12, pady=(6, 8))

        self.custom_scale_lbl = ctk.CTkLabel(
            self.custom_row, text="Custom:", font=self.get_ui_font(12, "bold"),
            text_color=THEME_COLORS["text_secondary"]
        )
        self.custom_scale_lbl.pack(side="left", padx=(0, 6))

        self.custom_entry = ctk.CTkEntry(
            self.custom_row, placeholder_text="e.g. 3.5, 6, 25",
            height=32, fg_color=THEME_COLORS["btn_secondary"],
            border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text_primary"],
            font=self.get_ui_font(12), corner_radius=8
        )
        self.custom_entry.insert(0, "2")
        self.custom_entry.pack(side="left", fill="x", expand=True)
        self.custom_entry.bind("<KeyRelease>", lambda e: self.on_custom_scale_changed())

        self.stats_frame = ctk.CTkFrame(
            self.scale_card, fg_color=THEME_COLORS["bg_metric"], corner_radius=8,
            border_width=1, border_color=THEME_COLORS["border"]
        )
        self.stats_frame.pack(fill="x", padx=12, pady=(0, 10))

        self.target_dim_lbl = ctk.CTkLabel(
            self.stats_frame, text="Target Output: —", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=THEME_COLORS["accent"], anchor="w"
        )
        self.target_dim_lbl.pack(fill="x", padx=10, pady=(6, 2))

        self.est_ram_lbl = ctk.CTkLabel(
            self.stats_frame, text="Estimated RAM: —", font=self.get_ui_font(11),
            text_color=THEME_COLORS["text_secondary"], anchor="w"
        )
        self.est_ram_lbl.pack(fill="x", padx=10, pady=(0, 6))

        self.pro_card = ctk.CTkFrame(
            self.sidebar, fg_color=THEME_COLORS["bg_card"], corner_radius=12,
            border_width=1, border_color=THEME_COLORS["border"]
        )
        self.pro_card.pack(fill="x", padx=16, pady=4)

        self.pro_header_row = ctk.CTkFrame(self.pro_card, fg_color="transparent")
        self.pro_header_row.pack(fill="x", padx=12, pady=(10, 4))

        self.pro_sec_lbl = ctk.CTkLabel(
            self.pro_header_row, text="Enhancement Tools", font=self.get_ui_font(13, "bold"),
            text_color=THEME_COLORS["text_primary"], anchor="w"
        )
        self.pro_sec_lbl.pack(side="left")

        self.btn_reset_fx = ctk.CTkButton(
            self.pro_header_row, text="↺ Reset", width=60, height=24,
            fg_color=THEME_COLORS["btn_secondary"],
            hover_color=THEME_COLORS["btn_secondary_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text_secondary"], font=self.get_ui_font(10), corner_radius=6,
            command=self.reset_effects
        )
        self.btn_reset_fx.pack(side="right")

        self.switch_deblur = ctk.CTkSwitch(
            self.pro_card, text="Clarity & Focus Deblur", font=self.get_ui_font(12),
            text_color=THEME_COLORS["text_primary"], command=self.on_tool_toggled
        )
        self.switch_deblur.select()
        self.switch_deblur.pack(fill="x", padx=12, pady=4)

        self.switch_denoise = ctk.CTkSwitch(
            self.pro_card, text="Deep Denoise & JPEG Cleaner", font=self.get_ui_font(12),
            text_color=THEME_COLORS["text_primary"], command=self.on_tool_toggled
        )
        self.switch_denoise.select()
        self.switch_denoise.pack(fill="x", padx=12, pady=4)

        self.switch_hdr = ctk.CTkSwitch(
            self.pro_card, text="Natural HDR & Color Balance", font=self.get_ui_font(12),
            text_color=THEME_COLORS["text_primary"], command=self.on_tool_toggled
        )
        self.switch_hdr.select()
        self.switch_hdr.pack(fill="x", padx=12, pady=4)

        self.switch_bg = ctk.CTkSwitch(
            self.pro_card, text="Deep Learning Background Cutout", font=self.get_ui_font(12),
            text_color=THEME_COLORS["text_primary"], command=self.on_tool_toggled
        )
        self.switch_bg.pack(fill="x", padx=12, pady=(4, 10))

        self.config_card = ctk.CTkFrame(
            self.sidebar, fg_color=THEME_COLORS["bg_card"], corner_radius=12,
            border_width=1, border_color=THEME_COLORS["border"]
        )
        self.config_card.pack(fill="x", padx=16, pady=4)

        self.algo_lbl = ctk.CTkLabel(
            self.config_card, text="Deep Learning Engine", font=self.get_ui_font(12, "bold"),
            text_color=THEME_COLORS["text_primary"], anchor="w"
        )
        self.algo_lbl.pack(fill="x", padx=12, pady=(8, 4))

        self.algo_menu = ctk.CTkOptionMenu(
            self.config_card,
            values=[
                "FSRCNN (Deep Learning Neural CNN)",
                "ESPCN (Sub-Pixel Convolutional Network)",
                "LapSRN (Deep Laplacian Pyramid Network)",
                "Super-Res (High-Frequency Synthesis)",
                "Lanczos-4 Sinc (Photo & Ultra Detail)",
                "Document & Text Vectorizer",
                "Pixel Art / Retro (Nearest 0% Blur)"
            ],
            command=lambda v: self.on_tool_toggled(),
            height=34,
            fg_color=THEME_COLORS["opt_bg"],
            button_color=THEME_COLORS["opt_btn"],
            button_hover_color=THEME_COLORS["opt_btn_hover"],
            dropdown_fg_color=THEME_COLORS["opt_bg"],
            dropdown_text_color=THEME_COLORS["text_primary"],
            dropdown_hover_color=THEME_COLORS["opt_btn"],
            text_color=THEME_COLORS["text_primary"],
            font=self.get_ui_font(12), corner_radius=8,
            dropdown_font=self.get_ui_font(12)
        )
        self.algo_menu.pack(fill="x", padx=12, pady=(0, 6))

        self.fmt_row = ctk.CTkFrame(self.config_card, fg_color="transparent")
        self.fmt_row.pack(fill="x", padx=12, pady=(2, 8))

        self.fmt_label = ctk.CTkLabel(
            self.fmt_row, text="Format:", font=self.get_ui_font(12, "bold"),
            text_color=THEME_COLORS["text_secondary"]
        )
        self.fmt_label.pack(side="left", padx=(0, 6))

        self.fmt_menu = ctk.CTkOptionMenu(
            self.fmt_row, values=["PNG", "JPG", "WEBP", "TIFF"],
            height=34,
            fg_color=THEME_COLORS["opt_bg"],
            button_color=THEME_COLORS["opt_btn"],
            button_hover_color=THEME_COLORS["opt_btn_hover"],
            dropdown_fg_color=THEME_COLORS["opt_bg"],
            dropdown_text_color=THEME_COLORS["text_primary"],
            dropdown_hover_color=THEME_COLORS["opt_btn"],
            text_color=THEME_COLORS["text_primary"],
            font=self.get_ui_font(12), corner_radius=8,
            dropdown_font=self.get_ui_font(12)
        )
        self.fmt_menu.pack(side="left", fill="x", expand=True)

        self.btn_upscale = ctk.CTkButton(
            self.sidebar, text="⚡ Upscale Image (2×)",
            height=46, fg_color=THEME_COLORS["accent"], hover_color=THEME_COLORS["accent_hover"],
            text_color="#ffffff", font=self.get_ui_font(14, "bold"), corner_radius=10,
            command=self.start_upscaling
        )
        self.btn_upscale.pack(fill="x", padx=16, pady=(12, 4))

        self.btn_preview = ctk.CTkButton(
            self.sidebar, text="Update Live Preview",
            height=34, fg_color=THEME_COLORS["btn_secondary"],
            hover_color=THEME_COLORS["btn_secondary_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text_primary"],
            font=self.get_ui_font(12, "bold"), corner_radius=8,
            command=self.trigger_live_preview
        )
        self.btn_preview.pack(fill="x", padx=16, pady=4)

        self.progress_bar = ctk.CTkProgressBar(self.sidebar, height=8, progress_color=THEME_COLORS["accent"])
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=16, pady=(8, 4))

        self.status_lbl = ctk.CTkLabel(
            self.sidebar, text="Ready", font=self.get_ui_font(11),
            text_color=THEME_COLORS["text_muted"], anchor="w"
        )
        self.status_lbl.pack(fill="x", padx=16, pady=(0, 16))

        self.main_panel = ctk.CTkFrame(self, fg_color=THEME_COLORS["bg_root"])
        self.main_panel.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        self.main_panel.grid_columnconfigure(0, weight=1)
        self.main_panel.grid_rowconfigure(0, weight=1)

        self.tab_view = ctk.CTkTabview(
            self.main_panel, fg_color=THEME_COLORS["bg_sidebar"],
            segmented_button_selected_color=THEME_COLORS["accent"],
            segmented_button_fg_color=THEME_COLORS["bg_card"],
            segmented_button_unselected_color=THEME_COLORS["bg_card"]
        )
        self.tab_view.grid(row=0, column=0, sticky="nsew")

        self.tab_single_frame = self.tab_view.add(self.t("tab_single"))
        self.tab_batch_frame = self.tab_view.add(self.t("tab_batch"))

        self.setup_single_viewport()
        self.setup_batch_viewport()
        self.setup_loading_overlay()

    def setup_loading_overlay(self):
        self.loading_overlay = ctk.CTkFrame(
            self.canvas_frame, fg_color=THEME_COLORS["bg_card"], corner_radius=18,
            border_width=2, border_color=THEME_COLORS["border"], width=420, height=220
        )

        logo_img_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.isfile(logo_img_path):
            try:
                pil_logo = Image.open(logo_img_path).resize((48, 48), Image.Resampling.LANCZOS)
                self.modal_logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(48, 48))
                self.modal_logo_lbl = ctk.CTkLabel(self.loading_overlay, image=self.modal_logo_img, text="")
                self.modal_logo_lbl.pack(pady=(20, 6))
            except Exception:
                pass

        self.loading_title_lbl = ctk.CTkLabel(
            self.loading_overlay, text=self.t("loading_title"),
            font=self.get_ui_font(16, "bold"),
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
            self.loading_overlay, width=320, height=10,
            progress_color=THEME_COLORS["accent"], fg_color=THEME_COLORS["bg_card_sub"]
        )
        self.loading_pbar.set(0.2)
        self.loading_pbar.pack(pady=4)

        self.loading_time_lbl = ctk.CTkLabel(
            self.loading_overlay, text="⏱ 0.0s elapsed",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=THEME_COLORS["accent"]
        )
        self.loading_time_lbl.pack(pady=(4, 16))

    def show_loading_screen(self, title: str = None, subtitle: str = None):
        if title:
            self.loading_title_lbl.configure(text=title)
        else:
            self.loading_title_lbl.configure(text=self.t("loading_title"))

        if subtitle:
            self.loading_sub_lbl.configure(text=subtitle)
        else:
            self.loading_sub_lbl.configure(text=self.t("loading_subtitle"))

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
            self.loading_time_lbl.configure(text=f"⏱ {elapsed:.1f}s elapsed")
            self.loading_timer_id = self.after(100, self._update_loading_timer)

    def setup_single_viewport(self):
        self.tab_single_frame.grid_columnconfigure(0, weight=1)
        self.tab_single_frame.grid_rowconfigure(1, weight=1)

        self.single_top_bar = ctk.CTkFrame(self.tab_single_frame, fg_color="transparent", height=42)
        self.single_top_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 8))

        self.slider_hint_lbl = ctk.CTkLabel(
            self.single_top_bar, text="Drag divider or hold Spacebar to compare",
            font=self.get_ui_font(12), text_color=THEME_COLORS["text_secondary"]
        )
        self.slider_hint_lbl.pack(side="left", padx=8)

        self.zoom_tools = ctk.CTkFrame(self.single_top_bar, fg_color="transparent")
        self.zoom_tools.pack(side="right", padx=4)

        self.btn_zoom_in = ctk.CTkButton(
            self.zoom_tools, text="+", width=32, height=32,
            fg_color=THEME_COLORS["btn_secondary"],
            hover_color=THEME_COLORS["btn_secondary_hover"],
            text_color=THEME_COLORS["text_primary"],
            border_width=1, border_color=THEME_COLORS["border"],
            font=self.get_ui_font(14, "bold"), corner_radius=6,
            command=lambda: self.change_zoom(1.3)
        )
        self.btn_zoom_in.pack(side="left", padx=2)

        self.btn_zoom_out = ctk.CTkButton(
            self.zoom_tools, text="–", width=32, height=32,
            fg_color=THEME_COLORS["btn_secondary"],
            hover_color=THEME_COLORS["btn_secondary_hover"],
            text_color=THEME_COLORS["text_primary"],
            border_width=1, border_color=THEME_COLORS["border"],
            font=self.get_ui_font(14, "bold"), corner_radius=6,
            command=lambda: self.change_zoom(0.75)
        )
        self.btn_zoom_out.pack(side="left", padx=2)

        self.btn_reset_zoom = ctk.CTkButton(
            self.zoom_tools, text="Fit View", width=70, height=32,
            fg_color=THEME_COLORS["btn_secondary"],
            hover_color=THEME_COLORS["btn_secondary_hover"],
            text_color=THEME_COLORS["text_primary"],
            border_width=1, border_color=THEME_COLORS["border"],
            font=self.get_ui_font(11), corner_radius=6,
            command=self.reset_viewport
        )
        self.btn_reset_zoom.pack(side="left", padx=2)

        self.btn_actual_size = ctk.CTkButton(
            self.zoom_tools, text="1:1 (100%)", width=80, height=32,
            fg_color=THEME_COLORS["btn_secondary"],
            hover_color=THEME_COLORS["btn_secondary_hover"],
            text_color=THEME_COLORS["text_primary"],
            border_width=1, border_color=THEME_COLORS["border"],
            font=self.get_ui_font(11, "bold"), corner_radius=6,
            command=self.set_actual_pixels_view
        )
        self.btn_actual_size.pack(side="left", padx=2)

        self.btn_zoom_200 = ctk.CTkButton(
            self.zoom_tools, text="200%", width=55, height=32,
            fg_color=THEME_COLORS["btn_secondary"],
            hover_color=THEME_COLORS["btn_secondary_hover"],
            text_color=THEME_COLORS["text_primary"],
            border_width=1, border_color=THEME_COLORS["border"],
            font=self.get_ui_font(11), corner_radius=6,
            command=lambda: self.set_preset_zoom(2.0)
        )
        self.btn_zoom_200.pack(side="left", padx=2)

        self.btn_copy = ctk.CTkButton(
            self.zoom_tools, text="Copy", width=65, height=32,
            fg_color=THEME_COLORS["btn_secondary"],
            border_width=1, border_color=THEME_COLORS["border"],
            hover_color=THEME_COLORS["btn_secondary_hover"],
            text_color=THEME_COLORS["text_primary"],
            font=self.get_ui_font(11, "bold"), corner_radius=6,
            command=self.copy_to_clipboard, state="disabled"
        )
        self.btn_copy.pack(side="left", padx=2)

        self.btn_save = ctk.CTkButton(
            self.zoom_tools, text="Save Image", height=32,
            fg_color=THEME_COLORS["accent_success"],
            hover_color="#059669", text_color="#ffffff",
            font=self.get_ui_font(12, "bold"), corner_radius=6,
            command=self.save_image, state="disabled"
        )
        self.btn_save.pack(side="left", padx=(4, 0))

        self.canvas_frame = ctk.CTkFrame(
            self.tab_single_frame, fg_color=THEME_COLORS["bg_card"], corner_radius=12,
            border_width=1, border_color=THEME_COLORS["border"]
        )
        self.canvas_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
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
            fg_color="transparent", button_color="#94a3b8", button_hover_color="#64748b"
        )
        self.v_scrollbar.grid(row=0, column=1, sticky="ns", padx=(2, 4), pady=4)

        self.h_scrollbar = ctk.CTkScrollbar(
            self.canvas_frame, orientation="horizontal", command=self.on_h_scroll,
            fg_color="transparent", button_color="#94a3b8", button_hover_color="#64748b"
        )
        self.h_scrollbar.grid(row=1, column=0, sticky="ew", padx=4, pady=(2, 4))

        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<MouseWheel>", self.on_canvas_wheel)
        self.canvas.bind("<Shift-MouseWheel>", self.on_canvas_shift_wheel)
        self.canvas.bind("<Button-3>", self.on_right_click_pan_start)
        self.canvas.bind("<B3-Motion>", self.on_right_click_pan_move)
        self.canvas.bind("<Configure>", lambda e: self.update_display_cache())

    def on_v_scroll(self, action, value, *args):
        c_h = self.canvas.winfo_height()
        disp_h = self.cached_disp_h
        if disp_h <= c_h:
            return

        max_pan = (disp_h - c_h) // 2
        val = float(value)
        self.pan_y = int((0.5 - val) * (disp_h - c_h))
        self.pan_y = max(-max_pan, min(max_pan, self.pan_y))
        self.redraw_comparison()

    def on_h_scroll(self, action, value, *args):
        c_w = self.canvas.winfo_width()
        disp_w = self.cached_disp_w
        if disp_w <= c_w:
            return

        max_pan = (disp_w - c_w) // 2
        val = float(value)
        self.pan_x = int((0.5 - val) * (disp_w - c_w))
        self.pan_x = max(-max_pan, min(max_pan, self.pan_x))
        self.redraw_comparison()

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
            self.redraw_comparison()

    def setup_batch_viewport(self):
        self.tab_batch_frame.grid_columnconfigure(0, weight=1)
        self.tab_batch_frame.grid_rowconfigure(1, weight=1)

        self.batch_top_bar = ctk.CTkFrame(self.tab_batch_frame, fg_color="transparent")
        self.batch_top_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 8))

        self.btn_batch_add_files = ctk.CTkButton(
            self.batch_top_bar, text="Add Images", height=34,
            fg_color=THEME_COLORS["accent"],
            text_color="#ffffff", font=self.get_ui_font(12, "bold"), corner_radius=8,
            command=self.batch_browse_files
        )
        self.btn_batch_add_files.pack(side="left", padx=(0, 6))

        self.btn_batch_add_folder = ctk.CTkButton(
            self.batch_top_bar, text="Add Folder", height=34,
            fg_color=THEME_COLORS["btn_secondary"],
            hover_color=THEME_COLORS["btn_secondary_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text_primary"], font=self.get_ui_font(12), corner_radius=8,
            command=self.batch_browse_folder
        )
        self.btn_batch_add_folder.pack(side="left", padx=4)

        self.btn_batch_clear = ctk.CTkButton(
            self.batch_top_bar, text="Clear Queue", height=34,
            fg_color=THEME_COLORS["btn_secondary"],
            hover_color="#fee2e2", border_width=1, border_color=THEME_COLORS["border"],
            text_color="#ef4444", font=self.get_ui_font(12), corner_radius=8,
            command=self.batch_clear_queue
        )
        self.btn_batch_clear.pack(side="left", padx=4)

        self.btn_batch_run = ctk.CTkButton(
            self.batch_top_bar, text="Start Batch Upscaling", height=34,
            fg_color=THEME_COLORS["accent_success"], hover_color="#059669",
            text_color="#ffffff", font=self.get_ui_font(12, "bold"), corner_radius=8,
            command=self.start_batch_upscale
        )
        self.btn_batch_run.pack(side="right", padx=(6, 0))

        self.batch_listbox_frame = ctk.CTkScrollableFrame(
            self.tab_batch_frame, fg_color=THEME_COLORS["bg_card"], corner_radius=10,
            border_width=1, border_color=THEME_COLORS["border"]
        )
        self.batch_listbox_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)

        self.batch_empty_lbl = ctk.CTkLabel(
            self.batch_listbox_frame,
            text="No images in batch queue.\nDrag & drop multiple files or a whole folder here!",
            font=self.get_ui_font(13), text_color=THEME_COLORS["text_muted"]
        )
        self.batch_empty_lbl.pack(pady=60)

        self.batch_bottom_bar = ctk.CTkFrame(self.tab_batch_frame, fg_color="transparent")
        self.batch_bottom_bar.grid(row=2, column=0, sticky="ew", padx=8, pady=(6, 4))

        self.batch_out_lbl = ctk.CTkLabel(
            self.batch_bottom_bar, text=f"Output: {self.batch_output_dir}",
            font=self.get_ui_font(11), text_color=THEME_COLORS["text_secondary"], anchor="w"
        )
        self.batch_out_lbl.pack(side="left", fill="x", expand=True, padx=4)

        self.btn_batch_change_dir = ctk.CTkButton(
            self.batch_bottom_bar, text="Change Folder", width=110, height=28,
            fg_color=THEME_COLORS["btn_secondary"],
            hover_color=THEME_COLORS["btn_secondary_hover"],
            border_width=1, border_color=THEME_COLORS["border"],
            text_color=THEME_COLORS["text_primary"], font=self.get_ui_font(11), corner_radius=6,
            command=self.batch_change_output_dir
        )
        self.btn_batch_change_dir.pack(side="right")

    def on_tool_toggled(self):
        if self.current_img_bytes:
            self.trigger_live_preview()

    def on_lang_changed(self, selected_lang_str: str):
        code_map = {
            "English (en)": "en", "فارسی (fa)": "fa", "العربية (ar)": "ar", "Español (es)": "es",
            "Français (fr)": "fr", "Deutsch (de)": "de", "日本語 (ja)": "ja", "中文 (zh)": "zh",
            "Русский (ru)": "ru", "Português (pt)": "pt"
        }
        self.current_lang = code_map.get(selected_lang_str, "en")
        self.update_translations()

    def update_translations(self):
        self.app_title_lbl.configure(text=self.t("title"), font=self.get_ui_font(20, "bold"))
        self.app_sub_lbl.configure(text=self.t("subtitle"), font=self.get_ui_font(11))
        self.drop_hint_lbl.configure(text=self.t("drop_hint"), font=self.get_ui_font(11, "bold"))
        self.btn_browse.configure(text=self.t("btn_browse"), font=self.get_ui_font(12, "bold"))
        self.btn_paste.configure(text=self.t("btn_paste"), font=self.get_ui_font(12))
        self.btn_sample.configure(text=self.t("btn_sample"), font=self.get_ui_font(12))
        self.btn_clear.configure(text=self.t("btn_clear"), font=self.get_ui_font(12))
        self.scale_sec_lbl.configure(text=self.t("sec_scale"), font=self.get_ui_font(13, "bold"))
        self.custom_scale_lbl.configure(text=self.t("custom_scale") + ":", font=self.get_ui_font(12, "bold"))
        self.pro_sec_lbl.configure(text=self.t("pro_features"), font=self.get_ui_font(13, "bold"))
        self.btn_reset_fx.configure(text=f"↺ {self.t('btn_reset_effects')}", font=self.get_ui_font(10))
        self.switch_deblur.configure(text=self.t("feat_deblur"), font=self.get_ui_font(12))
        self.switch_denoise.configure(text=self.t("feat_denoise"), font=self.get_ui_font(12))
        self.switch_hdr.configure(text=self.t("feat_hdr"), font=self.get_ui_font(12))
        self.switch_bg.configure(text=self.t("feat_bg"), font=self.get_ui_font(12))
        self.algo_lbl.configure(text=self.t("algo_label"), font=self.get_ui_font(12, "bold"))
        self.fmt_label.configure(text=self.t("fmt_label"), font=self.get_ui_font(12, "bold"))
        self.btn_preview.configure(text=self.t("btn_preview"), font=self.get_ui_font(12, "bold"))
        self.btn_save.configure(text=self.t("btn_save"), font=self.get_ui_font(12, "bold"))
        self.btn_copy.configure(text=self.t("btn_copy"), font=self.get_ui_font(11, "bold"))
        self.btn_reset_zoom.configure(text=self.t("reset_zoom"), font=self.get_ui_font(11))
        self.btn_actual_size.configure(text=self.t("actual_size"), font=self.get_ui_font(11, "bold"))
        self.slider_hint_lbl.configure(text=self.t("slider_instr"), font=self.get_ui_font(12))
        self.status_lbl.configure(text=self.t("status_ready"), font=self.get_ui_font(11))
        self.btn_batch_add_files.configure(text=self.t("batch_add_files"), font=self.get_ui_font(12, "bold"))
        self.btn_batch_add_folder.configure(text=self.t("batch_add_folder"), font=self.get_ui_font(12))
        self.btn_batch_clear.configure(text=self.t("batch_clear"), font=self.get_ui_font(12))
        self.btn_batch_run.configure(text=self.t("batch_start"), font=self.get_ui_font(12, "bold"))
        self.loading_title_lbl.configure(text=self.t("loading_title"), font=self.get_ui_font(16, "bold"))
        self.loading_sub_lbl.configure(text=self.t("loading_subtitle"), font=self.get_ui_font(12))

        self.lang_menu.configure(font=self.get_ui_font(12), dropdown_font=self.get_ui_font(12))
        self.algo_menu.configure(font=self.get_ui_font(12), dropdown_font=self.get_ui_font(12))
        self.fmt_menu.configure(font=self.get_ui_font(12), dropdown_font=self.get_ui_font(12))

        self.update_stats()
        self.redraw_comparison()

    def select_preset(self, val: float):
        self.scale_val = val
        self.custom_entry.delete(0, "end")
        self.custom_entry.insert(0, str(val))

        for key, btn in self.preset_btn_map.items():
            btn.configure(fg_color=THEME_COLORS["btn_secondary"], text_color=THEME_COLORS["text_primary"])

        target_key = f"mult_{int(val)}"
        if target_key in self.preset_btn_map:
            self.preset_btn_map[target_key].configure(fg_color=THEME_COLORS["accent"], text_color="#ffffff")

        self.update_stats()

    def on_custom_scale_changed(self):
        val_str = self.custom_entry.get().strip()
        try:
            val = float(val_str)
            if val > 40:
                val = 40.0
            self.scale_val = max(0.1, val)
        except ValueError:
            self.scale_val = 1.0

        for btn in self.preset_btn_map.values():
            btn.configure(fg_color=THEME_COLORS["btn_secondary"], text_color=THEME_COLORS["text_primary"])

        self.update_stats()

    def update_stats(self):
        scale_label = f"{self.scale_val:.0f}×" if self.scale_val.is_integer() else f"{self.scale_val}×"
        self.btn_upscale.configure(text=f"⚡ {self.t('btn_upscale')} ({scale_label})")

        if not self.orig_w or not self.orig_h:
            self.target_dim_lbl.configure(text=f"{self.t('target_dim')} —")
            self.est_ram_lbl.configure(text=f"{self.t('est_ram')} —")
            return

        out_w, out_h, eff_factor = UpscalerEngine.calculate_target_size(
            self.orig_w, self.orig_h, self.scale_type, self.scale_val
        )
        orig_mp = (self.orig_w * self.orig_h) / 1_000_000.0
        target_mp = (out_w * out_h) / 1_000_000.0
        ram_mb = (out_w * out_h * 4) / (1024 * 1024)

        self.target_dim_lbl.configure(
            text=f"{self.t('target_dim')} {out_w:,} × {out_h:,} px ({target_mp:.2f} MP, {eff_factor:.2f}×)"
        )
        self.est_ram_lbl.configure(
            text=f"{self.t('est_ram')} ~{ram_mb:.1f} MB  •  {orig_mp:.1f} MP ➔ {target_mp:.1f} MP"
        )

    def browse_file(self):
        path = filedialog.askopenfilename(
            title="Select Image to Upscale",
            filetypes=[
                ("Image Files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tiff;*.tif"),
                ("All Files", "*.*")
            ]
        )
        if path:
            self.load_image_from_path(path)

    def paste_from_clipboard(self):
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                self.active_filename = "clipboard_image.png"
                self.load_image_bytes(buf.getvalue(), self.active_filename)
                self.status_lbl.configure(text="Pasted image from clipboard.")
            elif isinstance(img, list) and len(img) > 0 and os.path.isfile(img[0]):
                self.load_image_from_path(img[0])
            else:
                messagebox.showinfo("Clipboard", "No image found on clipboard. Copy an image or screenshot first.")
        except Exception as e:
            messagebox.showerror("Clipboard Error", f"Could not paste from clipboard: {e}")

    def copy_to_clipboard(self):
        target_img = self.upscaled_pil_img or self.current_pil_img
        if not target_img:
            return

        if WIN32_CLIPBOARD_AVAILABLE:
            try:
                output = io.BytesIO()
                target_img.convert("RGB").save(output, "BMP")
                data = output.getvalue()[14:]
                output.close()
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                win32clipboard.CloseClipboard()
                self.status_lbl.configure(text=f"✓ {self.t('copied_clipboard')}")
                messagebox.showinfo("Copied", self.t("copied_clipboard"))
                return
            except Exception:
                pass

        messagebox.showinfo("Copied", "Image available in session memory.")

    def load_image_from_path(self, path: str):
        try:
            with open(path, "rb") as f:
                img_bytes = f.read()
            self.active_filename = os.path.basename(path)
            self.load_image_bytes(img_bytes, self.active_filename)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load image: {e}")

    def load_sample_image(self):
        img = Image.new("RGB", (320, 220), color=(248, 250, 252))
        draw = ImageDraw.Draw(img)

        for r in range(90, 10, -16):
            color = (37, 99, 235) if r % 32 == 0 else (16, 185, 129)
            draw.ellipse([160 - r, 110 - r, 160 + r, 110 + r], outline=color, width=2)

        draw.text((115, 95), "aupscaler", fill=(15, 23, 42))
        draw.text((105, 115), "Deep Learning CNN", fill=(71, 85, 105))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        self.active_filename = "sample_test.png"
        self.load_image_bytes(buf.getvalue(), self.active_filename)

    def load_image_bytes(self, img_bytes: bytes, filename: str):
        self.current_img_bytes = img_bytes
        self.current_pil_img = Image.open(io.BytesIO(img_bytes))
        self.current_pil_img = ImageOps.exif_transpose(self.current_pil_img)
        self.orig_w, self.orig_h = self.current_pil_img.size

        mp = (self.orig_w * self.orig_h) / 1_000_000.0
        self.img_info_lbl.configure(
            text=f"📁 {filename}\n📐 {self.orig_w} × {self.orig_h} px  •  {mp:.2f} MP"
        )
        self.update_stats()
        self.reset_viewport()
        self.trigger_live_preview()

    def clear_image(self):
        self.current_img_bytes = None
        self.current_pil_img = None
        self.upscaled_pil_img = None
        self.cached_before_thumb = None
        self.cached_after_thumb = None
        self.orig_w = 0
        self.orig_h = 0
        self.img_info_lbl.configure(text="No image loaded. Drop image or paste from clipboard.")
        self.canvas.delete("all")
        self.btn_save.configure(state="disabled")
        self.btn_copy.configure(state="disabled")
        self.update_stats()

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

    def set_preset_zoom(self, zoom_val: float):
        if not self.current_pil_img:
            return
        c_w = self.canvas.winfo_width()
        c_h = self.canvas.winfo_height()
        if c_w <= 10 or c_h <= 10:
            return
        img_w, img_h = self.current_pil_img.size
        base_scale = min((c_w - 40) / img_w, (c_h - 40) / img_h)
        if base_scale > 0:
            self.zoom_level = zoom_val / base_scale
        self.pan_x = 0
        self.pan_y = 0
        self.cached_disp_w = 0
        self.update_display_cache()

    def _render_checkerboard(self, width: int, height: int, check_size: int = 16) -> Image.Image:
        if self.current_theme == "dark":
            c1 = (24, 32, 47, 255)
            c2 = (11, 15, 25, 255)
        else:
            c1 = (255, 255, 255, 255)
            c2 = (226, 232, 240, 255)

        bg = Image.new("RGBA", (width, height), c1)
        draw = ImageDraw.Draw(bg)
        for y in range(0, height, check_size):
            for x in range(0, width, check_size):
                if ((x // check_size) + (y // check_size)) % 2 == 0:
                    draw.rectangle([x, y, x + check_size, y + check_size], fill=c2)
        return bg

    def update_display_cache(self):
        if not self.current_pil_img:
            self.redraw_comparison()
            return

        c_w = self.canvas.winfo_width()
        c_h = self.canvas.winfo_height()
        if c_w <= 10 or c_h <= 10:
            return

        img_w, img_h = self.current_pil_img.size
        base_scale = min((c_w - 40) / img_w, (c_h - 40) / img_h)
        eff_scale = base_scale * self.zoom_level

        disp_w = max(1, int(round(img_w * eff_scale)))
        disp_h = max(1, int(round(img_h * eff_scale)))

        if disp_w <= c_w:
            self.pan_x = 0
        if disp_h <= c_h:
            self.pan_y = 0

        if disp_w != self.cached_disp_w or disp_h != self.cached_disp_h:
            self.cached_disp_w = disp_w
            self.cached_disp_h = disp_h

            if disp_w > img_w * 1.5:
                raw_before = self.current_pil_img.resize((disp_w, disp_h), Image.Resampling.NEAREST)
            else:
                raw_before = self.current_pil_img.resize((disp_w, disp_h), Image.Resampling.BILINEAR)

            after_source = self.upscaled_pil_img or self.current_pil_img
            raw_after = after_source.resize((disp_w, disp_h), Image.Resampling.LANCZOS)

            checker = self._render_checkerboard(disp_w, disp_h)

            if raw_before.mode == "RGBA":
                self.cached_before_thumb = Image.alpha_composite(checker, raw_before.convert("RGBA"))
            else:
                self.cached_before_thumb = raw_before.convert("RGBA")

            if raw_after.mode == "RGBA":
                self.cached_after_thumb = Image.alpha_composite(checker, raw_after.convert("RGBA"))
            else:
                self.cached_after_thumb = raw_after.convert("RGBA")

        self.update_scrollbars()
        self.redraw_comparison()

    def on_canvas_click(self, event):
        self.update_split(event.x)

    def on_canvas_drag(self, event):
        self.update_split(event.x)

    def update_split(self, x: int):
        c_w = self.canvas.winfo_width()
        if c_w > 0:
            self.split_ratio = max(0.0, min(1.0, x / float(c_w)))
            self.redraw_comparison()

    def change_zoom(self, factor: float):
        self.zoom_level = max(0.2, min(30.0, self.zoom_level * factor))
        self.cached_disp_w = 0
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
            self.redraw_comparison()
        else:
            factor = 1.15 if event.delta > 0 else 0.85
            self.change_zoom(factor)

    def on_right_click_pan_start(self, event):
        self.pan_start_x = event.x - self.pan_x
        self.pan_start_y = event.y - self.pan_y

    def on_right_click_pan_move(self, event):
        c_w = self.canvas.winfo_width()
        c_h = self.canvas.winfo_height()
        disp_w = self.cached_disp_w
        disp_h = self.cached_disp_h

        max_pan_x = max(0, (disp_w - c_w) // 2)
        max_pan_y = max(0, (disp_h - c_h) // 2)

        self.pan_x = max(-max_pan_x, min(max_pan_x, event.x - self.pan_start_x))
        self.pan_y = max(-max_pan_y, min(max_pan_y, event.y - self.pan_start_y))
        self.update_scrollbars()
        self.redraw_comparison()

    def redraw_comparison(self):
        if not self.current_pil_img or not self.cached_before_thumb or not self.cached_after_thumb:
            self.canvas.delete("all")
            c_w = self.canvas.winfo_width() or 600
            c_h = self.canvas.winfo_height() or 400
            font_family = "A Nafis" if self.current_lang in ("fa", "ar") else "Segoe UI"
            font_sz = 15 if self.current_lang in ("fa", "ar") else 13
            text_color = "#94a3b8" if self.current_theme == "dark" else "#64748b"
            self.canvas.create_text(
                c_w // 2, c_h // 2,
                text="Drop an image here or press Ctrl+V to paste from clipboard",
                fill=text_color, font=(font_family, font_sz)
            )
            return

        c_w = self.canvas.winfo_width()
        c_h = self.canvas.winfo_height()

        disp_w = self.cached_disp_w
        disp_h = self.cached_disp_h
        disp_x = (c_w - disp_w) // 2 + self.pan_x
        disp_y = (c_h - disp_h) // 2 + self.pan_y

        font_family = "A Nafis" if self.current_lang in ("fa", "ar") else "Segoe UI"
        font_sz = 12 if self.current_lang in ("fa", "ar") else 10

        if self.hold_space_active:
            self.tk_canvas_img = ImageTk.PhotoImage(self.cached_before_thumb)
            self.canvas.delete("all")
            self.canvas.create_image(disp_x, disp_y, anchor="nw", image=self.tk_canvas_img)
            self.canvas.create_text(
                c_w // 2, 28, text="[ HOLDING SPACEBAR: SHOWING LOW-RES ORIGINAL ]",
                fill="#d97706", font=(font_family, font_sz + 1, "bold")
            )
            return

        split_canvas_x = int(c_w * self.split_ratio)
        img_split_x = max(0, min(disp_w, split_canvas_x - disp_x))

        composite = Image.new("RGBA", (disp_w, disp_h))
        if img_split_x > 0:
            left_crop = self.cached_after_thumb.crop((0, 0, img_split_x, disp_h))
            composite.paste(left_crop, (0, 0))
        if img_split_x < disp_w:
            right_crop = self.cached_before_thumb.crop((img_split_x, 0, disp_w, disp_h))
            composite.paste(right_crop, (img_split_x, 0))

        self.tk_canvas_img = ImageTk.PhotoImage(composite)
        self.canvas.delete("all")
        self.canvas.create_image(disp_x, disp_y, anchor="nw", image=self.tk_canvas_img)

        divider_color = "#3b82f6" if self.current_theme == "dark" else "#2563eb"
        divider_x = split_canvas_x
        self.canvas.create_line(divider_x, 0, divider_x, c_h, fill=divider_color, width=2)

        knob_y = c_h // 2
        badge_bg = "#1e293b" if self.current_theme == "dark" else "#ffffff"
        badge_border = "#334155" if self.current_theme == "dark" else "#e2e8f0"
        tag_secondary = "#cbd5e1" if self.current_theme == "dark" else "#475569"

        self.canvas.create_rectangle(
            divider_x - 14, knob_y - 14, divider_x + 14, knob_y + 14,
            fill=badge_bg, outline=divider_color, width=2
        )
        self.canvas.create_text(
            divider_x, knob_y, text="◀ ▶", fill=divider_color, font=("Segoe UI", 8, "bold")
        )

        after_text = f"◀ {self.t('after_tag')}"
        before_text = f"{self.t('before_tag')} ▶"

        self.canvas.create_rectangle(
            16, c_h - 38, 185, c_h - 10, fill=badge_bg, outline=badge_border, width=1
        )
        self.canvas.create_text(
            100, c_h - 24, text=after_text,
            fill=divider_color, font=(font_family, font_sz, "bold")
        )

        self.canvas.create_rectangle(
            c_w - 185, c_h - 38, c_w - 16, c_h - 10, fill=badge_bg, outline=badge_border, width=1
        )
        self.canvas.create_text(
            c_w - 100, c_h - 24, text=before_text,
            fill=tag_secondary, font=(font_family, font_sz, "bold")
        )

    def get_selected_algo_code(self) -> str:
        text = self.algo_menu.get().lower()
        if "fsrcnn" in text:
            return "fsrcnn"
        if "espcn" in text:
            return "espcn"
        if "lapsrn" in text:
            return "lapsrn"
        if "lanczos" in text:
            return "lanczos"
        if "document" in text or "text" in text:
            return "document"
        if "pixel" in text or "nearest" in text:
            return "nearest"
        return "super_res"

    def start_upscaling(self):
        if not self.current_img_bytes or self.is_processing:
            if not self.current_img_bytes:
                messagebox.showwarning("No Image", self.t("no_image"))
            return

        self.is_processing = True
        self.btn_upscale.configure(state="disabled")
        self.progress_bar.set(0.05)
        self.status_lbl.configure(text=self.t("status_processing"))

        out_w, out_h, factor = UpscalerEngine.calculate_target_size(
            self.orig_w, self.orig_h, self.scale_type, self.scale_val
        )
        self.show_loading_screen(
            title=f"{self.t('loading_title')} ({factor:.1f}×)",
            subtitle=f"Deep Learning Neural Inference ({out_w:,} × {out_h:,} px)..."
        )

        selected_algo = self.get_selected_algo_code()
        fmt_choice = self.fmt_menu.get().upper()

        def _on_progress_update(pct: float, step_name: str):
            self.after(0, lambda p=pct, s=step_name: (
                self.progress_bar.set(p),
                self.loading_pbar.set(p),
                self.loading_sub_lbl.configure(text=s),
                self.status_lbl.configure(text=s)
            ))

        worker = threading.Thread(
            target=self._run_upscaling_job,
            args=(
                self.current_img_bytes,
                self.scale_type,
                self.scale_val,
                selected_algo,
                self.switch_bg.get() == 1,
                self.switch_deblur.get() == 1,
                3 if self.switch_denoise.get() == 1 else 0,
                self.switch_hdr.get() == 1,
                fmt_choice,
                300,
                _on_progress_update
            ),
            daemon=True
        )
        worker.start()

    def _run_upscaling_job(self, img_bytes, s_type, s_val, algo, bg_cut, deblur, denoise, hdr, fmt, dpi, cb):
        start_time = time.time()
        try:
            out_bytes, meta = UpscalerEngine.process_image(
                image_bytes=img_bytes,
                scale_type=s_type,
                scale_val=s_val,
                algorithm=algo,
                remove_bg=bg_cut,
                deblur=deblur,
                denoise_level=denoise,
                auto_hdr=hdr,
                output_format=fmt,
                output_dpi=dpi,
                progress_callback=cb
            )
            elapsed = time.time() - start_time
            meta["elapsed_sec"] = round(elapsed, 2)

            self.upscaled_bytes = out_bytes
            self.upscaled_pil_img = Image.open(io.BytesIO(out_bytes))

            self.after(0, self._on_upscale_success, meta)
        except Exception as e:
            self.after(0, self._on_upscale_error, str(e))

    def _on_upscale_success(self, meta: dict):
        self.is_processing = False
        self.hide_loading_screen()
        self.btn_upscale.configure(state="normal")
        self.btn_save.configure(state="normal")
        self.btn_copy.configure(state="normal")
        self.progress_bar.set(1.0)
        self.status_lbl.configure(
            text=f"✓ {self.t('status_done')} ({meta['target_width']}×{meta['target_height']} px, {meta['file_size_mb']} MB in {meta['elapsed_sec']}s)"
        )
        self.cached_disp_w = 0
        self.update_display_cache()

    def _on_upscale_error(self, err_msg: str):
        self.is_processing = False
        self.hide_loading_screen()
        self.btn_upscale.configure(state="normal")
        self.progress_bar.set(0)
        self.status_lbl.configure(text=f"Error: {err_msg}")
        messagebox.showerror("Upscaling Error", err_msg)

    def trigger_live_preview(self):
        if not self.current_img_bytes or self.is_processing:
            return

        if self.preview_pending:
            return

        self.preview_pending = True
        selected_algo = self.get_selected_algo_code()
        bg_val = self.switch_bg.get() == 1
        deblur_val = self.switch_deblur.get() == 1
        denoise_val = 3 if self.switch_denoise.get() == 1 else 0
        hdr_val = self.switch_hdr.get() == 1

        def _bg_worker():
            try:
                orig_prev, upscaled_prev = UpscalerEngine.generate_roi_preview(
                    image_bytes=self.current_img_bytes,
                    scale_type=self.scale_type,
                    scale_val=self.scale_val,
                    algorithm=selected_algo,
                    remove_bg=bg_val,
                    deblur=deblur_val,
                    denoise_level=denoise_val,
                    auto_hdr=hdr_val
                )
                self.after(0, self._on_preview_ready, upscaled_prev)
            except Exception:
                self.preview_pending = False

        threading.Thread(target=_bg_worker, daemon=True).start()

    def _on_preview_ready(self, upscaled_prev_bytes: bytes):
        self.preview_pending = False
        self.upscaled_pil_img = Image.open(io.BytesIO(upscaled_prev_bytes))
        self.upscaled_bytes = upscaled_prev_bytes
        self.btn_save.configure(state="normal")
        self.btn_copy.configure(state="normal")
        self.cached_disp_w = 0
        self.update_display_cache()
        self.status_lbl.configure(text="Deep Learning Live Preview active.")

    def save_image(self):
        if not self.upscaled_bytes and not self.upscaled_pil_img:
            messagebox.showwarning("No Data", "No processed image to save.")
            return

        fmt = self.fmt_menu.get().lower()
        ext = "jpg" if fmt == "jpeg" else fmt

        base_name = os.path.splitext(self.active_filename)[0]
        out_w, out_h, eff_factor = UpscalerEngine.calculate_target_size(
            self.orig_w, self.orig_h, self.scale_type, self.scale_val
        )
        default_filename = f"{base_name}_aupscaled_{eff_factor:.1f}x_{out_w}x{out_h}.{ext}"

        save_path = filedialog.asksaveasfilename(
            title="Save Upscaled Image",
            defaultextension=f".{ext}",
            filetypes=[
                (f"{fmt.upper()} Image (*.{ext})", f"*.{ext}"),
                ("PNG Image (*.png)", "*.png"),
                ("JPEG Image (*.jpg;*.jpeg)", "*.jpg;*.jpeg"),
                ("WEBP Image (*.webp)", "*.webp"),
                ("TIFF Image (*.tiff)", "*.tiff"),
                ("All Files (*.*)", "*.*")
            ],
            initialfile=default_filename
        )

        if not save_path:
            return

        try:
            target_ext = os.path.splitext(save_path)[1].lower().replace(".", "")
            if target_ext in ["jpg", "jpeg"]:
                save_fmt = "JPEG"
            elif target_ext == "png":
                save_fmt = "PNG"
            elif target_ext == "webp":
                save_fmt = "WEBP"
            elif target_ext in ["tif", "tiff"]:
                save_fmt = "TIFF"
            else:
                save_fmt = "PNG"

            if self.upscaled_pil_img:
                img_to_save = self.upscaled_pil_img
                if save_fmt == "JPEG" and img_to_save.mode in ("RGBA", "LA", "P"):
                    img_to_save = img_to_save.convert("RGB")
                img_to_save.save(save_path, format=save_fmt, quality=98 if save_fmt == "JPEG" else None)
            else:
                with open(save_path, "wb") as f:
                    f.write(self.upscaled_bytes)

            self.status_lbl.configure(text=f"✓ Saved to: {os.path.basename(save_path)}")
            messagebox.showinfo("Saved Successfully", f"Image saved successfully to:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save image: {e}")

    def batch_browse_files(self):
        files = filedialog.askopenfilenames(
            title="Select Images for Batch Upscaling",
            filetypes=[
                ("Image Files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tiff;*.tif"),
                ("All Files", "*.*")
            ]
        )
        if files:
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
        dir_choice = filedialog.askdirectory(title="Select Output Directory for Batch Upscaling")
        if dir_choice:
            self.batch_output_dir = dir_choice
            self.batch_out_lbl.configure(text=f"Output: {self.batch_output_dir}")

    def refresh_batch_list_ui(self):
        for widget in self.batch_listbox_frame.winfo_children():
            widget.destroy()

        if not self.batch_file_list:
            self.batch_empty_lbl = ctk.CTkLabel(
                self.batch_listbox_frame,
                text="No images in batch queue.\nDrag & drop multiple files or a whole folder here!",
                font=self.get_ui_font(13), text_color=THEME_COLORS["text_muted"]
            )
            self.batch_empty_lbl.pack(pady=60)
            return

        for idx, fpath in enumerate(self.batch_file_list):
            row_frame = ctk.CTkFrame(self.batch_listbox_frame, fg_color=THEME_COLORS["bg_card_sub"], height=32)
            row_frame.pack(fill="x", padx=4, pady=2)

            fname_lbl = ctk.CTkLabel(
                row_frame, text=f"{idx + 1}. {os.path.basename(fpath)}",
                font=self.get_ui_font(11), text_color=THEME_COLORS["text_primary"], anchor="w"
            )
            fname_lbl.pack(side="left", padx=8, fill="x", expand=True)

            del_btn = ctk.CTkButton(
                row_frame, text="✕", width=24, height=24, fg_color="transparent",
                hover_color="#fee2e2", text_color="#ef4444", font=self.get_ui_font(10),
                command=lambda p=fpath: self.remove_batch_item(p)
            )
            del_btn.pack(side="right", padx=4)

    def remove_batch_item(self, path: str):
        if path in self.batch_file_list:
            self.batch_file_list.remove(path)
            self.refresh_batch_list_ui()

    def start_batch_upscale(self):
        if not self.batch_file_list:
            messagebox.showwarning("Batch Empty", "Please add images to the batch queue first.")
            return

        if self.is_processing:
            return

        os.makedirs(self.batch_output_dir, exist_ok=True)
        self.is_processing = True
        self.btn_batch_run.configure(state="disabled")
        self.progress_bar.set(0.0)

        selected_algo = self.get_selected_algo_code()
        fmt_choice = self.fmt_menu.get().upper()

        worker = threading.Thread(
            target=self._run_batch_worker,
            args=(
                list(self.batch_file_list),
                self.batch_output_dir,
                self.scale_type,
                self.scale_val,
                selected_algo,
                self.switch_bg.get() == 1,
                self.switch_deblur.get() == 1,
                3 if self.switch_denoise.get() == 1 else 0,
                self.switch_hdr.get() == 1,
                fmt_choice,
                300
            ),
            daemon=True
        )
        worker.start()

    def _run_batch_worker(self, files, out_dir, s_type, s_val, algo, bg_cut, deblur, denoise, hdr, fmt, dpi):
        total = len(files)
        success_count = 0

        for idx, fpath in enumerate(files):
            try:
                progress = (idx + 1) / total
                self.after(0, lambda p=progress, i=idx+1, t=total, fn=os.path.basename(fpath): (
                    self.progress_bar.set(p),
                    self.status_lbl.configure(text=f"Batch ({i}/{t}): Processing {fn}...")
                ))

                with open(fpath, "rb") as f:
                    img_bytes = f.read()

                out_bytes, _ = UpscalerEngine.process_image(
                    image_bytes=img_bytes,
                    scale_type=s_type,
                    scale_val=s_val,
                    algorithm=algo,
                    remove_bg=bg_cut,
                    deblur=deblur,
                    denoise_level=denoise,
                    auto_hdr=hdr,
                    output_format=fmt,
                    output_dpi=dpi
                )

                base_name = os.path.splitext(os.path.basename(fpath))[0]
                ext = "jpg" if fmt in ("JPEG", "JPG") else fmt.lower()
                dest_path = os.path.join(out_dir, f"{base_name}_aupscaled.{ext}")

                with open(dest_path, "wb") as out_f:
                    out_f.write(out_bytes)

                success_count += 1
            except Exception:
                pass

        self.after(0, self._on_batch_complete, success_count, total, out_dir)

    def _on_batch_complete(self, count: int, total: int, out_dir: str):
        self.is_processing = False
        self.btn_batch_run.configure(state="normal")
        self.progress_bar.set(1.0)
        self.status_lbl.configure(text=f"✓ Batch Complete: {count}/{total} images upscaled!")
        messagebox.showinfo(
            "Batch Complete",
            f"Successfully processed {count} of {total} images!\nSaved to:\n{out_dir}"
        )


if __name__ == "__main__":
    app = AupscalerApp()
    app.mainloop()
