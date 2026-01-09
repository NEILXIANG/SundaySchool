# Privacy & Offline Processing Notice (For Parents)

This document answers a common concern from parents: **Will this Sunday School photo organizer upload children’s photos to the Internet or any server?**---

As church staff, we completely understand your concerns about children's privacy. In this digital age, news of photo leaks and privacy violations occurs frequently. Your caution is a responsible approach to protecting your child.

This document will explain, from both technical design and practical verification perspectives, **how this tool fundamentally protects children's privacy**—in short: photos are processed only on the teacher's computer, never leave the local device, and are never uploaded anywhere.

---

## 💡 The Simplest Answer (3 Key Points)

1. **No uploads**: This tool runs entirely on the teacher's computer. Photos are never sent to the Internet or any server.
2. **Works offline**: You can disconnect Wi-Fi or unplug the network cable—the tool still works normally (proof that it doesn't need Internet).
3. **No login required**: No account registration, no cloud service. All data stays in local folders on the teacher's computer.

Important boundary: the tool **only processes the photos placed in the working folders** (for example `input/student_photos/` and `input/class_photos/`). It does **not** scan the computer's photo library or other folders. Even with a network connection, the tool will not upload any data; it is designed to run completely offline.

> Scope note: This document describes **automatic behavior of the software**. If a teacher manually shares exported photos to a cloud drive, chat group, or album, that is a human action—not an automatic upload by the tool.

---

## 1. Common Questions from Parents

### Q1: Will the photos be uploaded to a server?
No.
- The tool reads photos from local folders and writes results back to local folders.
- The code is open and easy to check; it contains no functions to upload data.

### Q2: Will the photos be sent to an online face-recognition or external AI service?
No.
- Face recognition runs locally on the teacher’s computer using offline models.
- The tool does not send photos to any third‑party online API.

### Q3: Will it secretly connect to the Internet in the background?
No. The photo organizing process is completed entirely locally, with no network connection required.
- You can turn off Wi-Fi or disconnect the network before running, and the tool will still work normally.
- The face recognition models needed by the tool are already bundled in the software package—no downloading required.

### Q4: Will the child’s face data be stored or misused?
The tool generates some intermediate data locally to speed up processing, but it all stays on the teacher's computer and is not transmitted.
- **What is "face data"**: The software converts each face into a series of numbers (called a "feature vector")—like a digital fingerprint for each face. These numbers **cannot be reversed back into photos**; even if someone obtained them, they still cannot reconstruct the child's photo. They can only be used for local similarity comparison.
- **Where is it stored**: This data is saved in the working directory on the teacher's computer (in the same folder as the photos).
- **How to delete**: Teachers can delete the entire working folder at any time to remove all caches.

### Parents also ask: Will it automatically send usage records, analytics, or crash reports?
No.
- The tool does not automatically upload logs, does not report analytics, and does not send crash reports to external servers.
- Logs are only for troubleshooting and are stored locally under `logs/`.

---

## 2. What the Tool Does (Simple Explanation)

### Inputs (provided by the teacher)
- Student reference photos: `input/student_photos/<student_name>/`
- Class/event photos: `input/class_photos/`

### Processing (all on the local computer)
1. Read photo files from local folders.
2. Detect faces in each photo.
3. Extract a numeric “feature vector” for each detected face.
4. Compare faces in class photos with student reference faces (local computation).
5. Export organized results to the local `output/` folder.

### Outputs (written locally)
- Photos organized by student (copied/organized under `output/`).
- Reports and “unknown face” clustering results (for teacher review).
- Local logs (for troubleshooting).

---

## 3. How to Prove "No Photo Uploads"?

### The Simplest Verification Method
**Offline test**: Before running the tool, turn off the computer's Wi-Fi or unplug the network cable. The tool can still complete photo organization. This directly proves it doesn't need a network connection.

### Why Choose an Offline Design?

From the beginning, we chose a "**completely offline**" technical approach rather than the "cloud processing" solution many software products use. The reason is simple:

**Only when data never leaves the teacher's computer can we fundamentally eliminate the risk of leaks.**

Our tool uses a "**completely offline**" approach, technically eliminating these risks. This is the most responsible way to protect children's privacy.

### Software Design Principles
- This tool's core features (face recognition, photo sorting) use offline technology and don't depend on any online services.
- The face recognition model files are already built into the software package—no downloads needed.
- The software code is open source; any technically-skilled member can review it to confirm there's no upload functionality.

---

## 4. What Is Stored on the Teacher’s Computer?

- Input photos remain under `input/`.
- Exported results are under `output/`.
- Caches/indexes may be created for faster incremental processing.
- Logs may include runtime information and filenames; logs are stored locally and are not automatically sent or uploaded.

To remove traces after use, the teacher can delete the entire working folder (including `input/`, `output/`, and `logs/`).

---

## 5. Common Real-World Scenarios Parents Ask About

### Will old photos still be recognized as children grow up?
Yes. Simply update the student reference photos (add the latest photos), and the tool will automatically use the new photos for recognition. Old reference photos can be kept or deleted.

### Will the data remain on the computer after organizing photos?
Yes, all photos and processing results are in the working folder on the teacher's computer. Teachers can choose to:
- Keep results for next time (the tool remembers already-processed photos for faster operation next time)
- Or delete the working folder after use, leaving no traces

### Is it safe if teachers share organized photos with parent groups?
The tool itself doesn't upload photos. If a teacher chooses to manually share (e.g., send to WeChat groups, upload to cloud storage), that's a human action requiring internal church sharing policies. Suggestions:
- Only share photos from the child's own class
- Share only with parental consent
- Use secure sharing channels (e.g., church-dedicated cloud storage)

---

## 6. Recommendations for Churches (Best Practices)

### Tool Usage
- Recommend using a church-dedicated computer to avoid mixing with personal private data
- Archive or delete the working folder promptly after use
- Teachers should review results before sharing to avoid accidental distribution

### Photo Management Policies
Churches should establish photo management guidelines:
- Clarify when photos can be taken and how they'll be used
- Whether parents consent to photos being shared within the church
- Use secure sharing channels (church-dedicated cloud storage or encrypted channels)

---

## 💬 One-Sentence Summary (Can Be Shared Directly with Parents)

> **This tool runs entirely on the teacher's computer, with no Internet connection and no uploads. It's like organizing files on a computer—photos stay local. Teachers can demonstrate it offline for you.**

---

## 🤝 Our Commitment

- ✅ The tool is designed to be "completely offline" and will not automatically upload children's photos
- ✅ It will not automatically send logs/analytics/crash reports to external servers
- ✅ The code is open source; technically-skilled members are welcome to review it
- ✅ If you have questions, please feel free to communicate with church staff anytime
