import os
import tkinter as tk
from tkinter import filedialog, ttk
import sv_ttk
from sys import platform
import fitz  # PyMuPDF
from io import BytesIO
from PIL import Image

class pdfToImageGUI(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        
        self.pdf_file_path = tk.StringVar()  # To store the path of the selected PDF
        sv_ttk.set_theme("dark")
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        
        file_label = ttk.Label(self, text="PDF File:")
        file_label.grid(column=0, row=0, padx=20, pady=20, sticky=tk.W)
        
        file_entry = ttk.Entry(self, width=30, textvariable=self.pdf_file_path)
        file_entry.grid(column=1, row=0, padx=20, pady=20, sticky=tk.W)

        file_button = ttk.Button(self, text="Select PDF", command=self.select_pdf, cursor=cursor_point)
        file_button.grid(column=2, row=0, padx=20, pady=20, sticky=tk.W)

        convert_button = ttk.Button(self, text="Convert PDF to WebP", command=self.convert_pdf_to_webp, cursor=cursor_point)
        convert_button.grid(column=1, row=1, padx=20, pady=20, sticky=tk.W)

    def select_pdf(self):
        file_selected = filedialog.askopenfilename(
            title="Select a PDF file",
            filetypes=(("PDF files", "*.pdf"), ("all files", "*.*"))
        )
        self.pdf_file_path.set(file_selected)

    def convert_pdf_to_webp(self):
        pdf_path = self.pdf_file_path.get()

        # Ensure a PDF is selected
        if not pdf_path or not pdf_path.endswith(".pdf"):
            tk.messagebox.showerror("Error", "Please select a valid PDF file.")
            return

        # Convert the first page of the PDF to an image using PyMuPDF
        pdf_document = fitz.open(pdf_path)
        page = pdf_document[0]
        pixmap = page.get_pixmap()

        # Convert the pixmap to a PIL Image
        pil_image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)

        # Save the PIL Image as WebP
        webp_path = os.path.splitext(pdf_path)[0] + "-thumbnail.webp"
        pil_image.save(webp_path, "WEBP")

        tk.messagebox.showinfo("Success", f"First page of the PDF has been converted to WebP and saved as {webp_path}.")