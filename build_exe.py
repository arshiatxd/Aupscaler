import os
import sys
import subprocess
import shutil

def build_single_exe():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    entry_script = os.path.join(base_dir, "aupscaler_gui.py")
    icon_path = os.path.join(base_dir, "assets", "icon.ico")
    assets_dir = os.path.join(base_dir, "assets")

    models_dir = os.path.join(base_dir, "models")

    if os.path.exists(os.path.join(base_dir, "dist")):
        shutil.rmtree(os.path.join(base_dir, "dist"), ignore_errors=True)

    pyinstaller_args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=aupscaler",
        "--onedir",
        "--noconfirm",
        "--clean",
        "--noconsole",
        f"--icon={icon_path}",
        f"--add-data={assets_dir};assets",
        f"--add-data={models_dir};models",
        "--collect-all=customtkinter",
        "--hidden-import=windnd",
        "--hidden-import=win32clipboard",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageTk",
        "--hidden-import=PIL.ImageOps",
        "--hidden-import=PIL.ImageDraw",
        "--hidden-import=PIL.ImageGrab",
        "--hidden-import=cv2",
        "--hidden-import=numpy",
        entry_script
    ]

    result = subprocess.run(pyinstaller_args, cwd=base_dir)

    if result.returncode == 0:
        dist_folder = os.path.join(base_dir, "dist", "aupscaler")
        dist_exe = os.path.join(dist_folder, "aupscaler.exe")
        print("Build complete at:", dist_exe)

if __name__ == "__main__":
    build_single_exe()
