#!/usr/bin/env python3

# Configuration - Edit these paths as needed
INBOX_PATH = "~/inbox"  # Source directory containing files to organize
VAULT_PATH = "~/digital_vault"  # Destination directory for organized files

# File category definitions
FILE_CATEGORIES = {
    'photos/raw': ['.nef', '.arw', '.cr2', '.cr3', '.raw', '.dng'],  # Raw photo formats
    'photos/jpg': ['.jpg', '.jpeg', '.heic'],  # Standard photo formats
    'images': ['.ico', '.icns', '.svg', '.gif', '.bmp', '.tiff', '.webp'],  # Other image formats
    'images/screenshots': ['.png'],  # Screenshots and screen captures
    'videos': ['.mp4', '.mov', '.avi', '.mpg', '.mpeg', '.m4v', '.wmv', '.flv', '.webm', '.scc'],
    'audio/music': ['.mp3', '.m4a', '.flac', '.wav', '.aac', '.ogg', '.wma'],  # Music files
    'audio/recordings': ['.mp3', '.m4a', '.wav', '.aac'],  # Personal audio recordings
    'documents/ebooks': ['.pdf', '.epub', '.mobi','.chm'],  # Ebook formats
    'documents/notes': ['.txt', '.md', '.markdown', '.rst'],  # Text and markdown files
    'documents/mindmaps': ['.mm'],  # Mind map files
    'documents/bookmarks': ['.html', '.htm'],  # Bookmark files
    'documents/general': [
        '.pdf', '.doc', '.docx', '.rtf', '.odt', 
        '.pages', '.xlsx', '.xls', '.numbers', '.key'
    ],
    'dev': [
        # Shell and script files
        '.sh', '.bash', '.zsh', '.fish', 
        # Python files
        '.py', '.pyw', '.ipynb',
        # Web development
        '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.scss', '.sass',
        # Configuration files
        '.yml', '.yaml', '.json', '.xml', '.ini', '.conf', '.config',
        # Other script types
        '.pl', '.rb', '.php', '.lua',
        # AppleScript
        '.scpt', '.applescript'
    ],
    'calendars': ['.ics'],  # Calendar files
    'secrets': [
        '.pem', '.pub', '.ssh',  # SSH and encryption keys
        'id_rsa', 'id_ed25519', 'known_hosts',  # SSH specific files
        '.kdb', '.kdbx'  # KeePass database files
    ],
    'archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
    'fonts': [
        '.ttf',    # TrueType fonts
        '.otf',    # OpenType fonts
        '.woff',   # Web Open Font Format
        '.woff2',  # Web Open Font Format 2
        '.eot',    # Embedded OpenType fonts
        '.pfm',    # Printer Font Metrics
        '.pfb',    # Printer Font Binary
        '.fon',    # Legacy Windows font format
    ],
    'other': []  # Default category for unmatched files
}

# Audio metadata fields that indicate the file is likely a music track
MUSIC_METADATA_FIELDS = ['Artist', 'Album', 'Genre', 'TrackNumber']

# Common ebook creator software and keywords
EBOOK_CREATORS = [
    'calibre', 'adobe digital editions', 'kindle', 'ibooks', 'google books',
    'pdf-xchange', 'adobe indesign', 'quartz', 'prince'
]

# Minimum page count to consider a PDF as potentially being an ebook
MIN_EBOOK_PAGES = 10

# Common timestamp patterns to detect in filenames
TIMESTAMP_PATTERNS = [
    # Patterns with dashes
    r'\d{8}-\d{6}',          # 20241208-082255
    r'\d{4}-\d{2}-\d{2}-\d{6}',  # 2024-12-08-082255
    
    # Patterns with underscores
    r'\d{8}_\d{6}',          # 20241208_082255
    r'\d{4}_\d{2}_\d{2}_\d{6}',  # 2024_12_08_082255
    
    # Mixed patterns (common in various devices)
    r'\d{4}-\d{2}-\d{2}_\d{6}',  # 2024-12-08_082255
    r'\d{4}_\d{2}_\d{2}-\d{6}',  # 2024_12_08-082255
    
    # Patterns with basic date validation
    r'\d{4}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])[-_]\d{6}',  # YYYYMMDD-/_ HHMMSS
    r'\d{4}[-_](?:0[1-9]|1[0-2])[-_](?:0[1-9]|[12]\d|3[01])[-_]\d{6}'  # YYYY-/_MM-/_DD-/_HHMMSS
]

