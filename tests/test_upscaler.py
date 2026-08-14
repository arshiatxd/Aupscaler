import os
import io
import unittest
from PIL import Image
import numpy as np
import cv2

from backend.upscaler import UpscalerEngine


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


if __name__ == "__main__":
    unittest.main()
