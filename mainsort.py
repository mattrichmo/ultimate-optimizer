import os
import sqlite3
import json
import re
import unicodedata
from PIL import Image
from pathlib import Path
from typing import List, Dict

def slugify(value: str) -> str:
    """
    Converts a string to a URL-safe slug.
    
    Args:
        value (str): The string to slugify.
    
    Returns:
        str: The slugified string.
    """
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '-', value)

def log_image_details(image_path: Path, description: str) -> Dict:
    """
    Logs the file size, width, and height of the image.

    Args:
        image_path (Path): The path to the image file.
        description (str): Description of the image (e.g., "Original image").

    Returns:
        Dict: A dictionary containing image details.
    """
    try:
        file_size_kb = os.path.getsize(image_path) / 1024  # size in KB
        with Image.open(image_path) as img:
            width, height = img.size
        print(f"{description} - {image_path.name}:")
        print(f"  Size: {file_size_kb:.2f} KB, Width: {width}, Height: {height}")
        return {
            "description": description,
            "path": f"/{image_path.relative_to(image_path.anchor)}".replace('\\', '/'),
            "size": {
                "w": width,
                "h": height,
                "kb": round(file_size_kb, 2)
            }
        }
    except Exception as e:
        print(f"Error logging details for {image_path}: {e}")
        return {}

def initialize_database(db_path: Path):
    """
    Initializes the SQLite database and creates the images table.

    Args:
        db_path (Path): The path to the SQLite database file.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_name TEXT,
            optimized_name TEXT,
            resized_name TEXT,
            original_size_kb REAL,
            optimized_size_kb REAL,
            resized_size_kb REAL,
            original_width INTEGER,
            original_height INTEGER,
            optimized_width INTEGER,
            optimized_height INTEGER,
            resized_width INTEGER,
            resized_height INTEGER,
            location TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_into_database(db_path: Path, image_data: Dict):
    """
    Inserts image data into the SQLite database.

    Args:
        db_path (Path): The path to the SQLite database file.
        image_data (Dict): A dictionary containing image details.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO images (
            original_name,
            optimized_name,
            resized_name,
            original_size_kb,
            optimized_size_kb,
            resized_size_kb,
            original_width,
            original_height,
            optimized_width,
            optimized_height,
            resized_width,
            resized_height,
            location
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        image_data.get("original_name"),
        image_data.get("optimized_name"),
        image_data.get("resized_name"),
        image_data.get("original_size_kb"),
        image_data.get("optimized_size_kb"),
        image_data.get("resized_size_kb"),
        image_data.get("original_width"),
        image_data.get("original_height"),
        image_data.get("optimized_width"),
        image_data.get("optimized_height"),
        image_data.get("resized_width"),
        image_data.get("resized_height"),
        image_data.get("location")
    ))
    conn.commit()
    conn.close()

