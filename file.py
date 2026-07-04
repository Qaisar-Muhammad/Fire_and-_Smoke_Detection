import os
import cv2
import time
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from PIL import Image, ImageTk
import pygame

# Optional YOLO import
try:
    from ultralytics import YOLO
    MODEL_AVAILABLE = True
except ImportError:
    MODEL_AVAILABLE = False

# ===== CONFIG =====
MODEL_PATH = "best.pt"  # YOLO model path
SNAPSHOT_DIR = "snapshots"
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

pygame.mixer.init()

# ===== LOGIN PAGE =====
class LoginPage:
    def __init__(self, root):
        self.root = root
        self.root.title("Login")
        self.root.geometry("400x300")
        self.root.configure(bg="#121212")

        tk.Label(root, text="Login", font=("Segoe UI", 20, "bold"), fg="#f97316", bg="#121212").pack(pady=20)

        tk.Label(root, text="Username", fg="white", bg="#121212").pack(pady=5)
        self.username_entry = tk.Entry(root, font=("Arial", 12))
        self.username_entry.pack(pady=5)

        tk.Label(root, text="Password", fg="white", bg="#121212").pack(pady=5)
        self.password_entry = tk.Entry(root, font=("Arial", 12), show="*")
        self.password_entry.pack(pady=5)

        tk.Button(root, text="Login", command=self.check_login, bg="#22c55e", fg="white", font=("Arial", 12, "bold")).pack(pady=20)

    def check_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if username == "admin" and password == "admin":
            self.root.destroy()
            main_app = tk.Tk()
            IndustrialFireSmokeGUI(main_app)
            main_app.mainloop()
        else:
            messagebox.showerror("Error", "Invalid credentials")


