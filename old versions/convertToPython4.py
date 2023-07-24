import os
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
from PIL import Image
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

# Function to convert and delete an image
def convert_and_delete(image_file, quality):
    # Set the output file name and path
    output_file = os.path.splitext(image_file)[0] + ".webp"

    # Convert the image to webp format with the specified quality
    try:
        with Image.open(image_file) as img:
            img.save(output_file, "webp", quality=quality, lossless=True)
    except:
        print(f"Error converting {image_file}")
        return False

    # Delete the original file
    try:
        os.remove(image_file)
    except:
        print(f"Error deleting {image_file}")
        return False

    return True

# Function to convert all images in a folder to webp format, compress them, and delete the original files
def convert_images():
    # Get the path of the folder containing the images
    folder_path = filedialog.askdirectory()

    # Check if a folder was selected
    if not folder_path:
        return

    # Get a list of all image files in the folder and its subdirectories
    image_files = []
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_files.append(os.path.join(dirpath, filename))

    # Check if there are any image files in the folder
    if not image_files:
        print("No image files found in the folder.")
        return

    # Convert each image file to webp format using multi-threading, compress the images, and delete the original files
    quality = quality_slider.get()  # Get the selected compression quality
    with ThreadPoolExecutor() as executor:
        results = list(tqdm(executor.map(lambda x: convert_and_delete(x, quality), image_files), total=len(image_files), desc="Converting images"))

    # Print the results
    success_count = results.count(True)
    failure_count = results.count(False)
    print(f"Conversion complete. Converted {success_count} images and failed to convert/delete {failure_count} images.")

# Create a GUI window
window = Tk()
window.title("Image Converter")

# Create a button to select the folder containing the images
select_button = Button(window, text="Select Folder", command=convert_images)
select_button.pack(pady=10)

# Create a slider to select the compression quality
quality_label = StringVar()
quality_value = DoubleVar()
def set_label(val):
    
    quality_label.set("Compression Quality: {}".format(quality_value))

firstLine = Frame(window)
firstLine.pack()
quality = Label(firstLine, textvariable=quality_label)
quality.pack(side=LEFT)
quality_slider = ttk.Scale(window, from_=0, to=100, variable=quality_value, orient=HORIZONTAL, command=set_label)
quality_slider.set(80)
quality_slider.pack()

# Run the GUI window
window.mainloop()
