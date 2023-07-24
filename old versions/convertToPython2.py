import os
import sys
from PIL import Image
from tqdm import tqdm

# Path to the folder containing the images to be converted
folder_path = "./images"

# Get a list of all image files in the folder and its subdirectories
image_files = []
for dirpath, dirnames, filenames in os.walk(folder_path):
    for filename in filenames:
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_files.append(os.path.join(dirpath, filename))

# Check if there are any image files in the folder
if not image_files:
    print("No image files found in the folder.")
    sys.exit()

# Convert each image file to webp format
for i, image_file in enumerate(tqdm(image_files, desc="Converting images")):
    # Set the output file name and path
    output_file = os.path.splitext(image_file)[0] + ".webp"

    # Convert the image to webp format
    try:
        with Image.open(image_file) as img:
            img.save(output_file, "webp", lossless=True)
    except:
        print(f"Error converting {image_file}")

    # Calculate the percentage of images converted
    progress = (i + 1) / len(image_files) * 100
    tqdm.write(f"Converted {image_file} to webp format ({progress:.2f}% complete)")

print("Conversion complete.")
