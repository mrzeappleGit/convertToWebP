import os
import tkinter as tk
from tkinter import filedialog, ttk
# import sv_ttk # No longer setting theme here
from sys import platform
import fitz  # PyMuPDF
from PIL import Image, ImageTk, ImageChops

class pdfToImageGUI(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)

        self.pdf_file_path = tk.StringVar()  # To store the path of the selected PDF
        self.include_margins = tk.BooleanVar(value=True)  # To store the state of the checkbox
        self.preview_image = None  # Placeholder for the preview image

        # sv_ttk.set_theme("dark") # Remove: Theme is managed globally
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"

        # Left side: Input fields and buttons
        input_frame = ttk.Frame(self)
        input_frame.grid(column=0, row=0, padx=20, pady=20, sticky=tk.N)

        file_label = ttk.Label(input_frame, text="PDF File:")
        file_label.grid(column=0, row=0, padx=5, pady=5, sticky=tk.W)

        file_entry = ttk.Entry(input_frame, width=30, textvariable=self.pdf_file_path)
        file_entry.grid(column=1, row=0, padx=5, pady=5, sticky=tk.W)

        file_button = ttk.Button(input_frame, text="Select PDF", command=self.select_pdf, cursor=cursor_point)
        file_button.grid(column=2, row=0, padx=5, pady=5, sticky=tk.W)

        margin_checkbox = ttk.Checkbutton(
            input_frame,
            text="Include Margins",
            variable=self.include_margins,
            cursor=cursor_point,
            command=self.update_preview
        )
        margin_checkbox.grid(column=1, row=1, padx=5, pady=5, sticky=tk.W)

        convert_button = ttk.Button(input_frame, text="Convert PDF", command=self.convert_pdf_to_webp, cursor=cursor_point)
        convert_button.grid(column=1, row=2, padx=5, pady=5, sticky=tk.W)

        # Right side: Preview
        self.preview_label = ttk.Label(self)  # Label to display the preview image
        self.preview_label.grid(column=1, row=0, padx=20, pady=20, sticky=tk.N)

    def select_pdf(self):
        file_selected = filedialog.askopenfilename(
            title="Select a PDF file",
            filetypes=(("PDF files", "*.pdf"), ("all files", "*.*"))
        )
        self.pdf_file_path.set(file_selected)
        self.update_preview()  # Generate preview when a file is selected

    def update_preview(self):
        pdf_path = self.pdf_file_path.get()
        if not pdf_path or not pdf_path.endswith(".pdf"):
            return  # Return if no valid PDF is selected

        # Open the PDF document and get the first page
        pdf_document = fitz.open(pdf_path)
        page = pdf_document[0]

        # Determine desired DPI for the preview image
        desired_dpi = 72  # Lower DPI for a quick preview

        # Calculate the scaling factor based on the desired DPI
        scale_factor = desired_dpi / 72  # PDF default DPI is usually 72

        # Render the entire page using the calculated scale factor
        matrix = fitz.Matrix(scale_factor, scale_factor)
        pixmap = page.get_pixmap(matrix=matrix)

        # Convert the pixmap to a PIL Image
        pil_image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)

        # Check whether to include margins or crop them out
        if not self.include_margins.get():
            pil_image = self.crop_to_content(pil_image)

        # Update the preview
        self.display_preview(pil_image)

    def display_preview(self, image):
        # Resize the image for display (optional: maintain aspect ratio)
        image.thumbnail((300, 400))  # Resize for the preview window
        self.preview_image = ImageTk.PhotoImage(image)

        # Update the label to show the image
        self.preview_label.config(image=self.preview_image)
        self.preview_label.image = self.preview_image

    def convert_pdf_to_webp(self):
        pdf_path = self.pdf_file_path.get()

        # Ensure a PDF is selected
        if not pdf_path or not pdf_path.endswith(".pdf"):
            tk.messagebox.showerror("Error", "Please select a valid PDF file.")
            return

        # Open the PDF document and get the first page
        pdf_document = fitz.open(pdf_path)
        page = pdf_document[0]

        # Determine desired DPI for the output image
        desired_dpi = 150  # Adjust as needed

        # Calculate the scaling factor based on the desired DPI
        scale_factor = desired_dpi / 72  # PDF default DPI is usually 72

        # Render the entire page using the calculated scale factor
        matrix = fitz.Matrix(scale_factor, scale_factor)
        pixmap = page.get_pixmap(matrix=matrix)

        # Convert the pixmap to a PIL Image
        pil_image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)

        # Check whether to include margins or crop them out
        if not self.include_margins.get():
            pil_image = self.crop_to_content(pil_image)

        # Save the PIL Image as WebP
        webp_path = os.path.splitext(pdf_path)[0] + "-thumbnail.webp"
        pil_image.save(webp_path, "WEBP")

        tk.messagebox.showinfo("Success", f"First page of the PDF has been converted to WebP and saved as {webp_path}.")

    def crop_to_content(self, image, threshold=10):
        # Create a background image of the same size with the same background color
        bg = Image.new(image.mode, image.size, image.getpixel((0, 0)))

        # Calculate the difference between the original image and the background
        diff = ImageChops.difference(image, bg)

        # Convert the difference image to grayscale
        diff = diff.convert("L")

        # Apply a threshold to the grayscale difference image
        diff = diff.point(lambda x: 255 if x > threshold else 0)

        # Get the bounding box of the non-background content
        bbox = diff.getbbox()

        if bbox:
            return image.crop(bbox)  # Crop the image to the bounding box

        return image