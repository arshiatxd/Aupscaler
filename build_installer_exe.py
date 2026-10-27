import os
import sys
import shutil
import zipfile
import subprocess

base_dir = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(base_dir, "assets", "icon.ico")
app_dist = os.path.join(base_dir, "dist_app", "aupscaler")

if not os.path.isdir(app_dist):
    app_dist = os.path.join(base_dir, "dist", "aupscaler")

if not os.path.isdir(app_dist):
    print("Building application bundle first via build_exe.py...")
    subprocess.run([sys.executable, os.path.join(base_dir, "build_exe.py")], cwd=base_dir, check=True)
    app_dist = os.path.join(base_dir, "dist_app", "aupscaler")
    if not os.path.isdir(app_dist):
        app_dist = os.path.join(base_dir, "dist", "aupscaler")

zip_payload_path = os.path.join(base_dir, "app_payload.zip")
print("Packaging app payload into compressed zip archive...")
with zipfile.ZipFile(zip_payload_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=4) as zf:
    for root, dirs, files in os.walk(app_dist):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, app_dist)
            zf.write(full, rel)

print(f"Payload zip created: {os.path.getsize(zip_payload_path) / (1024*1024):.2f} MB")

dist_installer_dir = os.path.join(base_dir, "dist_installer")
if os.path.exists(dist_installer_dir):
    shutil.rmtree(dist_installer_dir, ignore_errors=True)

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--name=Aupscaler_Setup",
    "--onefile",
    "--windowed",
    "--clean",
    "--noconfirm",
    f"--distpath={dist_installer_dir}",
    f"--icon={icon_path}",
    f"--add-data={os.path.join(base_dir, 'assets')};assets",
    f"--add-data={zip_payload_path};.",
    "--collect-all=customtkinter",
    "--exclude-module=torch",
    "--exclude-module=cv2",
    "--exclude-module=scipy",
    "--exclude-module=pandas",
    "--exclude-module=matplotlib",
    "--exclude-module=backend",
    "--exclude-module=fastapi",
    "--exclude-module=uvicorn",
    "--exclude-module=starlette",
    "--exclude-module=onnxruntime",
    "--exclude-module=rembg",
    "--exclude-module=numba",
    "--exclude-module=llvmlite",
    "--exclude-module=sqlalchemy",
    "--exclude-module=lxml",
    "installer_wizard.py"
]

print("Running PyInstaller to compile ultra-fast launching Aupscaler_Setup.exe...")
result = subprocess.run(cmd, cwd=base_dir)

if os.path.exists(zip_payload_path):
    os.remove(zip_payload_path)

if result.returncode == 0:
    setup_exe = os.path.join(dist_installer_dir, "Aupscaler_Setup.exe")
    print("Installer build successful:", setup_exe)
    
    desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.isdir(desktop_dir) and os.path.isfile(setup_exe):
        desktop_setup = os.path.join(desktop_dir, "Aupscaler_Setup.exe")
        shutil.copy2(setup_exe, desktop_setup)
        print("Copied Aupscaler_Setup.exe to Desktop:", desktop_setup)
else:
    print("Installer build failed with code:", result.returncode)
