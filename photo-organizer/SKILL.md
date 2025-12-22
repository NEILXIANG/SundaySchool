---
name: photo-organizer
description: This skill should be used when users need to automatically organize classroom photos by student names and dates using face recognition technology. It provides the complete workflow for processing photos, identifying students, and creating organized directory structures.
---

# Photo Organizer Skill

## Purpose

This skill provides a complete solution for automatically organizing Sunday school classroom photos using face recognition technology. It identifies students in photos and organizes them into standardized directory structures by student name and date.

## When to Use

Use this skill when users need to:
- Organize large numbers of classroom photos by student
- Automate the manual process of sorting photos by student identity
- Create structured photo archives for educational settings
- Process photos that contain multiple students who should each receive copies

## Workflow

### 1. Project Setup

To initialize a photo organization project:

1. Create the project structure with the required directories:
   ```
   sunday-photos/
   ├── src/              # Source code modules
   ├── data/             # Student data and reference photos
   ├── input/            # Photos to be processed
   ├── output/           # Organized photo results
   └── logs/             # Processing logs
   ```

2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

### 2. Student Information Management

To configure student information:

1. Edit the `data/students.csv` file with student details:
   ```
   ID,姓名,参考照片
   001,张三,photos/zhangsan.jpg
   002,李四,photos/lisi.jpg
   ```

2. Place reference photos in `data/students/photos/` directory
   - Use clear, front-facing photos
   - Ensure good lighting and minimal background distractions
   - Use consistent photo format (JPG recommended)

### 3. Photo Processing

To process photos:

1. Place all photos to be organized in the `input/` directory
   - Supported formats: .jpg, .jpeg, .png, .bmp, .tiff
   - No subdirectory structure needed (flat directory)

2. Run the photo organizer:
   ```
   python run.py
   ```

3. Monitor progress through the console output:
   - Student loading status
   - Photo scanning progress
   - Face recognition progress bar
   - Organization completion

### 4. Output Structure

The tool creates the following output structure:

```
output/
├── 张三/                 # Individual student directories
│   ├── 2024-01-21/       # Date-based subdirectories
│   │   ├── IMG_001_001.jpg
│   │   └── DSC_003_001.jpg
├── 李四/                 # Each student gets copies of photos
│   └── 2024-01-21/
│       └── DSC_003_001.jpg
└── 未知人脸/             # Unrecognized faces
    └── 2024-01-21/
        └── IMG_002_001.jpg
```

### 5. Multi-Student Photo Handling

When a photo contains multiple students:
- The photo is copied to each identified student's directory
- File naming remains consistent across all copies
- This ensures each student receives all photos where they appear

### 6. Error Handling and Troubleshooting

For common issues:

1. **Face recognition accuracy problems**
   - Adjust tolerance parameter: `--tolerance 0.5` (more strict)
   - Update reference photos with better quality images
   - Ensure reference photos show clear, front-facing views

2. **Processing speed issues**
   - Reduce batch size for large photo collections
   - Ensure sufficient system memory (4GB+ recommended)
   - Check available disk space for output

3. **Missing student encodings**
   - Verify CSV file format and paths
   - Check that reference photos exist and contain detectable faces
   - Review logs for specific error messages

### 7. Advanced Usage

For specific scenarios:

1. **Custom directory paths**:
   ```
   python run.py --input-dir /custom/path --output-dir /custom/output
   ```

2. **Processing multiple photo sets**:
   ```
   python run.py --input-dir class1_photos --output-dir class1_output
   python run.py --input-dir class2_photos --output-dir class2_output
   ```

3. **Debugging with detailed logs**:
   ```
   python run.py --log-dir debug_logs
   ```

## Reusable Components

### Scripts

- `src/main.py`: Main application entry point with command-line interface
- `src/face_recognizer.py`: Face detection and recognition logic
- `src/student_manager.py`: Student data and CSV management
- `src/file_organizer.py`: Photo copying and directory creation
- `src/utils.py`: Utility functions for logging and file operations

### References

The tool relies on face_recognition library documentation:
- Face detection and encoding methods
- Comparison algorithms and tolerance parameters
- Image processing best practices

### Assets

- `requirements.txt`: Python dependencies for face recognition
- `data/students.csv`: Template for student information
- `.gitignore`: Version control exclusions

## Best Practices

1. **Reference Photo Quality**
   - Use high-resolution photos (minimum 300x300 pixels)
   - Ensure consistent lighting conditions
   - Avoid facial obstructions (hands, accessories)

2. **Batch Processing**
   - Process photos in manageable batches (100-500 photos)
   - Monitor system resources during processing
   - Review output accuracy before processing large batches

3. **Data Management**
   - Regularly backup student reference photos
   - Maintain consistent naming conventions
   - Archive processed photos to free up input directory

4. **Quality Assurance**
   - Spot-check organized photos for accuracy
   - Review unrecognized photo collections
   - Update student information as needed