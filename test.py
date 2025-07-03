import tkinter as tk
from tkinter import messagebox, ttk
import cv2
from PIL import Image, ImageTk
import face_recognition
import os
import csv
from datetime import datetime
import numpy as np
import requests
import json
import threading
from urllib.parse import urlencode
import pyautogui
import time
import tkinter.filedialog 

class FaceRecognitionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-Face Recognition with Keyboard Auto-Input")
        self.root.geometry("1100x950")
        self.cap = None
        self.is_camera_running = False
        self.known_encodings = []
        self.known_names = []
        self.last_logged = {}  
        
        # Performance optimization variables
        self.process_this_frame = True 
        self.frame_count = 0
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        
        # Detection statistics
        self.total_faces_detected = 0
        self.current_faces_count = 0
        
        # Keyboard automation settings
        self.keyboard_settings = {
            'enabled': False,
            'auto_type_name': True,
            'auto_type_timestamp': False,
            'add_enter': True,
            'add_tab': False,
            'delay_seconds': 3,
            'format_template': '{name}', 
            'target_window': ''  
        }
        
        
        # Create GUI elements first
        self.create_gui()
        self.load_configs()
        self.load_known_faces()
        self.start_camera()

    def upload_image(self):
        """Allow user to upload an image and recognize faces in it."""
        file_path = tkinter.filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png")]
        )
        if not file_path:
            return

        try:
            image = face_recognition.load_image_file(file_path)
            face_locations = face_recognition.face_locations(image)
            face_encodings = face_recognition.face_encodings(image, face_locations)

            if not face_encodings:
                messagebox.showinfo("Result", "No faces detected in the selected image.")
                return

            # Draw rectangles and names on the image
            image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                matches = face_recognition.compare_faces(self.known_encodings, face_encoding, tolerance=0.5)
                name = "Unknown"
                if True in matches:
                    face_distances = face_recognition.face_distance(self.known_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index] and face_distances[best_match_index] < 0.6:
                        name = self.known_names[best_match_index]
                cv2.rectangle(image_bgr, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(image_bgr, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # Show the result in a new window
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(image_rgb)
            img.thumbnail((600, 600))
            photo = ImageTk.PhotoImage(img)

            top_window = tk.Toplevel(self.root)
            top_window.title("Recognition Result")
            label = tk.Label(top_window, image=photo)
            label.image = photo
            label.pack()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process image: {e}")
    
    def load_known_faces(self):
        """Load known faces from the known_people folder including subfolders"""
        known_people_folder = "./known_people"
        if not os.path.exists(known_people_folder):
            os.makedirs(known_people_folder)
            messagebox.showwarning("Warning", f"Created '{known_people_folder}' folder. Please add known face images there.")
            return
        
        self.known_encodings = []
        self.known_names = []
        
        for root_dir, dirs, files in os.walk(known_people_folder):
            for filename in files:
                if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    image_path = os.path.join(root_dir, filename)
                    try:
                        image = face_recognition.load_image_file(image_path)
                        encodings = face_recognition.face_encodings(image)
                        if encodings:
                            for i, encoding in enumerate(encodings):
                                self.known_encodings.append(encoding)
                                # Extract name from folder structure or filename
                                relative_path = os.path.relpath(root_dir, known_people_folder)
                                name = os.path.splitext(filename)[0]
                                if relative_path != ".":
                                    name = f"{relative_path}"
                                if len(encodings) > 1:
                                    name = f"{name}_{i+1}"
                                self.known_names.append(name)
                                print(f"Loaded face: {name}")
                        else:
                            print(f"Warning: No face detected in {filename}")
                    except Exception as e:
                        print(f"Error loading {filename}: {e}")
        
        print(f"Loaded {len(self.known_encodings)} known faces")
        if len(self.known_encodings) == 0:
            messagebox.showwarning("Warning", "No valid face images found in 'known_people' folder!")
        
        if hasattr(self, 'faces_count_label'):
            self.update_status()
    
    def create_gui(self):
        """Create the GUI elements"""
        title_label = tk.Label(self.root, text="Face Recognition with Keyboard Auto-Input", 
                              font=("Arial", 18, "bold"))
        title_label.pack(pady=10)
        
        # Video display label
        self.video_label = tk.Label(self.root, bg="black")
        self.video_label.pack(pady=10)

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        # Start/Stop camera button
        self.camera_button = tk.Button(button_frame, text="Stop Camera", 
                                      command=self.toggle_camera,
                                      bg="red", fg="white", font=("Arial", 12))
        self.camera_button.pack(side=tk.LEFT, padx=5)

        reload_button = tk.Button(button_frame, text="Reload Known Faces", 
                                 command=self.load_known_faces,
                                 bg="blue", fg="white", font=("Arial", 12))
        reload_button.pack(side=tk.LEFT, padx=5)
        
        # Keyboard settings button
        keyboard_button = tk.Button(button_frame, text="Keyboard Settings", 
                                   command=self.open_keyboard_config,
                                   bg="orange", fg="white", font=("Arial", 12))
        keyboard_button.pack(side=tk.LEFT, padx=5)

        # Status information frame
        status_frame = tk.Frame(self.root)
        status_frame.pack(pady=5)
        
        self.status_label = tk.Label(status_frame, text="Camera: Running", 
                                    font=("Arial", 10), fg="green")
        self.status_label.pack()

        self.faces_count_label = tk.Label(status_frame, text="Known faces: 0", 
                                         font=("Arial", 10), fg="blue")
        self.faces_count_label.pack()
        
        self.current_faces_label = tk.Label(status_frame, text="Current faces detected: 0", 
                                           font=("Arial", 10), fg="orange")
        self.current_faces_label.pack()
        
        self.keyboard_status_label = tk.Label(status_frame, text="Keyboard Auto-Input: Disabled", 
                                            font=("Arial", 10), fg="gray")
        self.keyboard_status_label.pack()

        instructions = tk.Label(self.root, 
                               text="✓ Place known face images in the 'known_people' folder or subfolders\n✓ Configure keyboard auto-input to automatically type data when face is recognized\n✓ Multiple faces will be detected simultaneously\n✓ Use clear, front-facing photos with good lighting for best results",
                               font=("Arial", 10), fg="gray", justify="left")
        instructions.pack(pady=5)
        upload_button = tk.Button(button_frame, text="Upload Image",
                                  command=self.upload_image,
                                  bg="purple", fg="white", font=("Arial", 12))
        upload_button.pack(side=tk.LEFT, padx=5)
    
    def update_status(self):
        """Update the status information"""
        self.faces_count_label.config(text=f"Known faces: {len(self.known_encodings)}")
        self.current_faces_label.config(text=f"Current faces detected: {self.current_faces_count}")
        
        # Update keyboard status
        if self.keyboard_settings['enabled']:
            self.keyboard_status_label.config(text="Keyboard Auto-Input: Enabled", fg="green")
        else:
            self.keyboard_status_label.config(text="Keyboard Auto-Input: Disabled", fg="gray")
    
    def start_camera(self):
        """Start the webcam"""
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                messagebox.showerror("Error", "Could not open webcam")
                return
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            self.is_camera_running = True
            self.camera_button.config(text="Stop Camera", bg="red")
            self.status_label.config(text="Camera: Running", fg="green")
            self.update_frame()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start camera: {e}")
    
    def stop_camera(self):
        """Stop the webcam"""
        self.is_camera_running = False
        if self.cap:
            self.cap.release()
        self.camera_button.config(text="Start Camera", bg="green")
        self.status_label.config(text="Camera: Stopped", fg="red")
        self.current_faces_count = 0
        self.update_status()
        self.video_label.config(image="")
        self.video_label.image = None
    
    def toggle_camera(self):
        """Toggle camera on/off"""
        if self.is_camera_running:
            self.stop_camera()
        else:
            self.start_camera()
    
    def get_face_color(self, index, is_known=False):
        """Get a unique color for each face"""
        if is_known:
            colors = [(0, 255, 0), (0, 200, 50), (50, 255, 50), (0, 255, 100), (100, 255, 0)]
        else:
            colors = [(0, 0, 255), (50, 0, 200), (100, 0, 255), (0, 50, 255), (200, 0, 100)]
        
        return colors[index % len(colors)]
    
    def update_frame(self):
        """Update the video frame with enhanced multi-face processing"""
        if not self.is_camera_running or not self.cap:
            return
        
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            
            if self.frame_count % 3 == 0:
                small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                
                self.face_locations = face_recognition.face_locations(rgb_small_frame, 
                                                                    model="hog", 
                                                                    number_of_times_to_upsample=1)
                self.face_encodings = face_recognition.face_encodings(rgb_small_frame, self.face_locations)
                
                self.current_faces_count = len(self.face_locations)
                
                self.face_names = []
                for face_encoding in self.face_encodings:
                    matches = face_recognition.compare_faces(self.known_encodings, face_encoding, tolerance=0.5)
                    name = "Unknown"
                    confidence = 0
                    
                    if True in matches:
                        face_distances = face_recognition.face_distance(self.known_encodings, face_encoding)
                        best_match_index = np.argmin(face_distances)
                        
                        if matches[best_match_index] and face_distances[best_match_index] < 0.6:
                            name = self.known_names[best_match_index]
                            confidence = 1 - face_distances[best_match_index]
                            self.log_match_with_cooldown(name)
                    
                    self.face_names.append((name, confidence))
                
                self.update_status()
            
            # Display results
            for i, ((top, right, bottom, left), (name, confidence)) in enumerate(zip(self.face_locations, self.face_names)):
                top *= 2
                right *= 2
                bottom *= 2
                left *= 2
                
                # Always use red for unknown faces, other colors for known faces
                if name == "Unknown":
                    color = (0, 0, 255)  # Red for unknown faces
                else:
                    color = self.get_face_color(i, is_known=True)  # Other colors for known faces
                
                cv2.rectangle(frame, (left, top), (right, bottom), color, 3)
                
                label_height = 40
                cv2.rectangle(frame, (left, bottom - label_height), (right, bottom), color, cv2.FILLED)
                
                display_text = f"{name}"
                if name != "Unknown" and confidence > 0:
                    display_text = f"{name} ({confidence:.2f})"
                
                if len(self.face_locations) > 1:
                    display_text = f"#{i+1} {display_text}"
                
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, display_text, (left + 6, bottom - 10), font, 0.6, (255, 255, 255), 2)
                cv2.putText(frame, display_text, (left + 6, bottom - 10), font, 0.6, (0, 0, 0), 1)
            
            if self.current_faces_count > 0:
                count_text = f"Faces: {self.current_faces_count}"
                cv2.putText(frame, count_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3)
                cv2.putText(frame, count_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            
            if self.keyboard_settings['enabled']:
                status_text = "Keyboard: ON"
                cv2.putText(frame, status_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)
            photo = ImageTk.PhotoImage(image=img)
            
            self.video_label.config(image=photo)
            self.video_label.image = photo
            
            self.frame_count += 1
        
        if self.is_camera_running:
            self.root.after(33, self.update_frame)
    
    def log_match_with_cooldown(self, name):
        """Log a match with cooldown to prevent spam logging"""
        current_time = datetime.now()
        
        if name in self.last_logged:
            time_diff = (current_time - self.last_logged[name]).total_seconds()
            if time_diff < 30:
                return
        
        self.log_match(name)
        self.last_logged[name] = current_time
        
        # Trigger keyboard auto-input if enabled
        if self.keyboard_settings['enabled']:
            self.auto_type_data(name, current_time)
    
    def auto_type_data(self, name, timestamp):
        """Automatically type data to keyboard"""
        def type_data():
            try:
                # Wait for the specified delay
                time.sleep(self.keyboard_settings['delay_seconds'])
                
                # Prepare the data to type
                now = timestamp
                date_str = now.strftime('%Y-%m-%d')
                time_str = now.strftime('%H:%M:%S')
                timestamp_str = now.strftime('%Y-%m-%d %H:%M:%S')
                
                # Format the text according to template
                text_to_type = self.keyboard_settings['format_template'].format(
                    name=name,
                    timestamp=timestamp_str,
                    date=date_str,
                    time=time_str
                )
                
                # Type the text
                pyautogui.typewrite(text_to_type, interval=0.05)
                
                # Add additional keys if configured
                if self.keyboard_settings['add_tab']:
                    pyautogui.press('tab')
                
                if self.keyboard_settings['add_enter']:
                    pyautogui.press('enter')
                
                print(f"Auto-typed: {text_to_type}")
                
            except Exception as e:
                print(f"Error in auto-typing: {e}")
        
        # Run in background thread
        thread = threading.Thread(target=type_data)
        thread.daemon = True
        thread.start()
    
    def open_keyboard_config(self):
        """Open keyboard configuration dialog"""
        config_window = tk.Toplevel(self.root)
        config_window.title("Keyboard Auto-Input Settings")
        config_window.geometry("500x600")
        config_window.resizable(False, False)
        
        config_window.transient(self.root)
        config_window.grab_set()
        
        # Center the window
        config_window.update_idletasks()
        x = (config_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (config_window.winfo_screenheight() // 2) - (600 // 2)
        config_window.geometry(f"500x600+{x}+{y}")
        
        tk.Label(config_window, text="Keyboard Auto-Input Settings", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Enable checkbox
        enable_var = tk.BooleanVar(value=self.keyboard_settings.get('enabled', False))
        tk.Checkbutton(config_window, text="Enable Keyboard Auto-Input", 
                      variable=enable_var, font=("Arial", 12)).pack(pady=10)
        
        # Delay setting
        tk.Label(config_window, text="Delay before typing (seconds):").pack(anchor='w', padx=20)
        delay_var = tk.DoubleVar(value=self.keyboard_settings.get('delay_seconds', 3))
        delay_spinbox = tk.Spinbox(config_window, from_=0.5, to=10.0, increment=0.5, 
                                  textvariable=delay_var, width=10)
        delay_spinbox.pack(pady=5)
        
        # Format template
        tk.Label(config_window, text="Text Format Template:").pack(anchor='w', padx=20, pady=(20,0))
        tk.Label(config_window, text="Available variables: {name}, {timestamp}, {date}, {time}", 
                font=("Arial", 9), fg="gray").pack(anchor='w', padx=20)
        
        format_var = tk.StringVar(value=self.keyboard_settings.get('format_template', '{name}'))
        format_entry = tk.Entry(config_window, textvariable=format_var, width=50)
        format_entry.pack(pady=5, padx=20)
        
        # Additional options
        options_frame = tk.Frame(config_window)
        options_frame.pack(pady=20)
        
        add_enter_var = tk.BooleanVar(value=self.keyboard_settings.get('add_enter', True))
        tk.Checkbutton(options_frame, text="Press Enter after typing", 
                      variable=add_enter_var).pack(anchor='w')
        
        add_tab_var = tk.BooleanVar(value=self.keyboard_settings.get('add_tab', False))
        tk.Checkbutton(options_frame, text="Press Tab after typing", 
                      variable=add_tab_var).pack(anchor='w')
        
        # Preview section
        preview_frame = tk.Frame(config_window)
        preview_frame.pack(pady=20, padx=20, fill='x')
        
        tk.Label(preview_frame, text="Preview:", font=("Arial", 10, "bold")).pack(anchor='w')
        preview_label = tk.Label(preview_frame, text="", font=("Arial", 10), 
                               bg="lightgray", relief="sunken", height=2)
        preview_label.pack(fill='x', pady=5)
        
        def update_preview():
            try:
                sample_name = "John_Doe"
                now = datetime.now()
                preview_text = format_var.get().format(
                    name=sample_name,
                    timestamp=now.strftime('%Y-%m-%d %H:%M:%S'),
                    date=now.strftime('%Y-%m-%d'),
                    time=now.strftime('%H:%M:%S')
                )
                preview_label.config(text=f"Example output: {preview_text}")
            except Exception as e:
                preview_label.config(text=f"Format error: {str(e)}")
        
        format_entry.bind('<KeyRelease>', lambda e: update_preview())
        update_preview()
        
        # Test button
        def test_typing():
            if messagebox.askyesno("Test Typing", 
                                  "This will type the preview text after the delay. "
                                  "Make sure you have a text field ready (like Notepad).\n\n"
                                  "Click Yes to continue, then quickly click on your target application."):
                test_name = "Test_User"
                test_time = datetime.now()
                
                # Temporarily update settings for test
                temp_settings = self.keyboard_settings.copy()
                temp_settings.update({
                    'enabled': True,
                    'delay_seconds': delay_var.get(),
                    'format_template': format_var.get(),
                    'add_enter': add_enter_var.get(),
                    'add_tab': add_tab_var.get()
                })
                
                def test_type():
                    try:
                        time.sleep(temp_settings['delay_seconds'])
                        text_to_type = temp_settings['format_template'].format(
                            name=test_name,
                            timestamp=test_time.strftime('%Y-%m-%d %H:%M:%S'),
                            date=test_time.strftime('%Y-%m-%d'),
                            time=test_time.strftime('%H:%M:%S')
                        )
                        pyautogui.typewrite(text_to_type, interval=0.05)
                        if temp_settings['add_tab']:
                            pyautogui.press('tab')
                        if temp_settings['add_enter']:
                            pyautogui.press('enter')
                    except Exception as e:
                        print(f"Test typing error: {e}")
                
                thread = threading.Thread(target=test_type)
                thread.daemon = True
                thread.start()
        
        tk.Button(config_window, text="Test Typing", command=test_typing, 
                 bg="orange", fg="white").pack(pady=10)
        
        # Buttons
        button_frame = tk.Frame(config_window)
        button_frame.pack(pady=20)
        
        def save_keyboard_config():
            try:
                # Validate format template
                test_format = format_var.get().format(
                    name="test", timestamp="test", date="test", time="test"
                )
                
                self.keyboard_settings.update({
                    'enabled': enable_var.get(),
                    'delay_seconds': delay_var.get(),
                    'format_template': format_var.get(),
                    'add_enter': add_enter_var.get(),
                    'add_tab': add_tab_var.get()
                })
                self.save_configs()
                self.update_status()
                config_window.destroy()
                messagebox.showinfo("Success", "Keyboard settings saved!")
            except Exception as e:
                messagebox.showerror("Error", f"Invalid format template: {str(e)}")
        
        tk.Button(button_frame, text="Save", command=save_keyboard_config, 
                 bg="green", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=config_window.destroy, 
                 bg="red", fg="white").pack(side=tk.LEFT, padx=5)
        
        # Instructions
        instructions = tk.Label(config_window, 
                               text="Instructions:\n• Enable auto-input to type data when faces are recognized\n• Set delay to give time to focus on target application\n• Use format template to customize output\n• Test the settings before saving",
                               font=("Arial", 9), fg="gray", justify="left")
        instructions.pack(pady=10, padx=20)
    
    def log_match(self, name):
        """Log the matched person and timestamp to CSV"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_data = [name, timestamp]
        
        # Log to CSV file
        log_file = 'Attendance_log.csv'
        file_exists = os.path.isfile(log_file)
        
        try:
            with open(log_file, mode='a', newline='') as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow(['Name', 'Timestamp'])
                writer.writerow(log_data)
                print(f"Logged to CSV: {name} at {timestamp}")
        except Exception as e:
            print(f"Error logging to CSV: {e}")
    
    def load_configs(self):
        """Load all configurations"""
      
        # Load keyboard config
        keyboard_file = 'keyboard_config.json'
        if os.path.exists(keyboard_file):
            try:
                with open(keyboard_file, 'r') as f:
                    self.keyboard_settings.update(json.load(f))
            except Exception as e:
                print(f"Error loading keyboard config: {e}")
    
    def save_configs(self):
        """Save all configurations"""

        # Save keyboard config
        try:
            with open('keyboard_config.json', 'w') as f:
                json.dump(self.keyboard_settings, f, indent=2)
        except Exception as e:
            print(f"Error saving keyboard config: {e}")
    
    def on_closing(self):
        """Handle window closing"""
        self.stop_camera()
        self.root.destroy()

if __name__ == "__main__":
    try:
        import pyautogui
    except ImportError:
        print("Installing pyautogui...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui"])
        import pyautogui

    pyautogui.FAILSAFE = True  
    pyautogui.PAUSE = 0.1    
    
    root = tk.Tk()
    app = FaceRecognitionApp(root)
    
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
