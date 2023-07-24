from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from PIL import Image
import os
import concurrent.futures

def browse_folder():
    folder_path = filedialog.askdirectory()
    folder_path_var.set(folder_path)

def convert_and_delete_wrapper(file_path, quality):
    convert_and_delete(file_path, quality)
    progress_bar.step(1)
    
def convert_and_delete(file_path, quality):
    try:
        image = Image.open(file_path)
        filename, file_extension = os.path.splitext(file_path)
        output_file_path = filename + ".webp"
        image.save(output_file_path, "webp", quality=quality, method=6)
        os.remove(file_path)
    except:
        print("Failed to convert file: ", file_path)

def convert_images():
    folder_path = folder_path_var.get()
    quality = quality_slider.get()
    images = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'))]
    num_images = len(images)

    # Disable the convert button while conversion is in progress
    convert_button.config(state=DISABLED)

    # Create a thread pool to process the images
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(convert_and_delete_wrapper, image, quality) for image in images]

        # Wait for all threads to complete before enabling the convert button again
        for future in concurrent.futures.as_completed(futures):
            pass

    # Enable the convert button again now that conversion is complete
    convert_button.config(state=NORMAL)
    print("Image conversion complete.")

def update_quality_label(value):
    # Round the value to the nearest whole number
    rounded_value = round(float(value))
    quality_label.config(text=f"Quality: {rounded_value}")

# Create the GUI window
window = Tk()
window.title("Image Converter")
window.geometry("400x250")

# Create a variable to hold the folder path
folder_path_var = StringVar()

# Create a label to display the folder path
folder_path_label = Label(window, textvariable=folder_path_var)
folder_path_label.pack()

# Create a button to browse for the folder
browse_button = Button(window, text="Browse", command=browse_folder)
browse_button.pack(pady=10)

# Create a label to display the quality
quality_label = Label(window, text="Quality: 80")
quality_label.pack()

# Create a slider to adjust the quality
quality_slider = Scale(window, from_=0, to=100, orient=HORIZONTAL, length=300, command=update_quality_label)
quality_slider.set(80)
quality_slider.pack()

# Create a button to start the image conversion
convert_button = Button(window, text="Convert", command=convert_images)
convert_button.pack(pady=10)

# Start the GUI main loop
window.mainloop()
