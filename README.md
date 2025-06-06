# Digital Vault Organizer

A Python script that automatically organizes files from an inbox directory into a structured digital vault, categorizing files based on their types and metadata.

## Features

- Automatically categorizes files into predefined directories based on file extensions
- Preserves original file timestamps
- Adds timestamps to filenames if not already present
- Special handling for different file types:
  - Distinguishes between music files and personal audio recordings using metadata
  - Categorizes photos by format (RAW, JPG, etc.)
  - Separates screenshots from other image types
  - Identifies and organizes ebooks
  - Handles various document types, development files, and archives

## Directory Structure

The script organizes files into the following categories:

- `photos/raw`: RAW photo formats (.nef, .arw, .cr2, .cr3, .raw, .dng)
- `photos/jpg`: Standard photo formats (.jpg, .jpeg, .heic)
- `images`: Other image formats (.ico, .icns, .svg, .gif, .bmp, .tiff, .webp)
- `images/screenshots`: Screenshots (.png)
- `videos`: Video files (.mp4, .mov, .avi, etc.)
- `audio/music`: Music files (.mp3, .m4a, .flac, etc.)
- `audio/recordings`: Personal audio recordings
- `documents/ebooks`: Ebook formats (.pdf, .epub, .mobi, .chm)
- `documents/notes`: Text and markdown files
- `documents/mindmaps`: Mind map files (.mm)
- `documents/bookmarks`: Bookmark files (.html, .htm)
- `documents/general`: General documents (.pdf, .doc, .docx, etc.)
- `dev`: Development and configuration files
- `calendars`: Calendar files (.ics)
- `secrets`: Security-related files (keys, certificates)
- `archives`: Archive files (.zip, .rar, .7z, etc.)
- `fonts`: Font files (.ttf, .otf, etc.)
- `other`: Unmatched file types

## Requirements

- Python 3.x
- ExifTool (for metadata extraction)

## Installation

1. Clone this repository or download the script
2. Install ExifTool:

   ```bash
   brew install exiftool
   ```

## Configuration

Edit the following variables at the top of the script:

```python
INBOX_PATH = "~/inbox"  # Source directory
VAULT_PATH = "~/digital_vault"  # Destination directory
```

## Usage

```bash
# Basic usage
python3 digital_vault_organizer.py

# With dry run (preview changes without moving files)
python3 digital_vault_organizer.py --dry-run

# With verbose output
python3 digital_vault_organizer.py --verbose
```

## Examples

### Example 1: Processing a Photo

Original file: `/inbox/IMG_1234.jpg`
New location: `/digital_vault/photos/jpg/IMG_1234_20241220-195110.jpg`

### Example 2: Processing a Document

Original file: `/inbox/meeting_notes.pdf`
New location: `/digital_vault/documents/general/meeting_notes_20241220-195110.pdf`

### Example 3: Processing a Music File

Original file: `/inbox/song.mp3` (with music metadata)
New location: `/digital_vault/audio/music/song_20241220-195110.mp3`

## Notes

- Files are renamed to include timestamps if they don't already have one
- The script preserves the original creation and modification dates
- Existing files in the vault are not overwritten
- Special metadata handling is used to distinguish between music and personal recordings
