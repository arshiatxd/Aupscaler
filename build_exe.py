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
    dist_app_dir = os.path.join(base_dir, "dist_app")

    if os.path.exists(dist_app_dir):
        shutil.rmtree(dist_app_dir, ignore_errors=True)

    pyinstaller_args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=aupscaler",
        "--onedir",
        "--noconfirm",
        "--clean",
        "--noconsole",
        f"--distpath={dist_app_dir}",
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
        "--exclude-module=matplotlib",
        "--exclude-module=pandas",
        "--exclude-module=sqlalchemy",
        "--exclude-module=lxml",
        "--exclude-module=jinja2",
        "--exclude-module=rich",
        entry_script
    ]

    result = subprocess.run(pyinstaller_args, cwd=base_dir)

    if result.returncode == 0:
        dist_folder = os.path.join(dist_app_dir, "aupscaler")
        dist_exe = os.path.join(dist_folder, "aupscaler.exe")
        print("Build complete at:", dist_exe)

if __name__ == "__main__":
    build_single_exe()
