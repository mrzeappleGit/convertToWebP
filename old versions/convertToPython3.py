import os
import sys
from PIL import Image
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

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

# Convert each image file to webp format using multi-threading, compress the images, and delete the original files
quality = 50  # Set the compression quality
with ThreadPoolExecutor() as executor:
    results = list(tqdm(executor.map(lambda x: convert_and_delete(x, quality), image_files), total=len(image_files), desc="Converting images"))

# Print the results
success_count = results.count(True)
failure_count = results.count(False)
print(f"Conversion complete. Converted {success_count} images and failed to convert/delete {failure_count} images.")