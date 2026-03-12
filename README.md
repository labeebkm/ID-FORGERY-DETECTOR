# DocForge.Detect — AI-Powered ID Forgery Detection

A production-quality prototype that analyzes uploaded ID document images and
produces structured forgery risk reports using five complementary forensic techniques.

---

## Architecture

```
docforge/
├── backend/              # FastAPI Python backend
│   ├── main.py           # App factory + CORS
│   ├── routes/
│   │   └── analyze.py    # POST /api/v1/analyze-id
│   ├── services/
│   │   ├── ela_analysis.py       # Error Level Analysis
│   │   ├── noise_analysis.py     # Noise consistency
│   │   ├── edge_detection.py     # Canny edge artifacts
│   │   ├── blur_analysis.py      # Blur/sharpness consistency
│   │   ├── metadata_analysis.py  # EXIF inspection
│   │   └── fraud_scoring.py      # Signal fusion → risk score
│   ├── models/schemas.py         # Pydantic request/response models
│   ├── utils/image_utils.py      # Image loading + validation
│   └── requirements.txt
│
└── frontend/             # Next.js TypeScript frontend
    ├── pages/
    │   ├── _app.tsx
    │   └── index.tsx             # Main page
    ├── components/
    │   ├── UploadBox.tsx         # Drag-and-drop uploader
    │   ├── FraudReportCard.tsx   # Verdict + score card
    │   ├── AnalysisPanel.tsx     # Per-signal breakdown
    │   ├── ForensicVisuals.tsx   # ELA/edge/overlay visuals
    │   └── Loader.tsx            # Animated checklist
    ├── services/api.ts           # Axios API client
    └── styles/globals.css        # Dark forensic terminal theme
```

---

## Quick Start

### 1. Backend

```bash
cd docforge

# Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Run the server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be live at: http://localhost:8000
API docs at: http://localhost:8000/docs

### 2. Frontend

```bash
cd docforge/frontend

# Install dependencies
npm install

# Set environment variable (optional — defaults to localhost:8000)
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Run dev server
npm run dev
```

Frontend will be live at: http://localhost:3000

---

## API Reference

### `POST /api/v1/analyze-id`

Upload a JPEG or PNG image for forensic analysis.

**Request:** `multipart/form-data` with field `image`

**Response:**
```json
{
  "risk_score": 42,
  "risk_level": "Medium Risk",
  "explanation": "Moderate ELA anomalies detected...",
  "processing_time_ms": 318,
  "analysis": {
    "ela_score": 0.48,
    "noise_anomaly": false,
    "edge_artifacts": true,
    "blur_inconsistency": false,
    "metadata_flag": true
  },
  "validation": {
    "is_valid": true,
    "width": 1200,
    "height": 800,
    "file_size_bytes": 245120,
    "mime_type": "image/jpeg"
  },
  "ela_visual": "data:image/png;base64,...",
  "edge_visual": "data:image/png;base64,...",
  "tamper_overlay_visual": "data:image/png;base64,..."
}
```

### Risk Score Thresholds
| Score | Level          |
|-------|----------------|
| 0–29  | Likely Genuine |
| 30–59 | Medium Risk    |
| 60+   | Suspicious     |

---

## Forensic Pipeline

1. **ELA (Error Level Analysis)** — Re-saves image at 75% JPEG quality, computes
   per-pixel error. Edited regions show higher error. Contributes up to 40 points.

2. **Noise Analysis** — Estimates high-frequency noise via Gaussian subtraction,
   checks patch-level coefficient of variation. Inconsistent noise = compositing.

3. **Edge Detection** — Canny edge map. Unusual density or concentration flags
   possible pasting/splicing artifacts.

4. **Blur Consistency** — Variance of Laplacian per grid patch. Forged documents
   often mix photos with different focus levels.

5. **Metadata Inspection** — EXIF check for editing software keywords (Photoshop,
   GIMP, etc.) and missing capture device metadata.

---

## Bugs Fixed From Original

| Location | Issue | Fix |
|---|---|---|
| `image_utils.py` | `str \| None` type hint broke Python 3.9 | Changed to `Optional[str]` |
| `services/api.ts` | Frontend mapped `visuals` as nested object but backend returns flat fields | Removed nested mapping, read `ela_visual` etc. directly |
| `ForensicVisuals.tsx` | Consumed `visuals.ela_visual` (nested) which was always undefined | Props now accept flat fields matching backend schema |
| `image_utils.py` | MIN_WIDTH/HEIGHT was 400×250 — rejected most test images | Relaxed to 200×150 |
| `ela_analysis.py` | ELA heatmap encoded as RGB but `encode_png_base64` expects BGR | Added `cv2.cvtColor(RGB→BGR)` before encoding |
| `fraud_scoring.py` | Binary flags added 8 pts each — easy to hit 100 on genuine docs | Reduced binary bumps from 8 to 5 pts each |

---

## Notes

- This is a prototype demonstrating forensic pipeline design, not a production fraud system.
- ELA analysis is most effective on JPEG images; PNG results may vary.
- Results should be treated as investigative leads, not definitive verdicts.


# To start the backend
cd C:\Users\HP\Documents\docforge\frontend
npm run dev

# To start the frontend
cd C:\Users\HP\Documents\docforge

# Option A: set backend env vars in a file (recommended)
#   1) Copy backend/.env.example -> backend/.env
#   2) Fill in GEMINI_API_KEY in backend/.env
#   3) Run the backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Option B: set backend env vars in the shell (one session only)
$env:GEMINI_API_KEY = "Give you api key here"
$env:GEMINI_MODEL = "gemini-2.0-flash"  # Free-tier model that supports image input
$env:GEMINI_MODEL_CHECK = "0"           # Optional: set "1" to enable model availability warning
$env:GEMINI_MODEL_CHECK_TTL_SECONDS = "3600"  # Optional: re-check cadence
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

## Gemini API Key (Free Tier)
1. Open Google AI Studio and sign in with a Google account.
2. Create a new API key from the API Keys page.
3. Put the key in `backend/.env` (recommended) or set `GEMINI_API_KEY` in your shell.

Notes:
- Free tier has rate limits and model availability constraints.
- If you set a model you don't have access to, the Gemini call will fail with a 4xx error.

#How to run
1. run backend in one terminal:
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

2. then got to cd frontend path and run frontend in another terminal:
npm run dev