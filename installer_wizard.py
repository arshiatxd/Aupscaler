import os
import sys
import shutil
import subprocess
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class AupscalerInstaller(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Aupscaler Setup Wizard")
        self.geometry("640x480")
        self.resizable(False, False)
        self.configure(fg_color="#f8fafc")

        self.setup_window_icon()

        self.default_install_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "Programs", "Aupscaler"
        )
        self.selected_dir = self.default_install_dir

        self.create_desktop_shortcut = tk.BooleanVar(value=True)
        self.create_start_menu_shortcut = tk.BooleanVar(value=True)

        self.current_step = 0
        self.steps = ["welcome", "directory", "options", "installing", "finish"]

        self.setup_ui()
        self.show_step("welcome")

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

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_container = ctk.CTkFrame(self, fg_color="#ffffff", corner_radius=0)
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.bottom_bar = ctk.CTkFrame(self, fg_color="#f1f5f9", height=60, corner_radius=0)
        self.bottom_bar.grid(row=1, column=0, sticky="ew", padx=0, pady=0)

        self.btn_cancel = ctk.CTkButton(
            self.bottom_bar, text="Cancel", width=90, height=34,
            fg_color="#ffffff", hover_color="#e2e8f0", text_color="#0f172a",
            border_width=1, border_color="#cbd5e1", corner_radius=8,
            command=self.destroy
        )
        self.btn_cancel.pack(side="right", padx=(6, 16), pady=12)

        self.btn_next = ctk.CTkButton(
            self.bottom_bar, text="Next >", width=100, height=34,
            fg_color="#2563eb", hover_color="#1d4ed8", text_color="#ffffff",
            font=ctk.CTkFont(size=12, weight="bold"), corner_radius=8,
            command=self.next_step
        )
        self.btn_next.pack(side="right", padx=6, pady=12)

        self.btn_back = ctk.CTkButton(
            self.bottom_bar, text="< Back", width=90, height=34,
            fg_color="#ffffff", hover_color="#e2e8f0", text_color="#0f172a",
            border_width=1, border_color="#cbd5e1", corner_radius=8,
            command=self.prev_step, state="disabled"
        )
        self.btn_back.pack(side="right", padx=6, pady=12)

    def clear_container(self):
        for w in self.main_container.winfo_children():
            w.destroy()

    def show_step(self, step_name: str):
        self.clear_container()

        if step_name == "welcome":
            self.btn_back.configure(state="disabled")
            self.btn_next.configure(text="Next >", state="normal")
            self._render_welcome()
        elif step_name == "directory":
            self.btn_back.configure(state="normal")
            self.btn_next.configure(text="Next >", state="normal")
            self._render_directory()
        elif step_name == "options":
            self.btn_back.configure(state="normal")
            self.btn_next.configure(text="Install", state="normal")
            self._render_options()
        elif step_name == "installing":
            self.btn_back.configure(state="disabled")
            self.btn_next.configure(state="disabled")
            self.btn_cancel.configure(state="disabled")
            self._render_installing()
            threading.Thread(target=self._perform_installation, daemon=True).start()
        elif step_name == "finish":
            self.btn_back.configure(state="disabled")
            self.btn_cancel.configure(state="disabled")
            self.btn_next.configure(text="Finish", state="normal", command=self._finish_and_launch)
            self._render_finish()

    def _render_welcome(self):
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.isfile(logo_path):
            try:
                pil_logo = Image.open(logo_path).resize((72, 72), Image.Resampling.LANCZOS)
                self.welcome_logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(72, 72))
                logo_lbl = ctk.CTkLabel(self.main_container, image=self.welcome_logo_img, text="")
                logo_lbl.pack(pady=(36, 12))
            except Exception:
                pass

        title = ctk.CTkLabel(
            self.main_container, text="Welcome to Aupscaler Setup",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#0f172a"
        )
        title.pack(pady=(0, 6))

        sub = ctk.CTkLabel(
            self.main_container,
            text="Deep Learning Super-Resolution & Enhancement Software\n\nThis wizard will guide you through installing Aupscaler on your computer.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#475569", justify="center"
        )
        sub.pack(padx=40, pady=(0, 20))

    def _render_directory(self):
        title = ctk.CTkLabel(
            self.main_container, text="Select Installation Folder",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#0f172a"
        )
        title.pack(anchor="w", padx=36, pady=(32, 6))

        desc = ctk.CTkLabel(
            self.main_container,
            text="Setup will install Aupscaler into the following folder. To install to a different folder, click Browse.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#475569", anchor="w", justify="left"
        )
        desc.pack(fill="x", padx=36, pady=(0, 20))

        dir_box = ctk.CTkFrame(self.main_container, fg_color="#f8fafc", corner_radius=10, border_width=1, border_color="#cbd5e1")
        dir_box.pack(fill="x", padx=36, pady=10)

        self.dir_entry = ctk.CTkEntry(
            dir_box, height=36, fg_color="#ffffff", border_color="#cbd5e1",
            text_color="#0f172a", font=ctk.CTkFont(size=12)
        )
        self.dir_entry.insert(0, self.selected_dir)
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=12, pady=12)

        browse_btn = ctk.CTkButton(
            dir_box, text="Browse...", width=90, height=36,
            fg_color="#e2e8f0", hover_color="#cbd5e1", text_color="#0f172a",
            corner_radius=8, command=self._browse_dir
        )
        browse_btn.pack(side="right", padx=(0, 12), pady=12)

    def _browse_dir(self):
        choice = filedialog.askdirectory(title="Select Destination Folder", initialdir=self.selected_dir)
        if choice:
            self.selected_dir = os.path.abspath(choice)
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, self.selected_dir)

    def _render_options(self):
        title = ctk.CTkLabel(
            self.main_container, text="Select Additional Shortcuts",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#0f172a"
        )
        title.pack(anchor="w", padx=36, pady=(32, 6))

        desc = ctk.CTkLabel(
            self.main_container,
            text="Select which shortcuts you want Setup to create:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#475569", anchor="w"
        )
        desc.pack(fill="x", padx=36, pady=(0, 20))

        opt_frame = ctk.CTkFrame(self.main_container, fg_color="#f8fafc", corner_radius=10, border_width=1, border_color="#cbd5e1")
        opt_frame.pack(fill="x", padx=36, pady=10)

        cb1 = ctk.CTkCheckBox(
            opt_frame, text="Create a Desktop shortcut", variable=self.create_desktop_shortcut,
            font=ctk.CTkFont(size=12), text_color="#0f172a"
        )
        cb1.pack(anchor="w", padx=16, pady=(16, 8))

        cb2 = ctk.CTkCheckBox(
            opt_frame, text="Create a Start Menu program shortcut", variable=self.create_start_menu_shortcut,
            font=ctk.CTkFont(size=12), text_color="#0f172a"
        )
        cb2.pack(anchor="w", padx=16, pady=(8, 16))

    def _render_installing(self):
        title = ctk.CTkLabel(
            self.main_container, text="Installing Aupscaler...",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#0f172a"
        )
        title.pack(anchor="w", padx=36, pady=(36, 12))

        self.install_status_lbl = ctk.CTkLabel(
            self.main_container, text="Preparing installation files...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#475569", anchor="w"
        )
        self.install_status_lbl.pack(fill="x", padx=36, pady=(0, 16))

        self.install_pbar = ctk.CTkProgressBar(
            self.main_container, height=12, corner_radius=6, progress_color="#2563eb"
        )
        self.install_pbar.set(0.1)
        self.install_pbar.pack(fill="x", padx=36, pady=10)

    def _perform_installation(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dist_src = os.path.join(base_dir, "dist", "aupscaler")
        target_dest = self.selected_dir

        try:
            self.after(0, lambda: self._update_pbar(0.2, "Creating directory structure..."))
            os.makedirs(target_dest, exist_ok=True)
            time.sleep(0.3)

            if os.path.isdir(dist_src):
                self.after(0, lambda: self._update_pbar(0.4, "Deploying binary runtime and deep learning neural models..."))
                for item in os.listdir(dist_src):
                    s = os.path.join(dist_src, item)
                    d = os.path.join(target_dest, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
            else:
                self.after(0, lambda: self._update_pbar(0.4, "Copying application modules..."))
                for folder in ["backend", "assets", "models"]:
                    src_f = os.path.join(base_dir, folder)
                    if os.path.isdir(src_f):
                        shutil.copytree(src_f, os.path.join(target_dest, folder), dirs_exist_ok=True)

                for f in ["aupscaler_gui.py", "run.bat", "aupscaler.bat"]:
                    src_file = os.path.join(base_dir, f)
                    if os.path.isfile(src_file):
                        shutil.copy2(src_file, target_dest)

            time.sleep(0.4)
            self.after(0, lambda: self._update_pbar(0.8, "Creating Windows shortcuts..."))

            exe_target = os.path.join(target_dest, "aupscaler.exe")
            if not os.path.isfile(exe_target):
                exe_target = os.path.join(target_dest, "aupscaler.bat")

            icon_target = os.path.join(target_dest, "assets", "icon.ico")
            if not os.path.isfile(icon_target):
                icon_target = exe_target

            if self.create_desktop_shortcut.get():
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                self._create_shortcut(
                    shortcut_path=os.path.join(desktop, "Aupscaler.lnk"),
                    target_path=exe_target,
                    icon_path=icon_target
                )

            if self.create_start_menu_shortcut.get():
                appdata = os.environ.get("APPDATA", "")
                programs = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs")
                if os.path.isdir(programs):
                    self._create_shortcut(
                        shortcut_path=os.path.join(programs, "Aupscaler.lnk"),
                        target_path=exe_target,
                        icon_path=icon_target
                    )

            time.sleep(0.3)
            self.after(0, lambda: self._update_pbar(1.0, "Installation complete!"))
            time.sleep(0.4)
            self.after(0, lambda: self.show_step("finish"))
        except Exception as e:
            self.after(0, lambda err=str(e): messagebox.showerror("Installation Error", f"Failed: {err}"))

    def _update_pbar(self, val: float, text: str):
        self.install_pbar.set(val)
        self.install_status_lbl.configure(text=text)

    def _create_shortcut(self, shortcut_path: str, target_path: str, icon_path: str):
        try:
            ps_cmd = f'''
            $WScriptShell = New-Object -ComObject WScript.Shell
            $Shortcut = $WScriptShell.CreateShortcut("{shortcut_path}")
            $Shortcut.TargetPath = "{target_path}"
            $Shortcut.WorkingDirectory = "{os.path.dirname(target_path)}"
            $Shortcut.IconLocation = "{icon_path}, 0"
            $Shortcut.Save()
            '''
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
        except Exception:
            pass

    def _render_finish(self):
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.isfile(logo_path):
            try:
                pil_logo = Image.open(logo_path).resize((64, 64), Image.Resampling.LANCZOS)
                self.finish_logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(64, 64))
                logo_lbl = ctk.CTkLabel(self.main_container, image=self.finish_logo_img, text="")
                logo_lbl.pack(pady=(36, 12))
            except Exception:
                pass

        title = ctk.CTkLabel(
            self.main_container, text="Aupscaler Installed Successfully!",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#10b981"
        )
        title.pack(pady=(0, 8))

        sub = ctk.CTkLabel(
            self.main_container,
            text=f"Aupscaler has been installed to:\n{self.selected_dir}\n\nClick Finish to launch the application.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#475569", justify="center"
        )
        sub.pack(padx=40, pady=(0, 20))

        self.launch_checkbox = ctk.CTkCheckBox(
            self.main_container, text="Launch Aupscaler now",
            font=ctk.CTkFont(size=12), text_color="#0f172a"
        )
        self.launch_checkbox.select()
        self.launch_checkbox.pack(pady=6)

    def _finish_and_launch(self):
        if hasattr(self, "launch_checkbox") and self.launch_checkbox.get() == 1:
            exe_target = os.path.join(self.selected_dir, "aupscaler.exe")
            if not os.path.isfile(exe_target):
                exe_target = os.path.join(self.selected_dir, "aupscaler.bat")

            if os.path.isfile(exe_target):
                subprocess.Popen([exe_target], cwd=self.selected_dir)

        self.destroy()

    def next_step(self):
        idx = self.steps.index(self.steps[self.current_step])
        if idx < len(self.steps) - 1:
            self.current_step += 1
            self.show_step(self.steps[self.current_step])

    def prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.show_step(self.steps[self.current_step])


if __name__ == "__main__":
    app = AupscalerInstaller()
    app.mainloop()
