import concurrent.futures
import gc
import hashlib
import importlib.util
import io
import logging
import math
import os
import queue
import sys
import threading
from collections import OrderedDict
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = None
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

REMBG_AVAILABLE = importlib.util.find_spec("rembg") is not None

ProgressCallback = Optional[Callable[[float, str], None]]
CancelCheck = Optional[Callable[[], bool]]


class OperationCancelled(Exception):
    pass


def _checkpoint(cancel_check: CancelCheck) -> None:
    if cancel_check is not None and cancel_check():
        raise OperationCancelled()


@lru_cache(maxsize=1)
def get_models_directory() -> str:
    candidates = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, "models"))

    exe_dir = os.path.dirname(sys.executable)
    candidates.append(os.path.join(exe_dir, "models"))
    candidates.append(os.path.join(exe_dir, "_internal", "models"))

    cur_file_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(os.path.dirname(cur_file_dir), "models"))
    candidates.append(os.path.join(cur_file_dir, "models"))
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

    PREVIEW_DEFAULT_SOURCE = 560
    PREVIEW_SOURCE_LIMITS = {"lapsrn": 448}
    PREVIEW_MAX_OUTPUT_PIXELS = 2_400_000

    TILE_SIZE = 512
    TILE_PAD = 12
    BG_WORK_DIM = 640
    BG_CACHE_SIZE = 4

    _sr_cache: Dict[str, Tuple[Any, int]] = {}
    _sr_pool_cache: Dict[Tuple[str, int], List[Any]] = {}
    _sr_cache_lock = threading.Lock()
    _infer_lock = threading.Lock()

    _bg_cache: "OrderedDict[Any, Image.Image]" = OrderedDict()
    _bg_cache_lock = threading.Lock()
    _rembg_sessions: Dict[str, Any] = {}
    _rembg_failed: set = set()
    _rembg_lock = threading.Lock()

    @classmethod
    def get_dnn_sr_model(cls, model_name: str, scale: int):
        key = f"{model_name}_{scale}"
        with cls._sr_cache_lock:
            cached = cls._sr_cache.get(key)
        if cached is not None:
            return cached

        models_dir = get_models_directory()
        resolved_scale = scale
        model_path = os.path.join(models_dir, f"{model_name.upper()}_x{scale}.pb")

        if not os.path.isfile(model_path):
            for candidate in (4, 3, 2):
                candidate_path = os.path.join(models_dir, f"{model_name.upper()}_x{candidate}.pb")
                if os.path.isfile(candidate_path):
                    model_path = candidate_path
                    resolved_scale = candidate
                    break

        if not os.path.isfile(model_path):
            return None

        try:
            sr = cv2.dnn_superres.DnnSuperResImpl_create()
            sr.readModel(model_path)
            sr.setModel(model_name.lower(), resolved_scale)
        except cv2.error as exc:
            logger.error("Could not load %s: %s", model_path, exc)
            return None

        entry = (sr, resolved_scale)
        with cls._sr_cache_lock:
            cls._sr_cache[key] = entry
        return entry

    @classmethod
    def _get_sr_pool(cls, model_name: str, scale: int, count: int = 2) -> List[Any]:
        pool_key = (model_name.lower(), int(scale))
        with cls._sr_cache_lock:
            existing = cls._sr_pool_cache.get(pool_key)
            if existing is not None and len(existing) >= count:
                return existing[:count]

        models_dir = get_models_directory()
        model_path = os.path.join(models_dir, f"{model_name.upper()}_x{scale}.pb")
        if not os.path.isfile(model_path):
            return []

        created: List[Any] = []
        for _ in range(count):
            try:
                sr = cv2.dnn_superres.DnnSuperResImpl_create()
                sr.readModel(model_path)
                sr.setModel(model_name.lower(), int(scale))
                created.append(sr)
            except cv2.error:
                break

        if created:
            with cls._sr_cache_lock:
                cls._sr_pool_cache[pool_key] = created
        return created

    @classmethod
    def warm_up(cls, model_name: str = "espcn", scale: int = 2, warm_cutout: bool = False) -> None:
        info = cls.get_dnn_sr_model(model_name, scale)
        if info:
            sr, _ = info
            try:
                with cls._infer_lock:
                    sr.upsample(np.zeros((16, 16, 3), dtype=np.uint8))
            except cv2.error as exc:
                logger.error("Model warm-up failed: %s", exc)
        if warm_cutout:
            cls._get_rembg_session("isnet-general-use")

    @classmethod
    def analyze_image(
        cls,
        img_bytes: bytes,
        scale_type: str = "multiplier",
        scale_val: float = 2.0,
        target_w: Optional[int] = None,
        target_h: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        pil_img = Image.open(io.BytesIO(img_bytes))
        orig_w, orig_h = pil_img.size
        out_w, out_h, eff_factor = cls.calculate_target_size(
            orig_w, orig_h, scale_type, scale_val, target_w, target_h
        )
        orig_mp = (orig_w * orig_h) / 1_000_000.0
        target_mp = (out_w * out_h) / 1_000_000.0
        ram_mb = (out_w * out_h * 4) / (1024 * 1024)
        return {
            "orig_width": orig_w,
            "orig_height": orig_h,
            "target_width": out_w,
            "target_height": out_h,
            "scale_factor": round(eff_factor, 2),
            "orig_megapixels": round(orig_mp, 2),
            "target_megapixels": round(target_mp, 2),
            "estimated_ram_mb": round(ram_mb, 1)
        }

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

        max_safe_pixels = 160_000_000
        if (target_w * target_h) > max_safe_pixels:
            reduction = math.sqrt(max_safe_pixels / (target_w * target_h))
            target_w = max(1, int(target_w * reduction))
            target_h = max(1, int(target_h * reduction))
            factor = target_w / orig_w

        return target_w, target_h, factor

    @staticmethod
    def _split_alpha(cv_img: np.ndarray) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        if cv_img.ndim == 3 and cv_img.shape[2] == 4:
            return np.ascontiguousarray(cv_img[:, :, :3]), np.ascontiguousarray(cv_img[:, :, 3])
        return cv_img, None

    @staticmethod
    def _merge_alpha(bgr: np.ndarray, alpha: Optional[np.ndarray]) -> np.ndarray:
        if alpha is None:
            return bgr
        return np.dstack((bgr, alpha))

    @classmethod
    def _get_rembg_session(cls, model_name: str = "isnet-general-use"):
        if not REMBG_AVAILABLE:
            return None
        with cls._rembg_lock:
            if model_name in cls._rembg_sessions:
                return cls._rembg_sessions[model_name]
            candidates = (model_name, "u2net") if model_name != "u2net" else ("u2net",)
            for name in candidates:
                if name in cls._rembg_sessions:
                    return cls._rembg_sessions[name]
                if name in cls._rembg_failed:
                    continue
                try:
                    import onnxruntime as ort
                    import rembg
                    so = ort.SessionOptions()
                    so.intra_op_num_threads = min(8, os.cpu_count() or 4)
                    so.inter_op_num_threads = 1
                    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                    sess = rembg.new_session(name, sess_options=so, providers=["CPUExecutionProvider"])
                    cls._rembg_sessions[name] = sess
                    return sess
                except Exception as exc:
                    logger.error("rembg session %s unavailable: %s", name, exc)
                    cls._rembg_failed.add(name)
            return None

    @staticmethod
    def _detect_letterbox_mask(rgb: np.ndarray) -> np.ndarray:
        h, w = rgb.shape[:2]
        valid = np.ones((h, w), dtype=np.uint8)
        if h < 32 or w < 32:
            return valid

        row_max = rgb.max(axis=(1, 2))
        top = 0
        while top < h // 3 and row_max[top] <= 8:
            top += 1
        bottom = h
        while bottom > (h * 2) // 3 and row_max[bottom - 1] <= 8:
            bottom -= 1
        if top > 8:
            valid[:top, :] = 0
        if (h - bottom) > 8:
            valid[bottom:, :] = 0

        col_max = rgb.max(axis=(0, 2))
        left = 0
        while left < w // 4 and col_max[left] <= 8:
            left += 1
        right = w
        while right > (w * 3) // 4 and col_max[right - 1] <= 8:
            right -= 1
        if left > 8:
            valid[:, :left] = 0
        if (w - right) > 8:
            valid[:, right:] = 0

        return valid

    @staticmethod
    def _guided_filter_gray(guide: np.ndarray, src: np.ndarray, radius: int = 4, eps: float = 1e-3) -> np.ndarray:
        I = guide.astype(np.float32) / 255.0
        p = src.astype(np.float32) / 255.0
        k = (2 * radius + 1, 2 * radius + 1)
        mean_I = cv2.boxFilter(I, cv2.CV_32F, k)
        mean_p = cv2.boxFilter(p, cv2.CV_32F, k)
        mean_Ip = cv2.boxFilter(I * p, cv2.CV_32F, k)
        cov_Ip = mean_Ip - mean_I * mean_p
        mean_II = cv2.boxFilter(I * I, cv2.CV_32F, k)
        var_I = mean_II - mean_I * mean_I
        a = cov_Ip / (var_I + eps)
        b = mean_p - a * mean_I
        mean_a = cv2.boxFilter(a, cv2.CV_32F, k)
        mean_b = cv2.boxFilter(b, cv2.CV_32F, k)
        q = mean_a * I + mean_b
        return np.clip(q * 255.0, 0.0, 255.0).astype(np.uint8)

    @classmethod
    def _refine_alpha_edges(
        cls,
        rgb: np.ndarray,
        alpha: np.ndarray,
        valid_lb: Optional[np.ndarray] = None
    ) -> np.ndarray:
        out = alpha.copy()
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        refined = cls._guided_filter_gray(gray, out, radius=4, eps=1e-3)
        band = (out > 10) & (out < 245)
        if np.any(band):
            band = cv2.dilate(band.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
            out[band] = refined[band]
        out[out < 14] = 0
        out[out > 242] = 255
        if valid_lb is not None:
            out[valid_lb == 0] = 0
        return out

    @classmethod
    def _remove_background_grabcut(cls, pil_img: Image.Image) -> Image.Image:
        rgb = np.asarray(pil_img.convert("RGB"))
        h, w = rgb.shape[:2]
        work_scale = min(1.0, cls.BG_WORK_DIM / float(max(h, w)))

        if work_scale < 1.0:
            small = cv2.resize(
                rgb, (max(1, int(w * work_scale)), max(1, int(h * work_scale))),
                interpolation=cv2.INTER_AREA
            )
        else:
            small = rgb

        bgr = cv2.cvtColor(small, cv2.COLOR_RGB2BGR)
        sh, sw = bgr.shape[:2]
        mask = np.zeros((sh, sw), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        rect = (max(2, int(sw * 0.05)), max(2, int(sh * 0.05)), max(4, int(sw * 0.9)), max(4, int(sh * 0.9)))

        cv2.grabCut(bgr, mask, rect, bgd_model, fgd_model, 4, cv2.GC_INIT_WITH_RECT)
        foreground = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        foreground = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, kernel)
        foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, kernel)

        if (sw, sh) != (w, h):
            alpha = cv2.resize(foreground, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            alpha = foreground
        alpha = cv2.GaussianBlur(alpha, (0, 0), 1.2)

        return Image.fromarray(np.dstack((rgb, alpha)))

    @classmethod
    def _remove_solid_background(cls, pil_img: Image.Image) -> Optional[Image.Image]:
        rgb = np.asarray(pil_img.convert("RGB"))
        h, w = rgb.shape[:2]
        if h < 16 or w < 16:
            return None
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
        b = max(4, min(h, w) // 40)
        border = np.concatenate([
            lab[:b, :].reshape(-1, 3),
            lab[-b:, :].reshape(-1, 3),
            lab[:, :b].reshape(-1, 3),
            lab[:, -b:].reshape(-1, 3),
        ], axis=0)
        med = np.median(border, axis=0)
        de_border = np.linalg.norm(border - med, axis=1)
        uniform_ratio = float((de_border < 14.0).mean())
        chroma = float(np.hypot(med[1] - 128.0, med[2] - 128.0))
        if uniform_ratio < 0.55 or chroma < 30.0:
            return None

        de = np.linalg.norm(lab - med.reshape(1, 1, 3), axis=2)
        alpha_f = np.clip((de - 16.0) / 16.0, 0.0, 1.0)
        alpha = (alpha_f * 255.0).astype(np.uint8)
        alpha[alpha < 8] = 0
        alpha[alpha > 248] = 255

        out_rgb = rgb.copy()
        fringe = (alpha_f > 0.02) & (alpha_f < 0.98)
        if np.any(fringe):
            spill_weight = np.clip(1.0 - alpha_f[fringe], 0.0, 1.0)
            lab_fringe = lab[fringe].copy()
            lab_fringe[:, 1] = lab_fringe[:, 1] * (1.0 - spill_weight) + 128.0 * spill_weight
            lab_fringe[:, 2] = lab_fringe[:, 2] * (1.0 - spill_weight) + 128.0 * spill_weight
            lab_u8 = np.clip(lab_fringe, 0.0, 255.0).astype(np.uint8).reshape(-1, 1, 3)
            out_rgb[fringe] = cv2.cvtColor(lab_u8, cv2.COLOR_LAB2RGB).reshape(-1, 3)

        return Image.fromarray(np.dstack((out_rgb, alpha)), mode="RGBA")

    @classmethod
    def remove_background(cls, pil_img: Image.Image, use_cache: bool = False) -> Image.Image:
        key = None
        if use_cache:
            digest = hashlib.blake2b(pil_img.tobytes(), digest_size=16).digest()
            key = (pil_img.size, pil_img.mode, digest)
            with cls._bg_cache_lock:
                hit = cls._bg_cache.get(key)
                if hit is not None:
                    cls._bg_cache.move_to_end(key)
                    return hit

        result = cls._remove_solid_background(pil_img)
        if result is None:
            rgb = np.asarray(pil_img.convert("RGB"))
            valid_lb = cls._detect_letterbox_mask(rgb)
            ys, xs = np.where(valid_lb > 0)
            session = cls._get_rembg_session("isnet-general-use")
            if session is not None and ys.size > 0:
                try:
                    import rembg
                    y0, y1 = int(ys.min()), int(ys.max()) + 1
                    x0, x1 = int(xs.min()), int(xs.max()) + 1
                    full_h, full_w = rgb.shape[:2]
                    cropped_rgb = rgb[y0:y1, x0:x1] if (y0 > 0 or y1 < full_h or x0 > 0 or x1 < full_w) else rgb
                    raw_rgba = rembg.remove(Image.fromarray(cropped_rgb), session=session).convert("RGBA")
                    crop_alpha = np.asarray(raw_rgba)[:, :, 3].copy()
                    crop_alpha = cls._refine_alpha_edges(cropped_rgb, crop_alpha, valid_lb[y0:y1, x0:x1])
                    if cropped_rgb is rgb:
                        full_alpha = crop_alpha
                    else:
                        full_alpha = np.zeros((full_h, full_w), dtype=np.uint8)
                        full_alpha[y0:y1, x0:x1] = crop_alpha
                    result = Image.fromarray(np.dstack((rgb, full_alpha)), mode="RGBA")
                except Exception as exc:
                    logger.error("rembg inference failed, using GrabCut fallback: %s", exc)

        if result is None:
            result = cls._remove_background_grabcut(pil_img)

        if key is not None:
            with cls._bg_cache_lock:
                cls._bg_cache[key] = result
                while len(cls._bg_cache) > cls.BG_CACHE_SIZE:
                    cls._bg_cache.popitem(last=False)
        return result

    @classmethod
    def smart_cutout(
        cls,
        pil_img: Image.Image,
        region_points: List[Tuple[int, int]],
        stroke_width: int = 24,
        existing_alpha: Optional[np.ndarray] = None,
        additive: bool = False
    ) -> np.ndarray:
        rgb = np.asarray(pil_img.convert("RGB"))
        h, w = rgb.shape[:2]
        valid_lb = cls._detect_letterbox_mask(rgb)

        clean_pts = [
            (max(0, min(w - 1, int(round(px)))), max(0, min(h - 1, int(round(py)))))
            for px, py in (region_points or [])
        ]
        if len(clean_pts) < 2:
            if existing_alpha is not None and existing_alpha.shape == (h, w):
                return existing_alpha.copy()
            return np.asarray(cls.remove_background(pil_img).convert("RGBA"))[:, :, 3].copy()

        pts = np.array(clean_pts, dtype=np.int32)
        min_xy = pts.min(axis=0)
        max_xy = pts.max(axis=0)
        diag = float(math.hypot(float(max_xy[0] - min_xy[0]), float(max_xy[1] - min_xy[1])))
        end_dist = float(math.hypot(float(pts[0][0] - pts[-1][0]), float(pts[0][1] - pts[-1][1])))

        stroke_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.polylines(stroke_mask, [pts], isClosed=False, color=255, thickness=max(12, int(stroke_width)))

        poly_mask = np.zeros((h, w), dtype=np.uint8)
        if len(clean_pts) >= 3:
            cv2.fillPoly(poly_mask, [pts], 255)

        is_closed_region = len(clean_pts) >= 3 and (
            end_dist < 0.45 * max(1.0, diag) or float(poly_mask.sum()) > float(stroke_mask.sum()) * 1.4
        )
        if is_closed_region:
            region_mask = poly_mask
            seed_mask = None
        else:
            seed_mask = stroke_mask
            hull = cv2.convexHull(pts)
            region_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillConvexPoly(region_mask, hull, 255)
            scribble_pad = max(36, int(diag * 0.22))
            k_scribble = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (scribble_pad * 2 + 1, scribble_pad * 2 + 1)
            )
            region_mask = cv2.dilate(region_mask | stroke_mask, k_scribble)

        region_mask &= (valid_lb * 255)
        ys, xs = np.where(region_mask > 0)
        if ys.size == 0:
            return np.zeros((h, w), dtype=np.uint8)

        x0, x1 = int(xs.min()), int(xs.max()) + 1
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        rw, rh = x1 - x0, y1 - y0
        pad_x = max(48, int(rw * 0.25))
        pad_y = max(48, int(rh * 0.25))

        lb_ys, lb_xs = np.where(valid_lb > 0)
        min_x_lb = int(lb_xs.min()) if lb_xs.size else 0
        max_x_lb = int(lb_xs.max()) + 1 if lb_xs.size else w
        min_y_lb = int(lb_ys.min()) if lb_ys.size else 0
        max_y_lb = int(lb_ys.max()) + 1 if lb_ys.size else h

        cx0 = max(min_x_lb, x0 - pad_x)
        cy0 = max(min_y_lb, y0 - pad_y)
        cx1 = min(max_x_lb, x1 + pad_x)
        cy1 = min(max_y_lb, y1 + pad_y)

        crop_rgb = rgb[cy0:cy1, cx0:cx1]
        crop_region = region_mask[cy0:cy1, cx0:cx1]
        crop_lb = valid_lb[cy0:cy1, cx0:cx1]
        crop_seed = seed_mask[cy0:cy1, cx0:cx1] if seed_mask is not None else None

        nn_alpha = None
        solid = cls._remove_solid_background(Image.fromarray(crop_rgb))
        if solid is not None:
            nn_alpha = np.asarray(solid)[:, :, 3].astype(np.float32) / 255.0
        else:
            session = cls._get_rembg_session("isnet-general-use")
            if session is not None:
                try:
                    import rembg
                    raw = rembg.remove(Image.fromarray(crop_rgb), session=session).convert("RGBA")
                    nn_alpha = np.asarray(raw)[:, :, 3].astype(np.float32) / 255.0
                except Exception as exc:
                    logger.error("smart_cutout rembg failed: %s", exc)

        if nn_alpha is None:
            nn_alpha = np.zeros(crop_rgb.shape[:2], dtype=np.float32)

        inside = crop_region > 0
        nn_bin = (nn_alpha > 0.35).astype(np.uint8)
        num_lbl, lbls = cv2.connectedComponents(nn_bin)
        keep_nn = np.zeros_like(nn_alpha)
        for lid in range(1, num_lbl):
            comp = (lbls == lid)
            if crop_seed is not None:
                touched = float((comp & (crop_seed > 0)).sum()) > 0.0
                ov_seed = float((comp & inside).sum()) / max(1.0, float(comp.sum()))
                if touched or ov_seed > 0.45:
                    keep_nn[comp] = nn_alpha[comp]
            else:
                ov_comp = float((comp & inside).sum()) / max(1.0, float(comp.sum()))
                ov_reg = float((comp & inside).sum()) / max(1.0, float(inside.sum()))
                if ov_comp > 0.35 or ov_reg > 0.15:
                    keep_nn[comp] = nn_alpha[comp]

        dil_r = max(36, int(diag * 0.20)) if crop_seed is not None else max(12, int(min(rw, rh) * 0.06))
        k_dil = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dil_r * 2 + 1, dil_r * 2 + 1))
        allowed = cv2.dilate(crop_region, k_dil) > 0
        keep_nn[~allowed] = 0.0

        final_cov = float((keep_nn[inside] > 0.5).mean()) if np.any(inside) else 0.0
        if final_cov < 0.20:
            ch, cw = crop_rgb.shape[:2]
            sc = min(1.0, 560.0 / float(max(ch, cw)))
            sw, sh = max(16, int(cw * sc)), max(16, int(ch * sc))
            small_bgr = cv2.cvtColor(cv2.resize(crop_rgb, (sw, sh), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2BGR)
            small_reg = cv2.resize(crop_region, (sw, sh), interpolation=cv2.INTER_NEAREST)
            gc_mask = np.full((sh, sw), cv2.GC_BGD, dtype=np.uint8)
            gc_mask[small_reg > 0] = cv2.GC_PR_BGD
            ek = max(5, int(min(sw, sh) * 0.08)) | 1
            erode_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ek, ek))
            core = cv2.erode(small_reg, erode_k)
            gc_mask[core > 0] = cv2.GC_PR_FGD
            if crop_seed is not None:
                small_seed = cv2.resize(crop_seed, (sw, sh), interpolation=cv2.INTER_NEAREST)
                gc_mask[small_seed > 0] = cv2.GC_FGD
            small_nn = cv2.resize(keep_nn, (sw, sh), interpolation=cv2.INTER_LINEAR)
            gc_mask[(small_nn > 0.7) & (small_reg > 0)] = cv2.GC_FGD
            bgd_model = np.zeros((1, 65), np.float64)
            fgd_model = np.zeros((1, 65), np.float64)
            try:
                cv2.grabCut(small_bgr, gc_mask, None, bgd_model, fgd_model, 4, cv2.GC_INIT_WITH_MASK)
                gc_fg = np.where((gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
                gc_fg = cv2.resize(gc_fg, (cw, ch), interpolation=cv2.INTER_LINEAR)
                alpha_crop = np.maximum((keep_nn * 255.0).astype(np.uint8), gc_fg)
            except cv2.error:
                alpha_crop = (keep_nn * 255.0).astype(np.uint8)
        else:
            alpha_crop = (keep_nn * 255.0).astype(np.uint8)

        alpha_crop = cls._refine_alpha_edges(crop_rgb, alpha_crop, crop_lb)

        full_alpha = np.zeros((h, w), dtype=np.uint8)
        full_alpha[cy0:cy1, cx0:cx1] = alpha_crop
        if additive and existing_alpha is not None and existing_alpha.shape == (h, w):
            return np.maximum(existing_alpha, full_alpha)
        return full_alpha

    @staticmethod
    def apply_brush_stroke(
        alpha_mask: np.ndarray,
        points: List[Tuple[int, int]],
        radius: int,
        erase: bool = True,
        soft: bool = False
    ) -> np.ndarray:
        if not points or alpha_mask is None:
            return alpha_mask
        h, w = alpha_mask.shape[:2]
        r = max(1, int(radius))
        clamped = [(max(0, min(w - 1, int(px))), max(0, min(h - 1, int(py)))) for px, py in points]

        if not soft:
            val = 0 if erase else 255
            if len(clamped) == 1:
                cv2.circle(alpha_mask, clamped[0], r, val, thickness=-1)
            else:
                for p0, p1 in zip(clamped[:-1], clamped[1:]):
                    cv2.line(alpha_mask, p0, p1, val, thickness=r * 2)
            return alpha_mask

        pad = max(8, r * 2)
        xs = [p[0] for p in clamped]
        ys = [p[1] for p in clamped]
        x0 = max(0, min(xs) - pad)
        y0 = max(0, min(ys) - pad)
        x1 = min(w, max(xs) + pad + 1)
        y1 = min(h, max(ys) + pad + 1)
        rw, rh = x1 - x0, y1 - y0
        if rw <= 0 or rh <= 0:
            return alpha_mask

        stroke = np.zeros((rh, rw), dtype=np.uint8)
        local_pts = [(px - x0, py - y0) for px, py in clamped]
        if len(local_pts) == 1:
            cv2.circle(stroke, local_pts[0], r, 255, thickness=-1)
        else:
            for p0, p1 in zip(local_pts[:-1], local_pts[1:]):
                cv2.line(stroke, p0, p1, 255, thickness=r * 2)

        sigma = max(1.0, r * 0.35)
        weight = cv2.GaussianBlur(stroke.astype(np.float32) / 255.0, (0, 0), sigma)
        patch = alpha_mask[y0:y1, x0:x1].astype(np.float32)
        if erase:
            updated = patch * (1.0 - weight)
        else:
            updated = patch + (255.0 - patch) * weight
        alpha_mask[y0:y1, x0:x1] = np.clip(updated, 0.0, 255.0).astype(np.uint8)
        return alpha_mask

    @classmethod
    def deblock_and_denoise(cls, cv_img: np.ndarray, strength: int = 3) -> np.ndarray:
        if strength <= 0:
            return cv_img

        bgr, alpha = cls._split_alpha(cv_img)
        ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)

        cr_clean = cv2.bilateralFilter(cr, d=5, sigmaColor=24, sigmaSpace=10)
        cb_clean = cv2.bilateralFilter(cb, d=5, sigmaColor=24, sigmaSpace=10)
        y_clean = cv2.bilateralFilter(y, d=5, sigmaColor=10 + strength * 3, sigmaSpace=5)
        y_out = cv2.addWeighted(y, 0.45, y_clean, 0.55, 0)

        denoised = cv2.cvtColor(cv2.merge((y_out, cr_clean, cb_clean)), cv2.COLOR_YCrCb2BGR)
        return cls._merge_alpha(denoised, alpha)

    @classmethod
    def apply_deblur(cls, cv_img: np.ndarray, strength: float = 0.5) -> np.ndarray:
        if strength <= 0:
            return cv_img

        bgr, alpha = cls._split_alpha(cv_img)
        ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)

        y_f = y.astype(np.float32)
        blur = cv2.GaussianBlur(y_f, (0, 0), 1.1)
        detail = y_f - blur
        abs_d = np.abs(detail)
        gate = np.clip((abs_d - 2.5) / 5.0, 0.0, 1.0)
        boost = np.clip(detail * gate * (0.95 * strength), -24.0, 24.0)
        y_sharp = np.clip(y_f + boost, 0.0, 255.0).astype(np.uint8)

        deblurred = cv2.cvtColor(cv2.merge((y_sharp, cr, cb)), cv2.COLOR_YCrCb2BGR)
        return cls._merge_alpha(deblurred, alpha)

    @classmethod
    def auto_hdr_enhance(cls, cv_img: np.ndarray, clip_limit: float = 1.08) -> np.ndarray:
        bgr, alpha = cls._split_alpha(cv_img)

        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
        l_clahe = clahe.apply(l).astype(np.float32)

        l_f = l.astype(np.float32)
        shadow_mask = np.clip((l_f - 10.0) / 25.0, 0.0, 1.0)
        l_blend = l_f + (l_clahe - l_f) * (0.35 * shadow_mask)
        norm = np.clip(l_blend / 255.0, 0.0, 1.0)
        s_curve = norm - 0.025 * np.sin(2.0 * math.pi * norm) * shadow_mask
        l_final = np.clip(s_curve * 255.0, 0.0, 255.0).astype(np.uint8)

        enhanced = cv2.cvtColor(cv2.merge((l_final, a, b)), cv2.COLOR_LAB2BGR)

        hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV)
        s_chan = hsv[:, :, 1].astype(np.float32) / 255.0
        v_mask = np.clip((hsv[:, :, 2].astype(np.float32) - 10.0) / 25.0, 0.0, 1.0)
        sat_boost = 1.0 + 0.06 * (1.0 - s_chan) * v_mask
        hsv[:, :, 1] = np.clip(hsv[:, :, 1].astype(np.float32) * sat_boost, 0.0, 255.0).astype(np.uint8)
        enhanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        return cls._merge_alpha(enhanced, alpha)

    @classmethod
    def enhance_document_text(cls, cv_img: np.ndarray) -> np.ndarray:
        bgr, alpha = cls._split_alpha(cv_img)

        gaussian = cv2.GaussianBlur(bgr, (0, 0), 1.2)
        sharpened = cv2.addWeighted(bgr, 1.6, gaussian, -0.6, 0)

        lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(4, 4))
        enhanced = cv2.cvtColor(cv2.merge((clahe.apply(l), a, b)), cv2.COLOR_LAB2BGR)

        return cls._merge_alpha(enhanced, alpha)

    @classmethod
    def apply_synthesis_sr(cls, cv_img: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
        bgr, alpha = cls._split_alpha(cv_img)
        alpha_up = None
        if alpha is not None:
            alpha_up = cv2.resize(alpha, (target_w, target_h), interpolation=cv2.INTER_CUBIC)

        base_upscaled = cv2.resize(bgr, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

        ycrcb = cv2.cvtColor(base_upscaled, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)

        g1 = cv2.GaussianBlur(y, (0, 0), 1.0)
        d1 = cv2.subtract(y, g1)
        g2 = cv2.GaussianBlur(y, (0, 0), 2.4)
        d2 = cv2.subtract(g1, g2)

        sobelx = cv2.Sobel(y, cv2.CV_32F, 1, 0, ksize=3)
        sobely = cv2.Sobel(y, cv2.CV_32F, 0, 1, ksize=3)
        grad_norm = np.clip(cv2.magnitude(sobelx, sobely) / 90.0, 0.0, 1.0)

        y_boosted = y.astype(np.float32) + d1.astype(np.float32) * (0.80 + 0.50 * grad_norm) + d2.astype(np.float32) * 0.35
        y_boosted = np.clip(y_boosted, 0, 255).astype(np.uint8)

        clahe = cv2.createCLAHE(clipLimit=1.35, tileGridSize=(8, 8))
        y_final = clahe.apply(y_boosted)

        upscaled_boosted = cv2.cvtColor(cv2.merge((y_final, cr, cb)), cv2.COLOR_YCrCb2BGR)

        kernel = np.array([[0, -0.30, 0], [-0.30, 2.2, -0.30], [0, -0.30, 0]], dtype=np.float32)
        sharpened_edges = cv2.filter2D(upscaled_boosted, -1, kernel)
        final_res = cv2.addWeighted(upscaled_boosted, 0.40, sharpened_edges, 0.60, 0)

        return cls._merge_alpha(final_res, alpha_up)

    @classmethod
    def _run_sr_tiled(
        cls,
        sr_engine: Any,
        bgr: np.ndarray,
        scale: int,
        cancel_check: CancelCheck = None,
        on_progress: Optional[Callable[[float], None]] = None,
        model_name: Optional[str] = None
    ) -> np.ndarray:
        in_h, in_w = bgr.shape[:2]
        tile = cls.TILE_SIZE

        if in_h * in_w <= tile * tile:
            _checkpoint(cancel_check)
            with cls._infer_lock:
                return sr_engine.upsample(np.ascontiguousarray(bgr))

        pad = cls.TILE_PAD
        out = np.empty((in_h * scale, in_w * scale, 3), dtype=np.uint8)
        coords = []
        for y in range(0, in_h, tile):
            y_end = min(in_h, y + tile)
            y0 = max(0, y - pad)
            y1 = min(in_h, y_end + pad)
            for x in range(0, in_w, tile):
                x_end = min(in_w, x + tile)
                x0 = max(0, x - pad)
                x1 = min(in_w, x_end + pad)
                coords.append((y, y_end, y0, y1, x, x_end, x0, x1))

        total_tiles = len(coords)
        pool = cls._get_sr_pool(model_name, scale, 2) if (model_name and total_tiles >= 2) else []

        if len(pool) >= 2:
            sr_queue: "queue.Queue[Any]" = queue.Queue()
            for inst in pool:
                sr_queue.put(inst)
            progress_lock = threading.Lock()
            done = 0

            def run_tile(c):
                nonlocal done
                _checkpoint(cancel_check)
                y, y_end, y0, y1, x, x_end, x0, x1 = c
                patch = np.ascontiguousarray(bgr[y0:y1, x0:x1])
                inst = sr_queue.get()
                try:
                    patch_sr = inst.upsample(patch)
                finally:
                    sr_queue.put(inst)
                oy = (y - y0) * scale
                ox = (x - x0) * scale
                th = (y_end - y) * scale
                tw = (x_end - x) * scale
                out[y * scale:y_end * scale, x * scale:x_end * scale] = patch_sr[oy:oy + th, ox:ox + tw]
                with progress_lock:
                    done += 1
                    frac = done / total_tiles
                if on_progress is not None:
                    on_progress(frac)

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(run_tile, c) for c in coords]
                for fut in concurrent.futures.as_completed(futures):
                    fut.result()
            return out

        done = 0
        for y, y_end, y0, y1, x, x_end, x0, x1 in coords:
            _checkpoint(cancel_check)
            patch = np.ascontiguousarray(bgr[y0:y1, x0:x1])
            with cls._infer_lock:
                patch_sr = sr_engine.upsample(patch)

            oy = (y - y0) * scale
            ox = (x - x0) * scale
            th = (y_end - y) * scale
            tw = (x_end - x) * scale
            out[y * scale:y_end * scale, x * scale:x_end * scale] = patch_sr[oy:oy + th, ox:ox + tw]

            done += 1
            if on_progress is not None:
                on_progress(done / total_tiles)
        return out

    @classmethod
    def apply_deep_learning_sr(
        cls,
        cv_img: np.ndarray,
        target_w: int,
        target_h: int,
        model_name: str,
        cancel_check: CancelCheck = None,
        on_progress: Optional[Callable[[float], None]] = None
    ) -> np.ndarray:
        in_h, in_w = cv_img.shape[:2]
        if target_w == in_w and target_h == in_h:
            return cv_img
        eff_scale = max(target_w / in_w, target_h / in_h)
        discrete_scale = 4 if eff_scale >= 3.5 else (3 if eff_scale >= 2.5 else 2)

        dnn_info = cls.get_dnn_sr_model(model_name, discrete_scale)
        if not dnn_info:
            return cls.apply_synthesis_sr(cv_img, target_w, target_h)

        sr_engine, actual_scale = dnn_info
        bgr, alpha = cls._split_alpha(cv_img)
        alpha_up = None
        if alpha is not None:
            alpha_up = cv2.resize(alpha, (target_w, target_h), interpolation=cv2.INTER_CUBIC)

        try:
            sr_out = cls._run_sr_tiled(
                sr_engine, bgr, actual_scale, cancel_check, on_progress, model_name=model_name
            )
        except (cv2.error, MemoryError) as exc:
            logger.error("Neural inference failed, using synthesis fallback: %s", exc)
            return cls.apply_synthesis_sr(cv_img, target_w, target_h)

        if sr_out.shape[1] != target_w or sr_out.shape[0] != target_h:
            shrinking = target_w < sr_out.shape[1] or target_h < sr_out.shape[0]
            interp = cv2.INTER_AREA if shrinking else cv2.INTER_LANCZOS4
            sr_out = cv2.resize(sr_out, (target_w, target_h), interpolation=interp)

        return cls._merge_alpha(sr_out, alpha_up)

    @classmethod
    def upscale_memory_safe(
        cls,
        cv_img: np.ndarray,
        target_w: int,
        target_h: int,
        algorithm: str,
        cancel_check: CancelCheck = None,
        on_progress: Optional[Callable[[float], None]] = None
    ) -> np.ndarray:
        in_h, in_w = cv_img.shape[:2]
        if target_w == in_w and target_h == in_h:
            return cv_img

        if cv_img.ndim == 3 and cv_img.shape[2] == 4 and algorithm in ("fsrcnn", "espcn", "lapsrn", "super_res"):
            ys, xs = np.where(cv_img[:, :, 3] > 0)
            if ys.size == 0:
                return np.zeros((target_h, target_w, 4), dtype=np.uint8)
            pad = 16
            x0 = max(0, int(xs.min()) - pad)
            y0 = max(0, int(ys.min()) - pad)
            x1 = min(in_w, int(xs.max()) + 1 + pad)
            y1 = min(in_h, int(ys.max()) + 1 + pad)
            if (x1 - x0) * (y1 - y0) < int(0.75 * in_w * in_h) and (x1 - x0) >= 8 and (y1 - y0) >= 8:
                ox0 = int(round(x0 * target_w / in_w))
                oy0 = int(round(y0 * target_h / in_h))
                ox1 = max(ox0 + 1, min(target_w, int(round(x1 * target_w / in_w))))
                oy1 = max(oy0 + 1, min(target_h, int(round(y1 * target_h / in_h))))
                sub = np.ascontiguousarray(cv_img[y0:y1, x0:x1])
                sub_tw = ox1 - ox0
                sub_th = oy1 - oy0
                if algorithm in ("fsrcnn", "espcn", "lapsrn"):
                    sub_out = cls.apply_deep_learning_sr(sub, sub_tw, sub_th, algorithm, cancel_check, on_progress)
                else:
                    sub_out = cls.apply_synthesis_sr(sub, sub_tw, sub_th)
                out_rgba = np.zeros((target_h, target_w, 4), dtype=np.uint8)
                out_rgba[oy0:oy1, ox0:ox1] = sub_out
                return out_rgba

        if algorithm in ("fsrcnn", "espcn", "lapsrn"):
            return cls.apply_deep_learning_sr(cv_img, target_w, target_h, algorithm, cancel_check, on_progress)

        if algorithm == "super_res" and (target_w * target_h) <= (3200 * 3200):
            return cls.apply_synthesis_sr(cv_img, target_w, target_h)

        if algorithm == "bicubic":
            interp = cv2.INTER_CUBIC
        elif algorithm == "nearest":
            interp = cv2.INTER_NEAREST
        else:
            interp = cv2.INTER_LANCZOS4

        if (target_w * target_h) <= (3000 * 3000):
            res = cv2.resize(cv_img, (target_w, target_h), interpolation=interp)
            if algorithm in ("nearest", "bicubic") or (target_w <= in_w and target_h <= in_h):
                return res
            bgr, alpha = cls._split_alpha(res)
            ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
            y, cr, cb = cv2.split(ycrcb)
            detail = cv2.subtract(y, cv2.GaussianBlur(y, (0, 0), 1.0))
            y_sharp = cv2.addWeighted(y, 1.0, detail, 0.18, 0)
            res_bgr = cv2.cvtColor(cv2.merge((y_sharp, cr, cb)), cv2.COLOR_YCrCb2BGR)
            return cls._merge_alpha(res_bgr, alpha)

        channels = cv_img.shape[2] if cv_img.ndim == 3 else 1
        tile_height_in = max(64, min(1024, int(40_000_000 / (target_w * (target_h / in_h) * channels))))
        scale_y = target_h / in_h

        out_shape = (target_h, target_w, channels) if channels > 1 else (target_h, target_w)
        out_img = np.zeros(out_shape, dtype=np.uint8)
        strips = math.ceil(in_h / tile_height_in)

        for index, y_in in enumerate(range(0, in_h, tile_height_in)):
            _checkpoint(cancel_check)
            y_in_end = min(in_h, y_in + tile_height_in)
            y_out = int(round(y_in * scale_y))
            y_out_end = target_h if y_in_end == in_h else int(round(y_in_end * scale_y))

            strip_out_h = y_out_end - y_out
            if strip_out_h <= 0:
                continue

            strip_in = np.ascontiguousarray(cv_img[y_in:y_in_end, :])
            out_img[y_out:y_out_end, :] = cv2.resize(strip_in, (target_w, strip_out_h), interpolation=interp)

            if on_progress is not None:
                on_progress((index + 1) / strips)

        return out_img

    @classmethod
    def run_pipeline(
        cls,
        pil_img: Image.Image,
        scale_type: str = "multiplier",
        scale_val: float = 2.0,
        target_w: Optional[int] = None,
        target_h: Optional[int] = None,
        algorithm: str = "fsrcnn",
        remove_bg: bool = False,
        deblur: bool = False,
        denoise_level: int = 0,
        auto_hdr: bool = False,
        progress_callback: ProgressCallback = None,
        cancel_check: CancelCheck = None,
        preview: bool = False,
        alpha_mask: Optional[np.ndarray] = None
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        def report(fraction: float, message: str) -> None:
            if progress_callback is not None:
                progress_callback(fraction, message)

        _checkpoint(cancel_check)
        report(0.1, "Preparing image...")

        if alpha_mask is not None:
            src_rgb = pil_img.convert("RGB")
            orig_w, orig_h = src_rgb.size
            if alpha_mask.shape[1] != orig_w or alpha_mask.shape[0] != orig_h:
                mask_resized = cv2.resize(alpha_mask, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
            else:
                mask_resized = alpha_mask
            rgb_arr = np.asarray(src_rgb)
            cv_img = np.dstack((cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR), mask_resized))
            pil_img = Image.fromarray(np.dstack((rgb_arr, mask_resized)), mode="RGBA")
        else:
            if remove_bg:
                report(0.15, "Removing background...")
                pil_img = cls.remove_background(pil_img, use_cache=preview)
                _checkpoint(cancel_check)

            has_alpha = pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info)
            if has_alpha:
                if pil_img.mode != "RGBA":
                    pil_img = pil_img.convert("RGBA")
                cv_img = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGBA2BGRA)
            else:
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                cv_img = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)

        orig_w, orig_h = pil_img.size
        out_w, out_h, eff_factor = cls.calculate_target_size(
            orig_w, orig_h, scale_type, scale_val, target_w, target_h
        )

        if denoise_level > 0:
            report(0.3, "Removing noise...")
            cv_img = cls.deblock_and_denoise(cv_img, strength=denoise_level)
            _checkpoint(cancel_check)

        if deblur:
            report(0.4, "Restoring focus and clarity...")
            cv_img = cls.apply_deblur(cv_img, strength=0.55)
            _checkpoint(cancel_check)

        if auto_hdr:
            report(0.5, "Balancing tone and color...")
            cv_img = cls.auto_hdr_enhance(cv_img)
            _checkpoint(cancel_check)

        if algorithm == "document":
            cv_img = cls.enhance_document_text(cv_img)

        message = f"Upscaling ({algorithm.upper()}: {out_w} × {out_h})..."
        report(0.6, message)

        def on_progress(fraction: float) -> None:
            report(0.6 + 0.35 * fraction, message)

        try:
            upscaled = cls.upscale_memory_safe(cv_img, out_w, out_h, algorithm, cancel_check, on_progress)
            if upscaled.shape[2] == 4:
                final_pil = Image.fromarray(cv2.cvtColor(upscaled, cv2.COLOR_BGRA2RGBA))
            else:
                final_pil = Image.fromarray(cv2.cvtColor(upscaled, cv2.COLOR_BGR2RGB))
        except (cv2.error, MemoryError) as exc:
            logger.error("Upscaling failed, using plain resize: %s", exc)
            resample_mode = Image.Resampling.NEAREST if algorithm == "nearest" else Image.Resampling.LANCZOS
            final_pil = pil_img.resize((out_w, out_h), resample_mode)

        meta = {
            "orig_width": orig_w,
            "orig_height": orig_h,
            "target_width": out_w,
            "target_height": out_h,
            "scale_factor": round(eff_factor, 3),
            "algorithm": algorithm
        }
        return final_pil, meta

    @staticmethod
    def _normalize_format(output_format: str) -> str:
        fmt = output_format.upper()
        if fmt == "JPG":
            fmt = "JPEG"
        elif fmt == "TIF":
            fmt = "TIFF"
        return fmt if fmt in ("PNG", "JPEG", "WEBP", "TIFF") else "PNG"

    @classmethod
    def write_image(cls, pil_img: Image.Image, target: Any, output_format: str = "PNG", output_dpi: int = 300) -> str:
        fmt = cls._normalize_format(output_format)
        image = pil_img
        if fmt == "JPEG" and image.mode in ("RGBA", "LA", "P"):
            image = image.convert("RGB")

        kwargs: Dict[str, Any] = {"dpi": (output_dpi, output_dpi)}
        if fmt == "PNG":
            kwargs["compress_level"] = 3
        elif fmt == "JPEG":
            kwargs["quality"] = 98
        elif fmt == "WEBP":
            kwargs["quality"] = 95

        image.save(target, format=fmt, **kwargs)
        return fmt

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
        progress_callback: ProgressCallback = None,
        cancel_check: CancelCheck = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        pil_img = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes)))

        final_pil, meta = cls.run_pipeline(
            pil_img,
            scale_type=scale_type,
            scale_val=scale_val,
            target_w=target_w,
            target_h=target_h,
            algorithm=algorithm,
            remove_bg=remove_bg,
            deblur=deblur,
            denoise_level=denoise_level,
            auto_hdr=auto_hdr,
            progress_callback=progress_callback,
            cancel_check=cancel_check
        )

        if progress_callback is not None:
            progress_callback(0.97, f"Encoding {output_format.upper()}...")

        out_io = io.BytesIO()
        fmt = cls.write_image(final_pil, out_io, output_format, output_dpi)
        out_bytes = out_io.getvalue()

        meta.update({
            "format": fmt,
            "dpi": output_dpi,
            "file_size_bytes": len(out_bytes),
            "file_size_mb": round(len(out_bytes) / (1024 * 1024), 2)
        })

        gc.collect()
        return out_bytes, meta

    @classmethod
    def prepare_preview_source(cls, pil_img: Image.Image, max_dim: Optional[int] = None) -> Image.Image:
        limit = max_dim or cls.PREVIEW_DEFAULT_SOURCE
        w, h = pil_img.size
        longest = max(w, h)
        if longest <= limit:
            return pil_img
        ratio = limit / float(longest)
        size = (max(1, int(round(w * ratio))), max(1, int(round(h * ratio))))
        return pil_img.resize(size, Image.Resampling.BILINEAR, reducing_gap=2.0)

    @classmethod
    def generate_preview(
        cls,
        preview_source: Image.Image,
        scale_type: str = "multiplier",
        scale_val: float = 2.0,
        algorithm: str = "fsrcnn",
        remove_bg: bool = False,
        deblur: bool = False,
        denoise_level: int = 0,
        auto_hdr: bool = False,
        cancel_check: CancelCheck = None,
        alpha_mask: Optional[np.ndarray] = None
    ) -> Image.Image:
        limit = cls.PREVIEW_SOURCE_LIMITS.get(algorithm, cls.PREVIEW_DEFAULT_SOURCE)
        source = cls.prepare_preview_source(preview_source, limit)
        src_w, src_h = source.size

        out_w, out_h, _ = cls.calculate_target_size(src_w, src_h, scale_type, scale_val)
        if out_w * out_h > cls.PREVIEW_MAX_OUTPUT_PIXELS:
            reduction = math.sqrt(cls.PREVIEW_MAX_OUTPUT_PIXELS / float(out_w * out_h))
            out_w = max(src_w, int(out_w * reduction))
            out_h = max(src_h, int(out_h * reduction))

        result, _ = cls.run_pipeline(
            source,
            scale_type="exact",
            target_w=out_w,
            target_h=out_h,
            algorithm=algorithm,
            remove_bg=remove_bg,
            deblur=deblur,
            denoise_level=denoise_level,
            auto_hdr=auto_hdr,
            cancel_check=cancel_check,
            preview=True,
            alpha_mask=alpha_mask
        )
        return result

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
        pil_img = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes)))
        source = cls.prepare_preview_source(pil_img)

        upscaled = cls.generate_preview(
            source,
            scale_type=scale_type,
            scale_val=scale_val,
            algorithm=algorithm,
            remove_bg=remove_bg,
            deblur=deblur,
            denoise_level=denoise_level,
            auto_hdr=auto_hdr
        )

        orig_io = io.BytesIO()
        source.save(orig_io, format="PNG")
        upscaled_io = io.BytesIO()
        cls.write_image(upscaled, upscaled_io, "PNG")
        return orig_io.getvalue(), upscaled_io.getvalue()
