import tkinter as tk
from tkinter import ttk, messagebox
import re
import sv_ttk
from sys import platform

class TextFormatterGUI(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        
        self.text_to_format = tk.StringVar()
        self.formatted_text = tk.StringVar()
        sv_ttk.set_theme("dark")
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"

        text_field_label = ttk.Label(self, text="Text to format:")
        text_field_label.grid(column=0, row=0, padx=20, pady=20, sticky=tk.W)

        text_field_entry = ttk.Entry(self, width=30, textvariable=self.text_to_format)
        text_field_entry.grid(column=1, row=0, padx=20, pady=20, sticky=tk.W)

        convert_button = ttk.Button(self, text="Convert", command=self.convert_text, cursor=cursor_point)
        convert_button.grid(column=0, row=1, padx=20, pady=20, sticky=tk.W)
        
        self.result_label = ttk.Label(self, text="", wraplength=300)
        self.result_label.grid(column=0, row=2, columnspan=2, padx=20, pady=20, sticky=tk.W)

        copy_button = ttk.Button(self, text="Copy to Clipboard", command=self.copy_to_clipboard, cursor=cursor_point)
        copy_button.grid(column=0, row=3, padx=20, pady=20, sticky=tk.W)

    def convert_text(self):
        text = self.text_to_format.get()
        
        new_text = re.sub(r'[^\w\s-]', '', text)  # Remove special characters
        new_text = new_text.lower()  # Convert to lowercase
        new_text = new_text.replace(' ', '-')  # Replace spaces with hyphens
        new_text = re.sub(r'[-_]+', '-', new_text)  # Remove underscores and multiple hyphens
        new_text = re.sub(r'^-|-$', '', new_text)  # Remove leading and trailing hyphens
        
        self.formatted_text.set(new_text)
        self.result_label.config(text=f"Formatted text: {new_text}")

    def copy_to_clipboard(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.formatted_text.get())
            messagebox.showinfo("Success", "Formatted text copied to clipboard.")
        except tk.TclError:
            messagebox.showerror("Error", "Failed to copy to clipboard. The application window might have been closed.")

def on_closing(root):
    try:
        root.destroy()
    except Exception as e:
        print(f"Error closing the application: {e}")

if __name__ == "__main__":
    try:
        root = tk.Tk()
        root.title("Text Formatter")
        app = TextFormatterGUI(master=root)
        app.grid(column=0, row=0, padx=20, pady=20)
        root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root))
        root.mainloop()
    except Exception as e:
        print(f"Unhandled exception: {e}")
