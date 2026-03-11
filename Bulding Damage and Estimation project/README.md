
# BuildSenseAI - Full Web App (Skeleton)
This is a minimal, runnable skeleton of **BuildSenseAI**: a React frontend + FastAPI backend with a **mock** detection model (OpenCV-based heuristic).
It provides:
- Image upload endpoint
- Mock damage detection (edge-density heuristic)
- Damage Report PDF and Remediation Report PDF generation (server-side using ReportLab)
- React frontend to upload images and download generated PDFs

## What is included
- backend/ (FastAPI app)
- frontend/ (React app skeleton)
- sample_images/ (a few demo images)
- README with run instructions

## How to run (Backend)
1. Install Python 3.9+ and create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux/Mac
   venv\Scripts\activate         # Windows
   ```
2. Install backend requirements:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
3. Run the backend:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
4. Backend will be available at `http://localhost:8000`.

## How to run (Frontend)
1. Ensure Node.js and npm are installed.
2. From project root:
   ```bash
   cd frontend
   npm install
   npm start
   ```
3. The React app will open at `http://localhost:3000` and will call the backend at `http://localhost:8000`.

## Usage
- Open the React app, upload an image (sample images included), click "Upload & Analyze".
- After processing, you can download the Damage Report and Remediation Report PDFs.

## Notes
- This is a **mock** detection model implemented with classical computer vision heuristics (Canny edges) for demo/testing.
- Replace `mock_detect_crack` in `backend/main.py` with a trained CNN or YOLO model for production-quality detection.
- PDF generation is done with ReportLab. Customize templates in `backend/main.py`.