def optimize_image(image_path: Path, base_dir: Path, photos_list: List[Dict], db_path: Path):
    """
    Renames the original image, creates an optimized version, and a resized version.
    Also logs details into JSON and SQLite.

    Args:
        image_path (Path): The path to the original image file.
        base_dir (Path): The base directory for calculating relative paths.
        photos_list (List[Dict]): The list to accumulate photo data.
        db_path (Path): The path to the SQLite database file.
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
    original_details = log_image_details(new_original_path, "Original image")

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
            if img_format.upper() in ['JPEG', 'JPG']:
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
    optimized_details = log_image_details(optimized_path, "Optimized image")

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
    resized_details = log_image_details(resized_path, "Resized image")

    # Calculate absolute path relative to the base directory
    try:
        relative_path = image_path.relative_to(base_dir)
        location = f"/{base_dir.name}/" + str(relative_path.parent / image_path.name).replace('\\', '/')
    except ValueError:
        # If image is not under base_dir, use absolute path
        location = str(image_path.resolve()).replace('\\', '/')

    # Prepare data for JSON and SQLite
    image_record = {
        "original": {
            "path": f"/{new_original_path.relative_to(base_dir)}".replace('\\', '/'),
            "size": original_details.get("size", {})
        },
        "optimized": {
            "path": f"/{optimized_path.relative_to(base_dir)}".replace('\\', '/'),
            "size": optimized_details.get("size", {})
        },
        "min": {
            "path": f"/{resized_path.relative_to(base_dir)}".replace('\\', '/'),
            "size": resized_details.get("size", {})
        }
    }

    # Append to photos list
    photos_list.append(image_record)

    # Prepare data for SQLite database
    db_image_record = {
        "original_name": new_original_path.name,
        "optimized_name": optimized_path.name,
        "resized_name": resized_path.name,
        "original_size_kb": original_details.get("size", {}).get("kb"),
        "optimized_size_kb": optimized_details.get("size", {}).get("kb"),
        "resized_size_kb": resized_details.get("size", {}).get("kb"),
        "original_width": original_details.get("size", {}).get("w"),
        "original_height": original_details.get("size", {}).get("h"),
        "optimized_width": optimized_details.get("size", {}).get("w"),
        "optimized_height": optimized_details.get("size", {}).get("h"),
        "resized_width": resized_details.get("size", {}).get("w"),
        "resized_height": resized_details.get("size", {}).get("h"),
        "location": location
    }

    # Insert into SQLite database
    insert_into_database(db_path, db_image_record)

def collect_series(base_dir: Path) -> List[Dict]:
    """
    Collects series information from subdirectories of the base directory.

    Args:
        base_dir (Path): The base directory.

    Returns:
        List[Dict]: A list of series information.
    """
    series_list = []
    for subdir in base_dir.iterdir():
        if subdir.is_dir():
            series_name = subdir.name
            slug = slugify(series_name)
            series_record = {
                "seriesName": series_name,
                "slug": slug,
                "description": f"Description for {series_name}.",
                "intentPurpose": f"Intent purpose for {series_name}.",
                "year": 2024,
                "frontPage": False,
                "keywords": []
            }
            series_list.append(series_record)
    return series_list

def process_directory(directory: Path, base_dir: Path, photos_list: List[Dict], db_path: Path):
    """
    Processes all images in the given directory and its subdirectories.

    Args:
        directory (Path): The path to the directory to process.
        base_dir (Path): The base directory for calculating relative paths.
        photos_list (List[Dict]): The list to accumulate photo data.
        db_path (Path): The path to the SQLite database file.
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
                optimize_image(image_path, base_dir, photos_list, db_path)

def save_photos_json(json_path: Path, photos: List[Dict], series: List[Dict]):
    """
    Saves the collected photo and series data to a JSON file.

    Args:
        json_path (Path): The path to the JSON file.
        photos (List[Dict]): The list of photo records.
        series (List[Dict]): The list of series records.
    """
    data = {
        "photos": photos,
        "series": series
    }
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"\nJSON data saved to {json_path}")
    except Exception as e:
        print(f"Error saving JSON file {json_path}: {e}")

def initialize_database(db_path: Path):
    """
    Initializes the SQLite database and creates the images table.

    Args:
        db_path (Path): The path to the SQLite database file.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_name TEXT,
            optimized_name TEXT,
            resized_name TEXT,
            original_size_kb REAL,
            optimized_size_kb REAL,
            resized_size_kb REAL,
            original_width INTEGER,
            original_height INTEGER,
            optimized_width INTEGER,
            optimized_height INTEGER,
            resized_width INTEGER,
            resized_height INTEGER,
            location TEXT
        )
    """)
    conn.commit()
    conn.close()

def mainsort():
    # Input directory to start optimization
    input_dir = input("Enter the directory path: ").strip()
    input_dir_path = Path(input_dir).resolve()

    if not input_dir_path.is_dir():
        print(f"{input_dir} is not a valid directory.")
        return

    # Define paths for SQLite database and JSON file
    db_path = input_dir_path / "images.db"
    json_path = input_dir_path / "photos.json"

    # Initialize database
    initialize_database(db_path)

    # Initialize photos list
    photos_list = []

    # Process directory
    process_directory(input_dir_path, input_dir_path, photos_list, db_path)

    # Collect series information
    series_list = collect_series(input_dir_path)

    # Save to JSON
    save_photos_json(json_path, photos_list, series_list)

    print("\nProcessing complete.")

if __name__ == "__main__":
    mainsort()
