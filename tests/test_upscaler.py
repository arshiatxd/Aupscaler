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


if __name__ == "__main__":
    unittest.main()
