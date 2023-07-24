from PIL import Image
import os
import time

# Path to the folder containing the images to be converted
folder_path = "./images"
# Loop through all directories and files within the folder and its subfolders
for root, dirs, files in os.walk(folder_path):
    # Loop through each file in the current directory
    for file_name in files:
        # Check if the file is an image
        if file_name.endswith('.jpg') or file_name.endswith('.jpeg') or file_name.endswith('.png'): 
            # Construct the full path to the image file
            file_path = os.path.join(root, file_name)
            # Open the image file using Pillow
            with Image.open(file_path) as im:
                # Set the output file name and path
                out_file_name = file_name.split('.')[0] + ".webp"
                out_file_path = os.path.join(root, out_file_name)

                # Convert the image to webp format
                im.save(out_file_path, 'webp')
                
                print(f"{file_path} converted to webp format.")