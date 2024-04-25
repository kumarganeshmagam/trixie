import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import requests
from datetime import datetime

class ImageInfo:
    def __init__(self, path, size, timestamp):
        self.path = path
        self.size = size
        self.timestamp = timestamp

def upload_file():
    file_path = filedialog.askopenfilename()
    if file_path:
        files = {'image': open(file_path, 'rb')}
        response = requests.post('http://localhost:5000/upload', files=files)
        if response.status_code == 200:
            show_message("File uploaded successfully with custom filename")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            image_info = ImageInfo(file_path, '', timestamp)
            if image_info not in history:
                history.append(image_info)
            show_uploaded_image(image_info)

def show_message(message):
    popup = tk.Toplevel(root)
    popup.title("Upload Result")
    label = tk.Label(popup, text=message, font=("Helvetica", 14))
    label.pack(pady=10)
    ok_button = tk.Button(popup, text="OK", command=popup.destroy, font=("Helvetica", 12))
    ok_button.pack()

def show_uploaded_image(image_info):
    image = Image.open(image_info.path)
    image = image.resize((200, 200), Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(image)
    image_info.size = image.size
    canvas.delete("all")
    canvas.create_image(0, 0, anchor=tk.NW, image=photo)
    canvas.image = photo
    root.geometry(f"500x{image.height + 200}") 

def toggle_history():
    if history_frame.winfo_ismapped():
        history_frame.grid_forget()
        root.geometry(f"500x400")  # Reset window size when history is hidden
        # canvas.delete("all")  # Remove the displayed image
    else:
        update_history_list()
        history_frame.grid(row=3, column=0, columnspan=3, pady=10)
        root.geometry("500x400")  # Increase window size when history is visible

def refresh():
     history_frame.grid_forget()
     canvas.delete("all")
     root.geometry(f"500x200")

def update_history_list():
    history_listbox.delete(0, tk.END)
    for idx, image_info in enumerate(history, start=1):
        history_listbox.insert(tk.END, f"{idx}. Size: {image_info.size[0]}x{image_info.size[1]}, Timestamp: {image_info.timestamp}")

def show_selected_image(event):
    selected_index = history_listbox.curselection()
    if selected_index:
        selected_index = int(selected_index[0])
        selected_image_path = history[selected_index].path
        show_uploaded_image(history[selected_index])

# Tkinter GUI setup
root = tk.Tk()
root.title("File Upload")
root.geometry("500x200")  # Set the initial size of the window
root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(3, weight=1)  # Ensure that the history frame can expand

history = []

upload_button = tk.Button(root, text="Upload File", command=upload_file, font=("Helvetica", 16))
upload_button.grid(row=0, column=0, padx=(10, 5), pady=10)

history_button = tk.Button(root, text="Show History", command=toggle_history, font=("Helvetica", 16))
history_button.grid(row=0, column=1, padx=5, pady=10)

refresh_button = tk.Button(root, text="Refresh", command=refresh, font=("Helvetica", 16))
refresh_button.grid(row=0, column=2, padx=(5, 10), pady=10)

canvas = tk.Canvas(root, width=200, height=200)
canvas.grid(row=1, column=0, columnspan=3, pady=20)

history_frame = tk.Frame(root)

history_listbox = tk.Listbox(history_frame, selectmode=tk.SINGLE, width=40, height=5)
history_listbox.pack(fill=tk.BOTH, expand=True)  # Allow the Listbox to expand

history_scrollbar = tk.Scrollbar(history_frame, orient=tk.VERTICAL)
history_scrollbar.config(command=history_listbox.yview)
history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
history_listbox.config(yscrollcommand=history_scrollbar.set)

history_listbox.bind("<ButtonRelease-1>", show_selected_image)

root.mainloop()
