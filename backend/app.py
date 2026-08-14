"""
FastAPI Server & REST API for aupscaler
"""

import os
import sys
import io
import uuid
import zipfile
import base64
import psutil
from typing import Optional, List
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import Response, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .upscaler import UpscalerEngine, REMBG_AVAILABLE

app = FastAPI(
    title="aupscaler",
    description="Studio-Grade 40x AI Image Super-Resolution & Enhancement Engine",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for processed downloads (with automatic cleanup)
STORAGE = {}
MAX_STORAGE_ITEMS = 50


def store_file(file_bytes: bytes, filename: str, mime_type: str) -> str:
    """Stores generated image in memory and keeps cache bounded."""
    if len(STORAGE) > MAX_STORAGE_ITEMS:
        # Evict oldest
        oldest_key = next(iter(STORAGE))
        del STORAGE[oldest_key]

    file_id = str(uuid.uuid4())
    STORAGE[file_id] = {
        "bytes": file_bytes,
        "filename": filename,
        "mime": mime_type
    }
    return file_id


@app.get("/api/health")
async def health_check():
    """System diagnostic and capability report."""
    mem = psutil.virtual_memory()
    return {
        "status": "online",
        "app_name": "aupscaler",
        "rembg_available": REMBG_AVAILABLE,
        "max_scale": 40.0,
        "preset_percentages": [5, 10, 15, 20, 25, 30, 35, 40],
        "algorithms": UpscalerEngine.ALGORITHMS,
        "system_ram": {
            "total_gb": round(mem.total / (1024**3), 1),
            "available_gb": round(mem.available / (1024**3), 1),
            "percent_used": mem.percent
        }
    }


@app.post("/api/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    scale_type: str = Form("multiplier"),
    scale_val: float = Form(2.0),
    target_w: Optional[int] = Form(None),
    target_h: Optional[int] = Form(None)
):
    """Inspects uploaded image and returns dimension/RAM calculation."""
    try:
        contents = await file.read()
        analysis = UpscalerEngine.analyze_image(
            img_bytes=contents,
            scale_type=scale_type,
            scale_val=scale_val
        )
        return analysis
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to analyze image: {str(e)}")


@app.post("/api/preview")
async def get_preview(
    file: UploadFile = File(...),
    scale_type: str = Form("multiplier"),
    scale_val: float = Form(2.0),
    algorithm: str = Form("lanczos"),
    remove_bg: bool = Form(False),
    face_enhance: bool = Form(False),
    denoise_level: int = Form(0),
    auto_hdr: bool = Form(False),
    sharpen_strength: float = Form(0.4)
):
    """Generates fast ROI Before/After preview images."""
    try:
        contents = await file.read()
        orig_roi, upscaled_roi = UpscalerEngine.generate_roi_preview(
            image_bytes=contents,
            scale_type=scale_type,
            scale_val=scale_val,
            algorithm=algorithm,
            remove_bg=remove_bg,
            face_enhance=face_enhance,
            denoise_level=denoise_level,
            auto_hdr=auto_hdr,
            sharpen_strength=sharpen_strength
        )

        return {
            "orig_roi_base64": f"data:image/png;base64,{base64.b64encode(orig_roi).decode('utf-8')}",
            "upscaled_roi_base64": f"data:image/png;base64,{base64.b64encode(upscaled_roi).decode('utf-8')}"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Preview generation failed: {str(e)}")


@app.post("/api/upscale")
async def upscale_image(
    file: UploadFile = File(...),
    scale_type: str = Form("multiplier"),
    scale_val: float = Form(2.0),
    target_w: Optional[int] = Form(None),
    target_h: Optional[int] = Form(None),
    algorithm: str = Form("lanczos"),
    remove_bg: bool = Form(False),
    face_enhance: bool = Form(False),
    face_amount: float = Form(0.5),
    denoise_level: int = Form(0),
    auto_hdr: bool = Form(False),
    sharpen_strength: float = Form(0.4),
    output_format: str = Form("PNG"),
    output_dpi: int = Form(300)
):
    """Runs complete 40x upscaling pipeline on image."""
    try:
        contents = await file.read()
        processed_bytes, meta = UpscalerEngine.process_image(
            image_bytes=contents,
            scale_type=scale_type,
            scale_val=scale_val,
            target_w=target_w,
            target_h=target_h,
            algorithm=algorithm,
            remove_bg=remove_bg,
            face_enhance=face_enhance,
            face_amount=face_amount,
            denoise_level=denoise_level,
            auto_hdr=auto_hdr,
            sharpen_strength=sharpen_strength,
            output_format=output_format,
            output_dpi=output_dpi
        )

        # Build output filename
        orig_name = os.path.splitext(file.filename or "image")[0]
        ext = output_format.lower()
        if ext == "jpeg":
            ext = "jpg"
        out_filename = f"{orig_name}_aupscaler_{meta['scale_factor']}x_{meta['target_width']}x{meta['target_height']}.{ext}"

        mime_map = {
            "PNG": "image/png",
            "JPEG": "image/jpeg",
            "JPG": "image/jpeg",
            "WEBP": "image/webp",
            "TIFF": "image/tiff"
        }
        mime_type = mime_map.get(output_format.upper(), "image/png")

        file_id = store_file(processed_bytes, out_filename, mime_type)

        # Also return base64 for quick display if under 15MB
        b64_data = None
        if len(processed_bytes) <= 15 * 1024 * 1024:
            b64_data = f"data:{mime_type};base64,{base64.b64encode(processed_bytes).decode('utf-8')}"

        return {
            "success": True,
            "file_id": file_id,
            "filename": out_filename,
            "download_url": f"/api/download/{file_id}",
            "meta": meta,
            "preview_data": b64_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upscaling processing failed: {str(e)}")


@app.post("/api/batch-upscale")
async def batch_upscale(
    files: List[UploadFile] = File(...),
    scale_type: str = Form("multiplier"),
    scale_val: float = Form(2.0),
    algorithm: str = Form("lanczos"),
    remove_bg: bool = Form(False),
    face_enhance: bool = Form(False),
    denoise_level: int = Form(0),
    auto_hdr: bool = Form(False),
    sharpen_strength: float = Form(0.4),
    output_format: str = Form("PNG"),
    output_dpi: int = Form(300)
):
    """Processes multiple images and creates a bundled ZIP archive."""
    try:
        results = []
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for idx, file in enumerate(files):
                contents = await file.read()
                try:
                    processed_bytes, meta = UpscalerEngine.process_image(
                        image_bytes=contents,
                        scale_type=scale_type,
                        scale_val=scale_val,
                        algorithm=algorithm,
                        remove_bg=remove_bg,
                        face_enhance=face_enhance,
                        denoise_level=denoise_level,
                        auto_hdr=auto_hdr,
                        sharpen_strength=sharpen_strength,
                        output_format=output_format,
                        output_dpi=output_dpi
                    )
                    orig_name = os.path.splitext(file.filename or f"image_{idx}")[0]
                    ext = output_format.lower()
                    if ext == "jpeg":
                        ext = "jpg"
                    out_name = f"{orig_name}_aupscaler_{meta['scale_factor']}x.{ext}"
                    zip_file.writestr(out_name, processed_bytes)

                    file_id = store_file(processed_bytes, out_name, f"image/{ext}")
                    results.append({
                        "filename": out_name,
                        "file_id": file_id,
                        "download_url": f"/api/download/{file_id}",
                        "meta": meta,
                        "status": "success"
                    })
                except Exception as ex:
                    results.append({
                        "filename": file.filename,
                        "status": "failed",
                        "error": str(ex)
                    })

        zip_bytes = zip_buffer.getvalue()
        zip_id = store_file(zip_bytes, "aupscaler_batch.zip", "application/zip")

        return {
            "batch_id": zip_id,
            "zip_download_url": f"/api/download/{zip_id}",
            "total": len(files),
            "processed": len([r for r in results if r.get("status") == "success"]),
            "items": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch processing error: {str(e)}")


@app.get("/api/download/{file_id}")
async def download_file(file_id: str):
    """Streams stored image or zip archive for download."""
    if file_id not in STORAGE:
        raise HTTPException(status_code=404, detail="File not found or session expired")

    entry = STORAGE[file_id]
    return StreamingResponse(
        io.BytesIO(entry["bytes"]),
        media_type=entry["mime"],
        headers={"Content-Disposition": f'attachment; filename="{entry["filename"]}"'}
    )


# Find frontend directory safely in source and PyInstaller frozen bundle
def get_frontend_dir() -> str:
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller temporary extraction folder
        bundled_path = os.path.join(sys._MEIPASS, "frontend")
        if os.path.isdir(bundled_path):
            return bundled_path

    # Standard relative path
    base = os.path.dirname(os.path.abspath(__file__))
    source_path = os.path.abspath(os.path.join(base, "..", "frontend"))
    if os.path.isdir(source_path):
        return source_path
    
    return os.path.abspath("frontend")


frontend_dir = get_frontend_dir()
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
