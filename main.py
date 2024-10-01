import os
from PIL import Image
from pathlib import Path

def log_image_details(image_path: Path, description: str):
    """
    Logs the file size, width, and height of the image.
    
    Args:
        image_path (Path): The path to the image file.
        description (str): Description of the image (e.g., "Original image").
    """
    try:
        file_size = os.path.getsize(image_path) / 1024  # size in KB
        with Image.open(image_path) as img:
            width, height = img.size
        print(f"{description} - {image_path.name}:")
        print(f"  Size: {file_size:.2f} KB, Width: {width}, Height: {height}")
    except Exception as e:
        print(f"Error logging details for {image_path}: {e}")

def optimize_image(image_path: Path):
    """
    Renames the original image, creates an optimized version, and a resized version.
    
    Args:
        image_path (Path): The path to the original image file.
    """
    original_path = image_path
    # Define new original path with '-original' suffix
    new_original_path = image_path.with_name(f"{image_path.stem}-original{image_path.suffix}")
    
    # Rename the original image to include '-original' suffix
    try:
        os.rename(original_path, new_original_path)
        print(f"Renamed {original_path.name} to {new_original_path.name}")
    except FileExistsError:
        print(f"File {new_original_path.name} already exists. Skipping renaming.")
        return
    except Exception as e:
        print(f"Error renaming {original_path.name}: {e}")
        return
    
    # Log original image details
    log_image_details(new_original_path, "Original image")
    
    # Determine image format
    try:
        with Image.open(new_original_path) as img:
            img_format = img.format
    except Exception as e:
        print(f"Error opening {new_original_path}: {e}")
        return
    
    # Prepare optimized image path (original name)
    optimized_path = original_path  # This is the original file name
    
    # Optimize and save the image
    try:
        with Image.open(new_original_path) as img:
            if img_format.upper() == 'JPEG' or img_format.upper() == 'JPG':
                # For JPEG images
                img.save(optimized_path, format='JPEG', optimize=True, progressive=True, quality=70, subsampling=2)
            elif img_format.upper() == 'PNG':
                # For PNG images
                if img.mode in ('RGBA', 'RGB'):
                    img = img.convert('P', palette=Image.ADAPTIVE)
                img.save(optimized_path, format='PNG', optimize=True)
            else:
                # For other formats, save with optimize option
                img.save(optimized_path, optimize=True)
        print(f"Optimized image saved as {optimized_path.name}")
    except Exception as e:
        print(f"Error optimizing {new_original_path}: {e}")
        return
    
    # Log optimized image details
    log_image_details(optimized_path, "Optimized image")
    
    # Resize to 1/8th aspect ratio (reduce both width and height by 1/8th)
    try:
        with Image.open(new_original_path) as img:
            width, height = img.size
            new_size = (max(width // 8, 1), max(height // 8, 1))
            img_resized = img.resize(new_size, Image.LANCZOS)
            
            # Prepare resized image path with '-min' suffix
            resized_path = image_path.with_name(f"{image_path.stem}-min{image_path.suffix}")
            
            # Save the resized image
            if img_format.upper() in ['JPEG', 'JPG']:
                img_resized.save(resized_path, format='JPEG', optimize=True, progressive=True, quality=70, subsampling=2)
            elif img_format.upper() == 'PNG':
                if img_resized.mode in ('RGBA', 'RGB'):
                    img_resized = img_resized.convert('P', palette=Image.ADAPTIVE)
                img_resized.save(resized_path, format='PNG', optimize=True)
            else:
                img_resized.save(resized_path, optimize=True)
            print(f"Resized image saved as {resized_path.name}")
    except Exception as e:
        print(f"Error resizing {new_original_path}: {e}")
        return
    
    # Log resized image details
    log_image_details(resized_path, "Resized image")

def process_directory(directory: Path):
    """
    Processes all images in the given directory and its subdirectories.
    
    Args:
        directory (Path): The path to the directory to process.
    """
    # Traverse through all files and folders recursively
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Check if the file is an image (e.g., JPG, PNG)
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_path = Path(root) / file
                # Skip files that are already renamed with '-original' or '-min'
                if '-original' in image_path.stem or '-min' in image_path.stem:
                    continue
                print(f"\nProcessing image: {image_path}")
                optimize_image(image_path)

if __name__ == "__main__":
    # Input directory to start optimization
    input_dir = input("Enter the directory path: ").strip()
    input_dir_path = Path(input_dir)
    
    if input_dir_path.is_dir():
        process_directory(input_dir_path)
    else:
        print(f"{input_dir} is not a valid directory.")
