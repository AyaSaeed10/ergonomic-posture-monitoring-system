AI-Based Ergonomic Posture Monitoring System

This project aims to develop a system that analyzes users' posture
while working at a computer using computer vision techniques.
The system detects neck and back posture from a side-positioned camera
and provides feedback to help maintain healthy ergonomics.

Technologies:
Python, MediaPipe, Computer Vision, Machine Learning

## How to run

These steps are for Windows, starting from a freshly downloaded (cloned) copy of the repository.

> **Important:** the project folder path must contain **only English characters**
> (for example `C:\Projects\ergonomic-posture-monitoring-system`).
> Some libraries fail to load files from folders with non-English names.

1. **Install Python 3.10** (other versions are not supported by the libraries we use).

2. **Create and activate a virtual environment** in the project folder:
   ```
   py -3.10 -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install the libraries:**
   ```
   pip install -r requirements.txt
   ```

4. **Add the Firebase configuration file.** It is **not in Git** (it is secret) - get it from the team.
   Put it here: `secrets/firebase_config.json`. It looks like this:
   ```json
   {
     "apiKey": "...",
     "projectId": "..."
   }
   ```

5. **Run the app** from the project folder:
   ```
   python -m user_app.main
   ```
