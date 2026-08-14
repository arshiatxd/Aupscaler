import io
import os
import sys
import math
import gc
import logging
from typing import Tuple, Optional, Dict, Any, List
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import cv2
import numpy as np

Image.MAX_IMAGE_PIXELS = None
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

REMBG_AVAILABLE = False
try:
    import importlib.util
    if importlib.util.find_spec("rembg") is not None:
        REMBG_AVAILABLE = True
except Exception:
    REMBG_AVAILABLE = False


def get_models_directory() -> str:
    candidates = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, "models"))
    
    exe_dir = os.path.dirname(sys.executable)
    candidates.append(os.path.join(exe_dir, "models"))
    candidates.append(os.path.join(exe_dir, "_internal", "models"))

    try:
        cur_file_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(os.path.dirname(cur_file_dir), "models"))
        candidates.append(os.path.join(cur_file_dir, "models"))
    except Exception:
        pass

    candidates.append(os.path.abspath("models"))

    for c in candidates:
        if os.path.isdir(c):
            return c
    return os.path.abspath("models")


class UpscalerEngine:
    ALGORITHMS = {
        "fsrcnn": "FSRCNN (Fast Deep Super-Resolution CNN)",
        "espcn": "ESPCN (Sub-Pixel Convolutional Neural Network)",
        "lapsrn": "LapSRN (Deep Laplacian Pyramid Network)",
        "super_res": "Super-Res (Deep Edge & Texture Synthesis)",
        "lanczos": "Lanczos-4 Sinc (Photo & Ultra Fine Detail)",
        "document": "Document & Text Vectorizer (High Contrast Clarity)",
        "bicubic": "Bicubic Spline (Smooth Natural Gradients)",
        "nearest": "Pixel Art / Retro (Nearest 0% Blur)"
    }

    _sr_cache = {}

    @classmethod
    def get_dnn_sr_model(cls, model_name: str, scale: int):
        key = f"{model_name}_{scale}"
        if key in cls._sr_cache:
            return cls._sr_cache[key]

        models_dir = get_models_directory()
        model_filename = f"{model_name.upper()}_x{scale}.pb"
        model_path = os.path.join(models_dir, model_filename)

        if not os.path.isfile(model_path):
            candidates = [4, 3, 2]
            for c in candidates:
                cand_path = os.path.join(models_dir, f"{model_name.upper()}_x{c}.pb")
                if os.path.isfile(cand_path):
                    model_path = cand_path
                    scale = c
                    break

        if not os.path.isfile(model_path):
            return None

        try:
            sr = cv2.dnn_superres.DnnSuperResImpl_create()
            sr.readModel(model_path)
            sr.setModel(model_name.lower(), scale)
            cls._sr_cache[key] = (sr, scale)
            return sr, scale
        except Exception:
            return None

    @staticmethod
    def calculate_target_size(
        orig_w: int,
        orig_h: int,
        scale_type: str,
        scale_val: float,
        target_w: Optional[int] = None,
        target_h: Optional[int] = None
    ) -> Tuple[int, int, float]:
        if scale_type == "exact" and target_w and target_h:
            w = max(1, int(target_w))
            h = max(1, int(target_h))
            eff_factor = max(w / orig_w, h / orig_h)
            return w, h, eff_factor

        if scale_type == "percent":
            if scale_val <= 100:
                factor = 1.0 + (scale_val / 100.0)
            else:
                factor = scale_val / 100.0
        else:
            factor = max(0.1, min(40.0, float(scale_val)))

        factor = min(40.0, max(1.0, factor))
        target_w = max(1, int(round(orig_w * factor)))
        target_h = max(1, int(round(orig_h * factor)))

        MAX_SAFE_PIXELS = 160_000_000
        if (target_w * target_h) > MAX_SAFE_PIXELS:
            reduction = math.sqrt(MAX_SAFE_PIXELS / (target_w * target_h))
            target_w = max(1, int(target_w * reduction))
            target_h = max(1, int(target_h * reduction))
            factor = target_w / orig_w

        return target_w, target_h, factor

    @classmethod
    def remove_background(cls, pil_img: Image.Image) -> Image.Image:
        try:
            import rembg
            return rembg.remove(pil_img)
        except Exception:
            pass

        try:
            rgb_img = pil_img.convert("RGB")
            cv_img = cv2.cvtColor(np.array(rgb_img), cv2.COLOR_RGB2BGR)
            h, w = cv_img.shape[:2]

            mask = np.zeros((h, w), np.uint8)
            bgd_model = np.zeros((1, 65), np.float64)
            fgd_model = np.zeros((1, 65), np.float64)
            rect = (max(2, int(w * 0.05)), max(2, int(h * 0.05)), max(4, int(w * 0.9)), max(4, int(h * 0.9)))

            cv2.grabCut(cv_img, mask, rect, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_RECT)
            mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype("uint8")
            alpha = (mask2 * 255).astype(np.uint8)

            rgba = np.dstack((np.array(rgb_img), alpha))
            return Image.fromarray(rgba, "RGBA")
        except Exception:
            return pil_img

    @classmethod
    def deblock_and_denoise(cls, cv_img: np.ndarray, strength: int = 3) -> np.ndarray:
        if strength <= 0:
            return cv_img

        has_alpha = cv_img.shape[2] == 4 if len(cv_img.shape) == 3 else False
        if has_alpha:
            bgr = cv_img[:, :, :3]
            alpha = cv_img[:, :, 3]
        else:
            bgr = cv_img

        h, w = bgr.shape[:2]
        try:
            if (h * w) <= (1400 * 1400):
                denoised = cv2.fastNlMeansDenoisingColored(
                    bgr, None, h=7, hColor=7, templateWindowSize=5, searchWindowSize=15
                )
            else:
                denoised = cv2.bilateralFilter(bgr, d=7, sigmaColor=28, sigmaSpace=12)
        except Exception:
            denoised = cv2.bilateralFilter(bgr, d=7, sigmaColor=28, sigmaSpace=12)

        if has_alpha:
            return np.dstack((denoised, alpha))
        return denoised

    @classmethod
    def apply_ai_deblur(cls, cv_img: np.ndarray, strength: float = 0.5) -> np.ndarray:
        if strength <= 0:
            return cv_img

        has_alpha = cv_img.shape[2] == 4 if len(cv_img.shape) == 3 else False
        if has_alpha:
            bgr = cv_img[:, :, :3]
            alpha = cv_img[:, :, 3]
        else:
            bgr = cv_img

        gaussian1 = cv2.GaussianBlur(bgr, (0, 0), 1.0)
        unsharp1 = cv2.addWeighted(bgr, 1.4, gaussian1, -0.4, 0)

        gaussian2 = cv2.GaussianBlur(bgr, (0, 0), 2.2)
        unsharp2 = cv2.addWeighted(unsharp1, 1.2, gaussian2, -0.2, 0)

        deblurred = cv2.addWeighted(bgr, 1.0 - strength, unsharp2, strength, 0)

        if has_alpha:
            return np.dstack((deblurred, alpha))
        return deblurred

    @classmethod
    def auto_hdr_enhance(cls, cv_img: np.ndarray, clip_limit: float = 1.25) -> np.ndarray:
        has_alpha = cv_img.shape[2] == 4 if len(cv_img.shape) == 3 else False
        if has_alpha:
            bgr = cv_img[:, :, :3]
            alpha = cv_img[:, :, 3]
        else:
            bgr = cv_img

        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
        cl = clahe.apply(l)

        l_norm = cl.astype(np.float32) / 255.0
        l_gamma = np.power(l_norm, 0.96) * 255.0
        l_gamma = np.clip(l_gamma, 0, 255).astype(np.uint8)

        limg = cv2.merge((l_gamma, a, b))
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.04, 0, 255)
        enhanced = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        if has_alpha:
            return np.dstack((enhanced, alpha))
        return enhanced

    @classmethod
    def enhance_document_text(cls, cv_img: np.ndarray) -> np.ndarray:
        has_alpha = cv_img.shape[2] == 4 if len(cv_img.shape) == 3 else False
        if has_alpha:
            bgr = cv_img[:, :, :3]
            alpha = cv_img[:, :, 3]
        else:
            bgr = cv_img

        gaussian = cv2.GaussianBlur(bgr, (0, 0), 1.2)
        sharpened = cv2.addWeighted(bgr, 1.6, gaussian, -0.6, 0)

        lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(4, 4))
        l_cl = clahe.apply(l)
        enhanced = cv2.cvtColor(cv2.merge((l_cl, a, b)), cv2.COLOR_LAB2BGR)

        if has_alpha:
            return np.dstack((enhanced, alpha))
        return enhanced

    @classmethod
    def apply_ai_super_res(cls, cv_img: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
        in_h, in_w = cv_img.shape[:2]
        has_alpha = cv_img.shape[2] == 4 if len(cv_img.shape) == 3 else False

        if has_alpha:
            bgr = cv_img[:, :, :3]
            alpha = cv_img[:, :, 3]
            alpha_up = cv2.resize(alpha, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
        else:
            bgr = cv_img
            alpha_up = None

        base_upscaled = cv2.resize(bgr, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

        ycrcb = cv2.cvtColor(base_upscaled, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)

        g1 = cv2.GaussianBlur(y, (0, 0), 1.0)
        d1 = cv2.subtract(y, g1)
        g2 = cv2.GaussianBlur(y, (0, 0), 2.4)
        d2 = cv2.subtract(g1, g2)

        sobelx = cv2.Sobel(y, cv2.CV_32F, 1, 0, ksize=3)
        sobely = cv2.Sobel(y, cv2.CV_32F, 0, 1, ksize=3)
        grad_mag = np.sqrt(sobelx**2 + sobely**2)
        grad_norm = np.clip(grad_mag / 90.0, 0.0, 1.0)

        y_float = y.astype(np.float32)
        y_boosted = y_float + d1.astype(np.float32) * (0.80 + 0.50 * grad_norm) + d2.astype(np.float32) * 0.35
        y_boosted = np.clip(y_boosted, 0, 255).astype(np.uint8)

        clahe = cv2.createCLAHE(clipLimit=1.35, tileGridSize=(8, 8))
        y_final = clahe.apply(y_boosted)

        upscaled_boosted = cv2.cvtColor(cv2.merge((y_final, cr, cb)), cv2.COLOR_YCrCb2BGR)

        kernel = np.array([[0, -0.30, 0], [-0.30, 2.2, -0.30], [0, -0.30, 0]], dtype=np.float32)
        sharpened_edges = cv2.filter2D(upscaled_boosted, -1, kernel)
        final_res = cv2.addWeighted(upscaled_boosted, 0.40, sharpened_edges, 0.60, 0)

        if alpha_up is not None:
            return np.dstack((final_res, alpha_up))
        return final_res

    @classmethod
    def apply_deep_learning_sr(
        cls,
        cv_img: np.ndarray,
        target_w: int,
        target_h: int,
        model_name: str
    ) -> np.ndarray:
        in_h, in_w = cv_img.shape[:2]
        eff_scale = max(target_w / in_w, target_h / in_h)
        discrete_scale = 4 if eff_scale >= 3.5 else (3 if eff_scale >= 2.5 else 2)

        dnn_info = cls.get_dnn_sr_model(model_name, discrete_scale)
        if not dnn_info:
            return cls.apply_ai_super_res(cv_img, target_w, target_h)

        sr_engine, actual_scale = dnn_info
        has_alpha = cv_img.shape[2] == 4 if len(cv_img.shape) == 3 else False

        if has_alpha:
            bgr = cv_img[:, :, :3]
            alpha = cv_img[:, :, 3]
            alpha_up = cv2.resize(alpha, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
        else:
            bgr = cv_img
            alpha_up = None

        try:
            if (in_w * in_h) <= (1024 * 1024):
                sr_out = sr_engine.upsample(bgr)
            else:
                tile_size = 512
                overlap = 16
                out_h_sr = in_h * actual_scale
                out_w_sr = in_w * actual_scale
                sr_out = np.zeros((out_h_sr, out_w_sr, 3), dtype=np.uint8)

                for y in range(0, in_h, tile_size - overlap):
                    for x in range(0, in_w, tile_size - overlap):
                        y_end = min(in_h, y + tile_size)
                        x_end = min(in_w, x + tile_size)
                        tile = bgr[y:y_end, x:x_end]
                        tile_sr = sr_engine.upsample(tile)

                        y_out = y * actual_scale
                        x_out = x * actual_scale
                        y_out_end = y_end * actual_scale
                        x_out_end = x_end * actual_scale

                        h_chunk = min(y_out_end - y_out, tile_sr.shape[0])
                        w_chunk = min(x_out_end - x_out, tile_sr.shape[1])
                        sr_out[y_out:y_out + h_chunk, x_out:x_out + w_chunk] = tile_sr[:h_chunk, :w_chunk]

            if sr_out.shape[1] != target_w or sr_out.shape[0] != target_h:
                sr_out = cv2.resize(sr_out, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

            if alpha_up is not None:
                return np.dstack((sr_out, alpha_up))
            return sr_out
        except Exception:
            return cls.apply_ai_super_res(cv_img, target_w, target_h)

    @classmethod
    def upscale_memory_safe(
        cls,
        cv_img: np.ndarray,
        target_w: int,
        target_h: int,
        algorithm: str
    ) -> np.ndarray:
        in_h, in_w = cv_img.shape[:2]

        if algorithm in ("fsrcnn", "espcn", "lapsrn"):
            return cls.apply_deep_learning_sr(cv_img, target_w, target_h, algorithm)

        if algorithm == "super_res":
            if (target_w * target_h) <= (3200 * 3200):
                return cls.apply_ai_super_res(cv_img, target_w, target_h)

        if algorithm == "bicubic":
            interp = cv2.INTER_CUBIC
        elif algorithm == "nearest":
            interp = cv2.INTER_NEAREST
        else:
            interp = cv2.INTER_LANCZOS4

        if (target_w * target_h) <= (3000 * 3000):
            try:
                res = cv2.resize(cv_img, (target_w, target_h), interpolation=interp)
                if algorithm not in ("nearest", "bicubic"):
                    has_alpha = res.shape[2] == 4 if len(res.shape) == 3 else False
                    bgr = res[:, :, :3] if has_alpha else res
                    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
                    y, cr, cb = cv2.split(ycrcb)
                    gauss_y = cv2.GaussianBlur(y, (0, 0), 1.0)
                    detail = cv2.subtract(y, gauss_y)
                    y_sharp = cv2.addWeighted(y, 1.0, detail, 0.6, 0)
                    res_bgr = cv2.cvtColor(cv2.merge((y_sharp, cr, cb)), cv2.COLOR_YCrCb2BGR)
                    if has_alpha:
                        return np.dstack((res_bgr, res[:, :, 3]))
                    return res_bgr
                return res
            except Exception:
                pass

        channels = cv_img.shape[2] if len(cv_img.shape) == 3 else 1
        tile_height_in = max(64, min(1024, int(40_000_000 / (target_w * (target_h / in_h) * channels))))
        scale_y = target_h / in_h

        out_img = np.zeros((target_h, target_w, channels) if channels > 1 else (target_h, target_w), dtype=np.uint8)

        for y_in in range(0, in_h, tile_height_in):
            y_in_end = min(in_h, y_in + tile_height_in)
            y_out = int(round(y_in * scale_y))
            y_out_end = int(round(y_in_end * scale_y))

            if y_in_end == in_h:
                y_out_end = target_h

            strip_in = cv_img[y_in:y_in_end, :]
            strip_out_h = y_out_end - y_out

            if strip_out_h <= 0:
                continue

            try:
                strip_upscaled = cv2.resize(strip_in, (target_w, strip_out_h), interpolation=interp)
                out_img[y_out:y_out_end, :] = strip_upscaled
            except Exception:
                pil_strip = Image.fromarray(strip_in)
                pil_res = pil_strip.resize((target_w, strip_out_h), Image.Resampling.LANCZOS)
                out_img[y_out:y_out_end, :] = np.array(pil_res)

        return out_img

    @classmethod
    def process_image(
        cls,
        image_bytes: bytes,
        scale_type: str = "multiplier",
        scale_val: float = 2.0,
        target_w: Optional[int] = None,
        target_h: Optional[int] = None,
        algorithm: str = "fsrcnn",
        remove_bg: bool = False,
        deblur: bool = False,
        denoise_level: int = 0,
        auto_hdr: bool = False,
        output_format: str = "PNG",
        output_dpi: int = 300,
        progress_callback: Optional[Any] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        if progress_callback:
            progress_callback(0.1, "Initializing image...")

        pil_img = Image.open(io.BytesIO(image_bytes))
        pil_img = ImageOps.exif_transpose(pil_img)

        if remove_bg:
            if progress_callback:
                progress_callback(0.2, "Executing Deep Learning Background Removal...")
            pil_img = cls.remove_background(pil_img)

        has_alpha = pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info)
        if has_alpha:
            pil_img = pil_img.convert("RGBA")
            cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGBA2BGRA)
        else:
            pil_img = pil_img.convert("RGB")
            cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        orig_w, orig_h = pil_img.size
        out_w, out_h, eff_factor = cls.calculate_target_size(
            orig_w, orig_h, scale_type, scale_val, target_w, target_h
        )

        if denoise_level > 0:
            if progress_callback:
                progress_callback(0.3, "Executing Non-Local Means Denoising...")
            cv_img = cls.deblock_and_denoise(cv_img, strength=denoise_level)

        if deblur:
            if progress_callback:
                progress_callback(0.4, "Executing AI Focus Deblur & Clarity...")
            cv_img = cls.apply_ai_deblur(cv_img, strength=0.55)

        if auto_hdr:
            if progress_callback:
                progress_callback(0.5, "Applying Balanced Natural HDR...")
            cv_img = cls.auto_hdr_enhance(cv_img)

        if algorithm == "document":
            cv_img = cls.enhance_document_text(cv_img)

        if progress_callback:
            progress_callback(0.7, f"Deep Learning inference ({algorithm.upper()}: {out_w}×{out_h})...")

        try:
            upscaled = cls.upscale_memory_safe(cv_img, out_w, out_h, algorithm)
        except Exception:
            resample_mode = Image.Resampling.NEAREST if algorithm == "nearest" else Image.Resampling.LANCZOS
            final_pil = pil_img.resize((out_w, out_h), resample_mode)
            upscaled = None

        if upscaled is not None:
            if has_alpha:
                final_pil = Image.fromarray(cv2.cvtColor(upscaled, cv2.COLOR_BGRA2RGBA))
            else:
                final_pil = Image.fromarray(cv2.cvtColor(upscaled, cv2.COLOR_BGR2RGB))

        if progress_callback:
            progress_callback(0.9, f"Encoding export format ({output_format.upper()})...")

        out_fmt = output_format.upper()
        if out_fmt not in ("PNG", "JPEG", "JPG", "WEBP", "TIFF"):
            out_fmt = "PNG"

        if out_fmt in ("JPEG", "JPG") and final_pil.mode in ("RGBA", "LA", "P"):
            final_pil = final_pil.convert("RGB")

        out_io = io.BytesIO()
        save_kwargs: Dict[str, Any] = {"dpi": (output_dpi, output_dpi)}

        if out_fmt == "PNG":
            final_pil.save(out_io, format="PNG", **save_kwargs)
        elif out_fmt in ("JPEG", "JPG"):
            save_kwargs["quality"] = 98
            final_pil.save(out_io, format="JPEG", **save_kwargs)
        elif out_fmt == "WEBP":
            save_kwargs["quality"] = 95
            final_pil.save(out_io, format="WEBP", **save_kwargs)
        elif out_fmt == "TIFF":
            final_pil.save(out_io, format="TIFF", **save_kwargs)

        out_bytes = out_io.getvalue()

        meta = {
            "orig_width": orig_w,
            "orig_height": orig_h,
            "target_width": out_w,
            "target_height": out_h,
            "scale_factor": round(eff_factor, 3),
            "algorithm": algorithm,
            "format": out_fmt,
            "dpi": output_dpi,
            "file_size_bytes": len(out_bytes),
            "file_size_mb": round(len(out_bytes) / (1024 * 1024), 2)
        }

        gc.collect()
        return out_bytes, meta

    @classmethod
    def generate_roi_preview(
        cls,
        image_bytes: bytes,
        scale_type: str = "multiplier",
        scale_val: float = 2.0,
        algorithm: str = "fsrcnn",
        remove_bg: bool = False,
        deblur: bool = False,
        denoise_level: int = 0,
        auto_hdr: bool = False
    ) -> Tuple[bytes, bytes]:
        pil_img = Image.open(io.BytesIO(image_bytes))
        pil_img = ImageOps.exif_transpose(pil_img)
        w, h = pil_img.size

        max_preview_dim = 1600
        if max(w, h) > max_preview_dim:
            scale_down = max_preview_dim / max(w, h)
            pw = max(1, int(w * scale_down))
            ph = max(1, int(h * scale_down))
            preview_base = pil_img.resize((pw, ph), Image.Resampling.LANCZOS)
        else:
            preview_base = pil_img

        orig_io = io.BytesIO()
        preview_base.save(orig_io, format="PNG")
        orig_preview_bytes = orig_io.getvalue()

        upscaled_bytes, _ = cls.process_image(
            image_bytes=orig_preview_bytes,
            scale_type=scale_type,
            scale_val=scale_val,
            algorithm=algorithm,
            remove_bg=remove_bg,
            deblur=deblur,
            denoise_level=denoise_level,
            auto_hdr=auto_hdr,
            output_format="PNG"
        )

        return orig_preview_bytes, upscaled_bytes