# ===== INDUSTRIAL GUI =====
class IndustrialFireSmokeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🔥 Industrial Fire & Smoke Monitoring System")
        self.root.geometry("1650x950")
        self.root.configure(bg="#121212")

        # ===== LOAD YOLO MODEL =====
        if MODEL_AVAILABLE and os.path.exists(MODEL_PATH):
            self.model = YOLO(MODEL_PATH)
            print("YOLO model loaded.")
        else:
            self.model = None
            print("YOLO model not found. GUI will still work.")

        # ===== SOUNDS =====
        self.fire_sound_path = "fire_alert.mp3"
        self.smoke_sound_path = "smoke_alert.mp3"

        self.fire_sound = self.load_sound(self.fire_sound_path)
        self.smoke_sound = self.load_sound(self.smoke_sound_path)
        self.current_alarm = None
        self.alarm_enabled = tk.BooleanVar(value=True)

        # ===== STATE =====
        self.cap = None
        self.running = False
        self.fire_count = 0
        self.smoke_count = 0
        self.start_time = time.time()
        self.conf_threshold = tk.DoubleVar(value=0.5)
        self.current_frame_img = None

        # ===== HEADER =====
        header = tk.Frame(root, bg="#1f1f1f", height=70)
        header.pack(fill=tk.X)
        tk.Label(header, text="🔥 INDUSTRIAL FIRE & SMOKE DASHBOARD",
                 fg="#f97316", bg="#1f1f1f", font=("Segoe UI", 20, "bold")).pack(side=tk.LEFT, padx=20)
        self.clock_label = tk.Label(header, fg="#38bdf8", bg="#1f1f1f",
                                    font=("Segoe UI", 14, "bold"))
        self.clock_label.pack(side=tk.RIGHT, padx=20)

        # ===== MAIN =====
        main = tk.Frame(root, bg="#121212")
        main.pack(fill=tk.BOTH, expand=True)

        # Video canvas
        self.canvas = tk.Canvas(main, width=1080, height=720, bg="black", highlightthickness=4,
                                highlightbackground="#0ea5e9")
        self.canvas.pack(side=tk.LEFT, padx=15, pady=15)

        # Side panel
        panel = tk.Frame(main, width=450, bg="#1f1f1f")
        panel.pack(side=tk.RIGHT, fill=tk.Y)

        # Status & Metrics
        self.status_label = tk.Label(panel, text="SYSTEM NORMAL", fg="#22c55e", bg="#1f1f1f",
                                     font=("Arial", 16, "bold"))
        self.status_label.pack(pady=10)

        self.fire_label = tk.Label(panel, text="Fire: 0", fg="#ff4444", bg="#1f1f1f",
                                   font=("Arial", 14, "bold"))
        self.fire_label.pack(pady=5)
        self.smoke_label = tk.Label(panel, text="Smoke: 0", fg="#eab308", bg="#1f1f1f",
                                    font=("Arial", 14, "bold"))
        self.smoke_label.pack(pady=5)
        self.uptime_label = tk.Label(panel, text="Uptime: 00:00:00", fg="#38bdf8", bg="#1f1f1f",
                                     font=("Arial", 14, "bold"))
        self.uptime_label.pack(pady=5)
        self.conf_label = tk.Label(panel, text=f"Confidence: {self.conf_threshold.get():.2f}", fg="#a855f7",
                                   bg="#1f1f1f", font=("Arial", 14, "bold"))
        self.conf_label.pack(pady=5)

        # ===== CONTROLS =====
        tk.Button(panel, text="▶ START CAMERA", bg="#22c55e", fg="white", font=("Arial", 12, "bold"),
                  command=self.start_camera).pack(fill=tk.X, padx=20, pady=5)
        tk.Button(panel, text="📂 LOAD VIDEO", bg="#2563eb", fg="white", font=("Arial", 12, "bold"),
                  command=self.load_video).pack(fill=tk.X, padx=20, pady=5)
        tk.Button(panel, text="🖼 LOAD IMAGE", bg="#8b5cf6", fg="white", font=("Arial", 12, "bold"),
                  command=self.load_image).pack(fill=tk.X, padx=20, pady=5)
        tk.Button(panel, text="■ STOP CAMERA", bg="#ff4444", fg="white", font=("Arial", 12, "bold"),
                  command=self.stop_camera).pack(fill=tk.X, padx=20, pady=5)
        tk.Button(panel, text="📸 SNAPSHOT", bg="#38bdf8", fg="white", font=("Arial", 12, "bold"),
                  command=self.save_snapshot).pack(fill=tk.X, padx=20, pady=5)
        tk.Button(panel, text="🚨 EMERGENCY STOP", bg="#dc2626", fg="white", font=("Arial", 12, "bold"),
                  command=self.emergency_stop).pack(fill=tk.X, padx=20, pady=5)

        tk.Button(panel, text="🔊 Select Fire Alarm (MP3)", bg="#ff6b6b", fg="white",
                  font=("Arial", 12, "bold"), command=self.select_fire_alarm).pack(fill=tk.X, padx=20, pady=5)
        tk.Button(panel, text="🔊 Select Smoke Alarm (MP3)", bg="#facc15", fg="white",
                  font=("Arial", 12, "bold"), command=self.select_smoke_alarm).pack(fill=tk.X, padx=20, pady=5)

        tk.Checkbutton(panel, text="Enable Alarm", variable=self.alarm_enabled, bg="#1f1f1f",
                       fg="white", font=("Arial", 12, "bold")).pack(pady=10)

        tk.Scale(panel, from_=0.1, to=1.0, resolution=0.05, variable=self.conf_threshold,
                 orient=tk.HORIZONTAL, bg="#1f1f1f", fg="white", troughcolor="#38bdf8",
                 label="Confidence Threshold").pack(fill=tk.X, padx=20, pady=10)

        # Logs
        tk.Label(panel, text="Logs:", fg="white", bg="#1f1f1f", font=("Arial", 12, "bold")).pack()
        self.log_text = scrolledtext.ScrolledText(panel, width=45, height=15, bg="#111111",
                                                  fg="#ffffff", font=("Consolas", 10))
        self.log_text.pack(padx=10, pady=10)

        # Start clock & uptime
        self.update_clock()
        self.update_uptime()

    # ===== SOUND SELECTION =====
    def load_sound(self, path):
        if os.path.exists(path):
            return pygame.mixer.Sound(path)
        else:
            class DummySound:
                def play(self, loops=0): pass
                def stop(self): pass
            return DummySound()

    def select_fire_alarm(self):
        path = filedialog.askopenfilename(title="Select Fire Alarm Sound", filetypes=[("MP3 Files", "*.mp3")])
        if path:
            self.fire_sound_path = path
            self.fire_sound = self.load_sound(path)
            self.log(f"Fire alarm set: {path}")

    def select_smoke_alarm(self):
        path = filedialog.askopenfilename(title="Select Smoke Alarm Sound", filetypes=[("MP3 Files", "*.mp3")])
        if path:
            self.smoke_sound_path = path
            self.smoke_sound = self.load_sound(path)
            self.log(f"Smoke alarm set: {path}")

    # ===== CAMERA & VIDEO =====
    def start_camera(self):
        if self.running: return
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.log("Cannot open camera")
            return
        self.running = True
        self.log("Camera started")
        self.update_frame()

    def load_video(self):
        path = filedialog.askopenfilename(title="Select Video File",
                                          filetypes=[("Video Files", "*.mp4 *.avi *.mov")])
        if path:
            self.cap = cv2.VideoCapture(path)
            if not self.cap.isOpened():
                self.log("Cannot open video file")
                return
            self.running = True
            self.log(f"Video loaded: {path}")
            self.update_frame()

    def load_image(self):
        path = filedialog.askopenfilename(title="Select Image",
                                          filetypes=[("Image Files", "*.jpg *.png *.jpeg")])
        if path:
            frame = cv2.imread(path)
            frame = self.detect_fire_smoke(frame)
            self.show_frame(frame)
            self.log(f"Image processed: {path}")

    def stop_camera(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.stop_sounds()
        self.status_label.config(text="SYSTEM NORMAL", fg="#22c55e")
        self.log("Camera stopped")

    def emergency_stop(self):
        self.stop_camera()
        self.status_label.config(text="🚨 EMERGENCY STOP", fg="#dc2626")
        self.log("Emergency stop activated!")

    # ===== FRAME UPDATE =====
    def update_frame(self):
        if not self.running or not self.cap: return
        ret, frame = self.cap.read()
        if ret:
            frame = self.detect_fire_smoke(frame)
            self.show_frame(frame)
        self.root.after(30, self.update_frame)

    # ===== DETECTION =====
    def detect_fire_smoke(self, frame):
        fire_detected = smoke_detected = False
        if self.model:
            results = self.model(frame, verbose=False)[0]
            if results.boxes:
                for box in results.boxes:
                    conf = float(box.conf[0])
                    if conf < self.conf_threshold.get(): continue
                    cls = int(box.cls[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    color = (0,0,255) if cls==0 else (0,255,255)
                    label = f"🔥 FIRE {conf:.2f}" if cls==0 else f"💨 SMOKE {conf:.2f}"
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    self.log(f"{label} detected")
                    if cls==0: fire_detected=True; self.fire_count+=1
                    else: smoke_detected=True; self.smoke_count+=1

        # Update status & alarms
        if fire_detected:
            self.status_label.config(text="🔥 FIRE ALERT", fg="#ff4444")
            self.fire_label.config(text=f"Fire: {self.fire_count}")
            if self.alarm_enabled.get() and self.current_alarm != "fire":
                self.stop_sounds()
                self.fire_sound.play(loops=-1)
                self.current_alarm = "fire"
        elif smoke_detected:
            self.status_label.config(text="💨 SMOKE ALERT", fg="#eab308")
            self.smoke_label.config(text=f"Smoke: {self.smoke_count}")
            if self.alarm_enabled.get() and self.current_alarm != "smoke":
                self.stop_sounds()
                self.smoke_sound.play(loops=-1)
                self.current_alarm = "smoke"
        else:
            self.status_label.config(text="SYSTEM NORMAL", fg="#22c55e")
            self.stop_sounds()

        self.conf_label.config(text=f"Confidence: {self.conf_threshold.get():.2f}")
        return frame

    # ===== UTILITIES =====
    def stop_sounds(self):
        self.fire_sound.stop()
        self.smoke_sound.stop()
        self.current_alarm = None

    def show_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(img)
        self.current_frame_img = imgtk
        self.canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)

    def save_snapshot(self):
        if self.cap:
            ret, frame = self.cap.read()
            if ret:
                filename = os.path.join(SNAPSHOT_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                cv2.imwrite(filename, frame)
                self.log(f"Snapshot saved: {filename}")

    def update_clock(self):
        self.clock_label.config(text=time.strftime("%d %b %Y | %H:%M:%S"))
        self.root.after(1000, self.update_clock)

    def update_uptime(self):
        uptime = time.time() - self.start_time
        self.uptime_label.config(text=f"Uptime: {time.strftime('%H:%M:%S', time.gmtime(uptime))}")
        self.root.after(1000, self.update_uptime)

    def log(self, message):
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)

# ===== RUN LOGIN =====
if __name__ == "__main__":
    root = tk.Tk()
    LoginPage(root)
    root.mainloop()