import os
import subprocess
import json
from datetime import datetime
from pathlib import Path
import shutil
import re
import zipfile
import argparse

class DigitalVaultOrganizer:
    def __init__(self, inbox_path, vault_path):
        self.inbox_path = Path(inbox_path).expanduser().resolve()
        self.vault_path = Path(vault_path).expanduser().resolve()
        
        if not self.inbox_path.exists():
            raise ValueError(f"Inbox path does not exist: {self.inbox_path}")
        
        # Create vault directory if it doesn't exist
        self.vault_path.mkdir(parents=True, exist_ok=True)

    def get_file_datetime(self, file_path):
        """Get the datetime from a file's metadata or name."""
        file_path = Path(file_path)
        
        try:
            # Check if the filename contains a timestamp (e.g., name_20120212-115330.zip)
            timestamp_match = re.search(r'_(\d{8}-\d{6})\.', file_path.name)
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)
                try:
                    return datetime.strptime(timestamp_str, '%Y%m%d-%H%M%S')
                except ValueError:
                    pass  # If parsing fails, continue with other methods
            
            # Use file's modification time
            return datetime.fromtimestamp(file_path.stat().st_mtime)
            
        except Exception as e:
            print(f"Error getting file datetime for {file_path}: {e}")
            return datetime.now()  # Fallback to current time if all else fails

    def has_timestamp(self, filename):
        """Check if the filename already contains a valid timestamp."""
        for pattern in TIMESTAMP_PATTERNS:
            if re.search(pattern, filename):
                return True
        return False

    def generate_new_filename(self, original_path, file_datetime):
        """Generate new filename with timestamp while preserving original name and extension."""
        stem = original_path.stem
        suffix = original_path.suffix
        
        # Replace spaces with dashes in the filename
        stem = stem.replace(' ', '-')
        
        # Check if the filename already contains a timestamp
        if self.has_timestamp(stem):
            return f"{stem}{suffix}"
        
        # Format timestamp with dash between date and time
        timestamp = file_datetime.strftime('%Y%m%d-%H%M%S')
        
        # Use underscore to separate original name from timestamp
        return f"{stem}_{timestamp}{suffix}"

    def is_music_file(self, file_path):
        """
        Determine if an audio file is likely a music track based on its metadata.
        Returns True if the file appears to be music, False if it's likely a personal recording.
        """
        try:
            result = subprocess.run(
                ['exiftool', '-json', '-Artist', '-Album', '-Genre', '-TrackNumber', str(file_path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                metadata = json.loads(result.stdout)[0]
                
                # Count how many music-related metadata fields are present and non-empty
                music_fields_present = sum(
                    1 for field in MUSIC_METADATA_FIELDS
                    if field in metadata and metadata[field] and str(metadata[field]).strip()
                )
                
                # If at least 2 music-related fields are present, consider it a music file
                return music_fields_present >= 2
            
            return False  # If exiftool fails, assume it's not a music file
            
        except Exception as e:
            print(f"Error checking audio metadata for {file_path}: {e}")
            return False

    def is_screenshot(self, file_path):
        """
        Determine if a PNG file is likely a screenshot based on metadata and filename.
        
        Args:
            file_path (Path): Path to the PNG file
            
        Returns:
            bool: True if the file is likely a screenshot, False otherwise
        """
        file_path = Path(file_path)
        if file_path.suffix.lower() != '.png':
            return False
            
        # Check filename patterns common for screenshots
        name_lower = file_path.stem.lower()
        screenshot_patterns = [
            'screenshot', 'screen shot', 'screen-shot', 'screen_shot',
            'capture', 'screen-capture', 'screen_capture',
            'snip', 'snippet', 'snap'
        ]
        
        # Check if filename contains date-time pattern (common for screenshots)
        has_datetime = bool(re.search(r'\d{4}[-_]?\d{2}[-_]?\d{2}[-_at]?\d{2}[-_]?\d{2}', name_lower))
        
        # Check for screenshot patterns in filename
        if any(pattern in name_lower for pattern in screenshot_patterns) or has_datetime:
            return True
            
        try:
            # Use exiftool to check metadata
            result = subprocess.run(
                ['exiftool', '-json', str(file_path)],
                capture_output=True,
                text=True,
                check=True
            )
            metadata = json.loads(result.stdout)[0]
            
            # Check for common screenshot software in metadata
            software = metadata.get('Software', '').lower()
            screenshot_software = [
                'screenshot', 'snagit', 'lightshot', 'grabber',
                'monosnap', 'snipping tool', 'screencapture'
            ]
            
            if any(sw in software for sw in screenshot_software):
                return True
                
            # Check image dimensions
            # Most screenshots have standard screen dimensions
            width = int(metadata.get('ImageWidth', 0))
            height = int(metadata.get('ImageHeight', 0))
            
            common_resolutions = [
                (1920, 1080), (2560, 1440), (3840, 2160),  # Common desktop resolutions
                (1280, 720), (1366, 768), (1440, 900),
                (1680, 1050), (2880, 1800), (3200, 1800)
            ]
            
            for w, h in common_resolutions:
                # Allow some flexibility in dimensions (e.g., for partial screenshots)
                if width <= w and height <= h:
                    return True
                    
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as e:
            print(f"Error checking screenshot metadata: {e}")
            # If metadata check fails, fall back to filename check only
            pass
            
        return False

    def is_bookmark_file(self, file_path):
        """
        Determine if an HTML file is likely a bookmark list.
        
        Args:
            file_path (Path): Path to the HTML file
            
        Returns:
            bool: True if the file appears to be a bookmark list
        """
        if file_path.suffix.lower() not in ['.html', '.htm']:
            return False
            
        try:
            # Read the first few KB of the file to check its content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(8192)  # Read first 8KB
                
            # Common patterns in bookmark files
            bookmark_indicators = [
                'NETSCAPE-Bookmark-file',
                'Bookmarks Menu',
                'Bookmarks Toolbar',
                'bookmark',
                '<DL><p>',  # Common Netscape bookmark format
                'favorites',
                '<A HREF=',  # Multiple links
                'Mozilla Firefox',
                'Google Chrome',
                'Safari Bookmarks',
                'Opera Bookmarks',
            ]
            
            # Check if content has multiple links (typical for bookmark files)
            href_count = content.lower().count('<a href=')
            if href_count > 5:  # If file has more than 5 links, likely a bookmark file
                return True
                
            # Check for common bookmark file indicators
            content_lower = content.lower()
            if any(indicator.lower() in content_lower for indicator in bookmark_indicators):
                return True
                
            # Check if file has a typical bookmark structure
            # (multiple links organized in lists or hierarchical structure)
            if ('<dl' in content_lower and '<dt' in content_lower) or \
               ('<ul' in content_lower and '<li' in content_lower and href_count > 0):
                return True
                
        except Exception as e:
            print(f"Error checking if {file_path} is a bookmark file: {e}")
            
        return False

    def is_likely_ebook(self, file_path):
        """
        Determine if a PDF file is likely an ebook based on its metadata and characteristics.
        Returns True if the file appears to be an ebook, False otherwise.
        """
        try:
            result = subprocess.run(
                ['exiftool', '-json', '-Creator', '-Producer', '-PageCount', '-Title', '-Author', str(file_path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                metadata = json.loads(result.stdout)[0]
                
                # Check page count
                page_count = metadata.get('PageCount', 0)
                if page_count and int(page_count) >= MIN_EBOOK_PAGES:
                    return True
                
                # Check creator software
                creator = metadata.get('Creator', '').lower()
                producer = metadata.get('Producer', '').lower()
                if any(ebook_creator.lower() in creator or ebook_creator.lower() in producer 
                      for ebook_creator in EBOOK_CREATORS):
                    return True
                
                # Check for common ebook keywords in title or author
                title = metadata.get('Title', '').lower()
                author = metadata.get('Author', '').lower()
                ebook_keywords = ['book', 'edition', 'volume', 'chapter', 'publication']
                if any(keyword in title or keyword in author for keyword in ebook_keywords):
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error checking PDF metadata for {file_path}: {e}")
            return False

    def get_file_category(self, file_path):
        """Determine the category of a file based on its extension, name, and metadata."""
        file_path = Path(file_path)
        file_extension = file_path.suffix.lower()
        file_name = file_path.name.lower()

        # Special handling for HTML files
        if file_extension in ['.html', '.htm']:
            return 'documents/bookmarks' if self.is_bookmark_file(file_path) else 'dev'

        # Special handling for PNG files
        if file_extension == '.png':
            return 'images/screenshots' if self.is_screenshot(file_path) else 'images'

        # Special handling for audio files
        if file_extension in ['.mp3', '.m4a', '.flac', '.wav', '.aac', '.ogg', '.wma']:
            return 'audio/music' if self.is_music_file(file_path) else 'audio/recordings'

        # Special handling for PDFs
        if file_extension == '.pdf':
            return 'documents/ebooks' if self.is_likely_ebook(file_path) else 'documents/general'

        # Check each category's extensions
        for category, extensions in FILE_CATEGORIES.items():
            # Skip audio categories as they're handled above
            if category.startswith('audio/'):
                continue
            # Skip the documents/general category for .pdf files as they're handled above
            if category == 'documents/general' and file_extension == '.pdf':
                continue
            # Check if the file extension matches
            if file_extension in extensions:
                return category
            # For secrets, also check the filename
            if category == 'secrets' and any(secret_pattern in file_name for secret_pattern in extensions):
                return category
        
        return 'other'

    def get_destination_path(self, file_datetime, category):
        """Generate the destination path based on category and date hierarchy."""
        year = file_datetime.strftime('%Y')
        month = file_datetime.strftime('%Y-%m')
        day = file_datetime.strftime('%Y-%m-%d')
        
        # Split the category path if it contains subcategories
        category_parts = category.split('/')
        
        # Build the path including all category parts
        path_parts = [self.vault_path] + category_parts + [year, month, day]
        day_path = Path(*path_parts)
        
        # Create the full path
        day_path.mkdir(parents=True, exist_ok=True)
        return day_path

    def get_directory_datetime(self, dir_path):
        """Get the datetime for a directory based on its modification time."""
        dir_path = Path(dir_path)
        if not dir_path.is_dir():
            return None

        try:
            # Try to get directory's birth time (creation time) first
            try:
                # On macOS, st_birthtime is available
                dir_stat = os.stat(dir_path)
                if hasattr(dir_stat, 'st_birthtime'):
                    creation_time = datetime.fromtimestamp(dir_stat.st_birthtime)
                    if creation_time <= datetime.now():
                        return creation_time
            except AttributeError:
                pass

            # Next, try directory's modification time
            dir_mtime = datetime.fromtimestamp(dir_path.stat().st_mtime)
            if dir_mtime <= datetime.now():
                return dir_mtime

            # If both above fail, look for the oldest file in the directory
            oldest_time = None
            for item in dir_path.rglob('*'):
                if item.is_file() and not item.name.startswith('.'):
                    try:
                        # Try to get file's creation time first
                        stat = os.stat(item)
                        if hasattr(stat, 'st_birthtime'):
                            file_time = datetime.fromtimestamp(stat.st_birthtime)
                        else:
                            file_time = datetime.fromtimestamp(item.stat().st_mtime)
                        
                        if oldest_time is None or file_time < oldest_time:
                            oldest_time = file_time
                    except (OSError, ValueError):
                        continue

            if oldest_time and oldest_time <= datetime.now():
                return oldest_time

            # If all attempts fail, use directory mtime as last resort
            return dir_mtime

        except Exception as e:
            print(f"Error getting directory datetime for {dir_path}: {e}")
            return None

    def process_directory(self, dir_path):
        """Process a directory by zipping it and moving to archives."""
        try:
            dir_path = Path(dir_path)
            if not dir_path.is_dir():
                return

            # Remove .git directories first
            for git_dir in dir_path.rglob('.git'):
                if git_dir.is_dir():
                    try:
                        shutil.rmtree(git_dir)
                        print(f"Removed .git directory: {git_dir}")
                    except Exception as e:
                        print(f"Error removing .git directory {git_dir}: {e}")

            # Remove any hidden files
            for item in dir_path.rglob('*'):
                if item.name.startswith('.'):
                    try:
                        item.unlink()
                        print(f"Deleted hidden/system file: {item}")
                    except Exception as e:
                        print(f"Error deleting hidden file {item}: {e}")

            # Get directory timestamp before creating zip
            dir_datetime = self.get_directory_datetime(dir_path)
            if dir_datetime is None:
                print(f"Could not determine timestamp for directory {dir_path}")
                return

            # Create zip archive
            zip_path = self.zip_directory(dir_path, dir_datetime)
            if not zip_path:
                return

            # Move zip file to vault
            dest_dir = Path(self.vault_path) / 'archives' / str(dir_datetime.year) / \
                      f"{dir_datetime.year}-{dir_datetime.month:02d}" / \
                      f"{dir_datetime.year}-{dir_datetime.month:02d}-{dir_datetime.day:02d}"
            dest_dir.mkdir(parents=True, exist_ok=True)

            dest_path = dest_dir / zip_path.name
            shutil.move(str(zip_path), str(dest_path))
            print(f"Moved {zip_path.name} to {dest_path}")

            # Remove original directory
            shutil.rmtree(dir_path)
            print(f"Removed original directory: {dir_path}")

        except Exception as e:
            print(f"Error processing directory {dir_path}: {e}")

    def zip_directory(self, dir_path, dir_datetime):
        """Create a zip archive of a directory, preserving original timestamps."""
        try:
            if not dir_path.is_dir():
                return None

            # Format the timestamp for the zip filename
            timestamp = dir_datetime.strftime('%Y%m%d-%H%M%S')
            zip_filename = f"{dir_path.name}_{timestamp}.zip"
            zip_path = dir_path.parent / zip_filename

            # Create the zip archive
            with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zipf:
                for item in dir_path.rglob('*'):
                    if item.is_file() and not item.name.startswith('.'):
                        # Get original file timestamp
                        file_time = item.stat().st_mtime
                        # Convert to ZIP file date time tuple
                        date_time = datetime.fromtimestamp(file_time).timetuple()[:6]
                        
                        # Create ZipInfo object to preserve timestamp
                        zinfo = zipfile.ZipInfo(
                            filename=str(item.relative_to(dir_path)),
                            date_time=date_time
                        )
                        zinfo.compress_type = zipfile.ZIP_DEFLATED
                        
                        # Copy file data and permissions
                        with open(item, 'rb') as f:
                            zipf.writestr(zinfo, f.read())
                        
                        # Preserve Unix permissions if any
                        if os.name == 'posix':
                            zinfo.external_attr = (item.stat().st_mode & 0xFFFF) << 16

            # Set the zip file's timestamp to match the directory's timestamp
            os.utime(zip_path, (dir_datetime.timestamp(), dir_datetime.timestamp()))

            print(f"Created zip archive: {zip_path}")
            return zip_path

        except Exception as e:
            print(f"Error creating zip for directory {dir_path}: {e}")
            return None

    def is_duplicate_file(self, source_path, target_dir):
        """
        Check if a file with same size and timestamp exists in target directory.
        
        Args:
            source_path (Path): Path to the source file
            target_dir (Path): Directory to check for duplicates
            
        Returns:
            bool: True if a duplicate exists, False otherwise
        """
        if not target_dir.exists():
            return False
            
        source_stat = source_path.stat()
        source_size = source_stat.st_size
        source_mtime = source_stat.st_mtime
        
        # Check all files in the target directory
        for existing_file in target_dir.glob('*'):
            if not existing_file.is_file():
                continue
                
            # Check if sizes match first (quick check)
            if existing_file.stat().st_size != source_size:
                continue
                
            # If sizes match, check modification time
            if abs(existing_file.stat().st_mtime - source_mtime) < 1:  # Allow 1 second difference
                # Files have same size and timestamp
                return True
                
        return False

    def process_file(self, file_path):
        """Process a single file: rename and move to appropriate location."""
        try:
            file_path = Path(file_path)
            if not file_path.is_file():
                print(f"Skipping {file_path} - not a file")
                return

            # Check if this is a file that should be ignored
            if self.should_ignore_file(file_path):
                try:
                    file_path.unlink()
                    print(f"Deleted hidden/system file: {file_path}")
                except Exception as e:
                    print(f"Error deleting hidden/system file {file_path}: {e}")
                return

            # Get file datetime
            file_datetime = self.get_file_datetime(file_path)
            
            # Get file category
            category = self.get_file_category(file_path)
            
            # Generate new filename
            new_filename = self.generate_new_filename(file_path, file_datetime)
            
            # Get destination directory with category
            dest_dir = self.get_destination_path(file_datetime, category)
            
            # Check for duplicates before proceeding
            if self.is_duplicate_file(file_path, dest_dir):
                print(f"Skipping duplicate file: {file_path.name}")
                return

            # Create destination directory if it doesn't exist
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Full destination path
            dest_path = dest_dir / new_filename
            
            # Ensure we don't overwrite existing files
            counter = 1
            base_stem = Path(new_filename).stem
            base_suffix = Path(new_filename).suffix
            
            while dest_path.exists():
                if self.has_timestamp(base_stem):
                    # If filename already has timestamp, just add counter
                    new_name = f"{base_stem}-{counter}{base_suffix}"
                else:
                    # If we added timestamp, add counter before timestamp
                    timestamp_split = base_stem.rsplit('_', 1)
                    if len(timestamp_split) == 2:
                        new_name = f"{timestamp_split[0]}-{counter}_{timestamp_split[1]}{base_suffix}"
                    else:
                        new_name = f"{base_stem}-{counter}{base_suffix}"
                
                dest_path = dest_dir / new_name
                counter += 1
            
            # Move the file
            shutil.move(str(file_path), str(dest_path))
            print(f"Moved {file_path.name} to {dest_path}")
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    def process_directories(self):
        """Process all directories in the inbox, creating zip archives."""
        inbox_path = Path(self.inbox_path)
        
        # Get all immediate subdirectories in inbox
        directories = [d for d in inbox_path.iterdir() if d.is_dir()]
        
        for dir_path in directories:
            # Create zip archive
            zip_path = self.zip_directory(dir_path, self.get_directory_datetime(dir_path))
            if zip_path:
                # Process the zip file
                self.process_file(zip_path)
                # Remove the original directory after successful zip creation
                try:
                    shutil.rmtree(dir_path)
                    print(f"Removed original directory: {dir_path}")
                except Exception as e:
                    print(f"Error removing directory {dir_path}: {e}")

    def organize_vault(self):
        """Process all files in the inbox directory."""
        # First, process any directories and create zip archives
        self.process_directories()
        
        # Then process all remaining files
        for item in Path(self.inbox_path).iterdir():
            if item.is_file():
                self.process_file(item)

    def should_ignore_file(self, file_path):
        """Check if the file should be ignored and deleted.
        This includes:
        - All hidden files (starting with .)
        - macOS specific files (.DS_Store, ._* files)
        """
        file_name = file_path.name
        return (
            file_name.startswith('.') or  # All hidden files
            file_name.startswith('._')    # macOS resource fork files
        )

def main():
    try:
        organizer = DigitalVaultOrganizer(INBOX_PATH, VAULT_PATH)
        organizer.organize_vault()
        print("Organization complete!")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
