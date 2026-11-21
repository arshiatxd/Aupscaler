import io
import unittest

import numpy as np
from PIL import Image

from backend.upscaler import OperationCancelled, UpscalerEngine


def smooth_noise_image(width: int, height: int, seed: int = 0) -> np.ndarray:
    rng = np.random.RandomState(seed)
    small = rng.randint(0, 255, (max(2, height // 8), max(2, width // 8), 3), dtype=np.uint8)
    return np.asarray(Image.fromarray(small).resize((width, height), Image.Resampling.BICUBIC))


class TestUpscalerEngine(unittest.TestCase):
    def setUp(self):
        self.test_img = Image.new("RGB", (100, 100), color=(120, 150, 180))
        img_byte_arr = io.BytesIO()
        self.test_img.save(img_byte_arr, format="PNG")
        self.test_img_bytes = img_byte_arr.getvalue()

    def test_calculate_target_size_multiplier(self):
        w, h, factor = UpscalerEngine.calculate_target_size(100, 100, "multiplier", 4.0)
        self.assertEqual(w, 400)
        self.assertEqual(h, 400)
        self.assertAlmostEqual(factor, 4.0)

    def test_calculate_target_size_percent(self):
        w, h, factor = UpscalerEngine.calculate_target_size(100, 100, "percent", 40.0)
        self.assertEqual(w, 140)
        self.assertEqual(h, 140)
        self.assertAlmostEqual(factor, 1.4)

    def test_fsrcnn_deep_learning_inference(self):
        cv_img = np.random.randint(0, 255, (60, 60, 3), dtype=np.uint8)
        res = UpscalerEngine.apply_deep_learning_sr(cv_img, 240, 240, "fsrcnn")
        self.assertEqual(res.shape, (240, 240, 3))

    def test_espcn_deep_learning_inference(self):
        cv_img = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        res = UpscalerEngine.apply_deep_learning_sr(cv_img, 200, 200, "espcn")
        self.assertEqual(res.shape, (200, 200, 3))

    def test_lapsrn_deep_learning_inference(self):
        cv_img = np.random.randint(0, 255, (40, 40, 3), dtype=np.uint8)
        res = UpscalerEngine.apply_deep_learning_sr(cv_img, 160, 160, "lapsrn")
        self.assertEqual(res.shape, (160, 160, 3))

    def test_alpha_channel_survives_inference(self):
        rgb = smooth_noise_image(64, 48)
        alpha = np.full((48, 64, 1), 200, dtype=np.uint8)
        res = UpscalerEngine.apply_deep_learning_sr(np.dstack((rgb, alpha)), 128, 96, "fsrcnn")
        self.assertEqual(res.shape, (96, 128, 4))
        self.assertTrue(np.all(res[:, :, 3] == 200))

    def test_tiled_inference_matches_single_pass(self):
        bgr = smooth_noise_image(700, 330, seed=4)
        sr_engine, scale = UpscalerEngine.get_dnn_sr_model("fsrcnn", 2)

        tiled = UpscalerEngine._run_sr_tiled(sr_engine, bgr, scale)
        direct = sr_engine.upsample(np.ascontiguousarray(bgr))

        self.assertEqual(tiled.shape, direct.shape)
        difference = np.abs(tiled.astype(np.int16) - direct.astype(np.int16))
        self.assertLess(float(difference.mean()), 0.5)

    def test_process_image_full_pipeline(self):
        out_bytes, meta = UpscalerEngine.process_image(
            image_bytes=self.test_img_bytes,
            scale_type="multiplier",
            scale_val=2.0,
            algorithm="fsrcnn",
            deblur=True,
            denoise_level=3,
            auto_hdr=True,
            output_format="PNG"
        )
        self.assertIsNotNone(out_bytes)
        self.assertEqual(meta["target_width"], 200)
        self.assertEqual(meta["target_height"], 200)
        self.assertEqual(meta["format"], "PNG")

    def test_run_pipeline_returns_image_without_encoding(self):
        result, meta = UpscalerEngine.run_pipeline(self.test_img, scale_val=3.0, algorithm="lanczos")
        self.assertEqual(result.size, (300, 300))
        self.assertEqual(meta["target_width"], 300)

    def test_write_image_formats(self):
        for fmt in ("png", "jpg", "webp", "tiff"):
            buffer = io.BytesIO()
            written = UpscalerEngine.write_image(Image.new("RGBA", (16, 16), (1, 2, 3, 255)), buffer, fmt)
            self.assertGreater(len(buffer.getvalue()), 0)
            self.assertIn(written, ("PNG", "JPEG", "WEBP", "TIFF"))

    def test_roi_preview_generation(self):
        orig_prev, upscaled_prev = UpscalerEngine.generate_roi_preview(
            image_bytes=self.test_img_bytes,
            scale_type="multiplier",
            scale_val=2.0,
            algorithm="fsrcnn",
            auto_hdr=True
        )
        self.assertIsNotNone(orig_prev)
        self.assertIsNotNone(upscaled_prev)

    def test_preview_output_is_bounded(self):
        source = Image.fromarray(smooth_noise_image(1200, 800))
        result = UpscalerEngine.generate_preview(source, scale_val=40.0, algorithm="lanczos")
        self.assertLessEqual(result.width * result.height, UpscalerEngine.PREVIEW_MAX_OUTPUT_PIXELS * 1.05)
        self.assertGreaterEqual(result.width, UpscalerEngine.PREVIEW_DEFAULT_SOURCE)

    def test_preview_keeps_aspect_ratio(self):
        source = Image.fromarray(smooth_noise_image(900, 300))
        result = UpscalerEngine.generate_preview(source, scale_val=4.0, algorithm="fsrcnn")
        self.assertAlmostEqual(result.width / result.height, 3.0, delta=0.05)

    def test_preview_can_be_cancelled(self):
        source = Image.fromarray(smooth_noise_image(400, 300))
        with self.assertRaises(OperationCancelled):
            UpscalerEngine.generate_preview(source, scale_val=2.0, cancel_check=lambda: True)

    def test_cancel_mid_pipeline_stops_before_inference(self):
        source = Image.fromarray(smooth_noise_image(400, 300))
        calls = {"count": 0}

        def cancel_after_first_stage():
            calls["count"] += 1
            return calls["count"] > 2

        with self.assertRaises(OperationCancelled):
            UpscalerEngine.generate_preview(
                source, scale_val=2.0, denoise_level=3, deblur=True, cancel_check=cancel_after_first_stage
            )

    def test_background_removal_is_cached_for_previews(self):
        array = np.full((96, 96, 3), 240, dtype=np.uint8)
        array[24:72, 24:72] = (200, 30, 30)
        image = Image.fromarray(array)

        first = UpscalerEngine.remove_background(image, use_cache=True)
        second = UpscalerEngine.remove_background(image, use_cache=True)

        self.assertIs(first, second)
        self.assertEqual(first.mode, "RGBA")
        self.assertEqual(first.size, image.size)

    def test_1x_upscale_returns_identity(self):
        img = smooth_noise_image(128, 96, seed=7)
        for algo in ("espcn", "fsrcnn", "lanczos", "nearest"):
            out = UpscalerEngine.upscale_memory_safe(img, 128, 96, algo)
            self.assertEqual(out.shape, img.shape)
            self.assertTrue(np.array_equal(out, img))

    def test_solid_background_removal_preserves_subject_and_thin_wire(self):
        arr = np.full((160, 160, 3), (140, 235, 70), dtype=np.uint8)
        arr[40:140, 30:95] = (12, 12, 12)
        arr[35:115, 118:120] = (248, 248, 248)
        img = Image.fromarray(arr)

        cutout = UpscalerEngine.remove_background(img, use_cache=False)
        self.assertEqual(cutout.mode, "RGBA")
        self.assertEqual(cutout.size, (160, 160))
        alpha = np.asarray(cutout)[:, :, 3]
        self.assertEqual(int(alpha[10, 10]), 0)
        self.assertEqual(int(alpha[90, 60]), 255)
        self.assertGreater(int(alpha[75, 118]), 200)

    def test_enhancements_preserve_rgba_channels(self):
        rgb = smooth_noise_image(80, 64, seed=11)
        alpha = np.full((64, 80, 1), 180, dtype=np.uint8)
        rgba = np.dstack((rgb, alpha))

        denoised = UpscalerEngine.deblock_and_denoise(rgba, strength=3)
        deblurred = UpscalerEngine.apply_deblur(rgba, strength=0.55)
        hdr = UpscalerEngine.auto_hdr_enhance(rgba)

        for out in (denoised, deblurred, hdr):
            self.assertEqual(out.shape, rgba.shape)
            self.assertTrue(np.array_equal(out[:, :, 3], alpha[:, :, 0]))

    def test_detect_letterbox_mask(self):
        arr = np.full((160, 200, 3), 140, dtype=np.uint8)
        arr[:24, :, :] = 2
        arr[-24:, :, :] = 3
        mask = UpscalerEngine._detect_letterbox_mask(arr)
        self.assertEqual(mask.shape, (160, 200))
        self.assertEqual(int(mask[:24, :].max()), 0)
        self.assertEqual(int(mask[-24:, :].max()), 0)
        self.assertEqual(int(mask[40:120, :].min()), 1)

    def test_smart_cutout_isolates_selected_object(self):
        arr = np.full((160, 240, 3), 240, dtype=np.uint8)
        arr[40:120, 25:85] = (30, 80, 210)
        arr[40:120, 155:215] = (210, 50, 40)
        pil_img = Image.fromarray(arr, mode="RGB")

        right_lasso = [
            (145, 30), (225, 30), (225, 130), (145, 130), (145, 30)
        ]
        mask = UpscalerEngine.smart_cutout(pil_img, right_lasso)
        self.assertEqual(mask.shape, (160, 240))
        self.assertGreater(int(mask[65:95, 175:195].mean()), 200)
        self.assertLess(int(mask[65:95, 45:65].mean()), 20)

        left_lasso = [
            (15, 30), (95, 30), (95, 130), (15, 130), (15, 30)
        ]
        both_mask = UpscalerEngine.smart_cutout(
            pil_img, left_lasso, existing_alpha=mask, additive=True
        )
        self.assertGreater(int(both_mask[65:95, 175:195].mean()), 200)
        self.assertGreater(int(both_mask[65:95, 45:65].mean()), 200)

    def test_apply_brush_stroke_erase_and_restore(self):
        mask = np.full((100, 100), 255, dtype=np.uint8)
        UpscalerEngine.apply_brush_stroke(mask, [(50, 50), (60, 50)], radius=8, erase=True, soft=False)
        self.assertEqual(int(mask[50, 55]), 0)

        UpscalerEngine.apply_brush_stroke(mask, [(55, 50)], radius=10, erase=False, soft=False)
        self.assertEqual(int(mask[50, 55]), 255)

        soft_mask = np.full((100, 100), 255, dtype=np.uint8)
        UpscalerEngine.apply_brush_stroke(soft_mask, [(50, 50)], radius=12, erase=True, soft=True)
        self.assertLess(int(soft_mask[50, 50]), 40)
        rim = soft_mask[50, 62]
        self.assertTrue(0 < int(rim) < 255)

    def test_run_pipeline_with_alpha_mask_tight_bbox(self):
        arr = np.full((100, 120, 3), 25, dtype=np.uint8)
        arr[35:65, 45:75] = (40, 160, 220)
        pil_img = Image.fromarray(arr, mode="RGB")

        alpha = np.zeros((100, 120), dtype=np.uint8)
        alpha[35:65, 45:75] = 255

        result, meta = UpscalerEngine.run_pipeline(
            pil_img,
            scale_type="multiplier",
            scale_val=2.0,
            algorithm="espcn",
            remove_bg=True,
            alpha_mask=alpha
        )
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.size, (240, 200))
        self.assertEqual(meta["target_width"], 240)
        out_arr = np.asarray(result)
        self.assertEqual(int(out_arr[:40, :40, 3].max()), 0)
        self.assertGreater(int(out_arr[90:110, 110:130, 3].min()), 200)

    def test_smart_cutout_subtract_removes_targeted_object(self):
        arr = np.full((160, 240, 3), 240, dtype=np.uint8)
        arr[40:120, 25:85] = (30, 80, 210)
        arr[40:120, 155:215] = (210, 50, 40)
        pil_img = Image.fromarray(arr, mode="RGB")

        right_lasso = [(145, 30), (225, 30), (225, 130), (145, 130), (145, 30)]
        left_lasso = [(15, 30), (95, 30), (95, 130), (15, 130), (15, 30)]
        mask = UpscalerEngine.smart_cutout(pil_img, right_lasso)
        both = UpscalerEngine.smart_cutout(pil_img, left_lasso, existing_alpha=mask, additive=True)
        self.assertGreater(int(both[65:95, 175:195].mean()), 200)
        self.assertGreater(int(both[65:95, 45:65].mean()), 200)

        only_left = UpscalerEngine.smart_cutout(pil_img, right_lasso, existing_alpha=both, subtract=True)
        self.assertLess(int(only_left[65:95, 175:195].mean()), 20)
        self.assertGreater(int(only_left[65:95, 45:65].mean()), 200)

    def test_apply_deep_learning_sr_rgba_no_dark_fringe_bleed(self):
        bgra = np.zeros((80, 80, 4), dtype=np.uint8)
        bgra[20:60, 20:60, :3] = (230, 220, 210)
        bgra[20:60, 20:60, 3] = 255
        out = UpscalerEngine.apply_deep_learning_sr(bgra, 160, 160, "fsrcnn")
        self.assertEqual(out.shape, (160, 160, 4))
        edge_strip = out[40:44, 42:118, :3]
        self.assertGreater(float(edge_strip.min()), 160.0)
        self.assertGreater(int(out[50:110, 50:110, 3].min()), 230)
        self.assertEqual(int(out[:20, :20, 3].max()), 0)

    def test_generate_preview_1x_preserves_native_resolution(self):
        img = Image.fromarray(smooth_noise_image(1200, 800, seed=5), mode="RGB")
        alpha = np.full((800, 1200), 255, dtype=np.uint8)
        alpha[:100, :] = 0
        out = UpscalerEngine.generate_preview(
            img, scale_type="multiplier", scale_val=1.0, algorithm="espcn", remove_bg=True, alpha_mask=alpha
        )
        self.assertEqual(out.size, (1200, 800))
        self.assertEqual(out.mode, "RGBA")


if __name__ == "__main__":
    unittest.main()
