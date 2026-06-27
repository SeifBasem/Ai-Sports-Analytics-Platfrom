# Goalithm

Football intelligence dashboard for player tracking, movement heatmaps, match event spotting, player action detection, review, and analysis history

## Project Structure

```text
.
+-- frontend/        Angular dashboard UI
+-- backend/
|   +-- SA/SA/      ASP.NET Core API, auth, database, history, statistics
|   +-- Ai/         Flask AI backend and model inference code
|   +-- requirements.txt
+-- README.md
```

## Local Services

| Service | Default URL | Purpose |
| --- | --- | --- |
| Angular frontend | `http://localhost:4200` | Dashboard UI |
| ASP.NET API | `http://localhost:5067` | Auth, users, analysis history, saved statistics |
| Flask AI API | `http://localhost:5050` | Video processing and AI model inference |

The frontend API URLs are currently configured in:

```text
frontend/src/environments/environment.ts
```

## Required Local Files

Model files are not committed to git. Place them manually in `backend/Ai/` before running the AI backend:

```text
backend/Ai/best.pt
backend/Ai/yolo-football-pitch-detection.pt
backend/Ai/ball_model_FULL_OBJECT.pt
backend/Ai/sen_best_model_4.keras
```

Runtime outputs are written under `backend/Ai/outputs/` and are ignored by git.

## Environment

A local `.env` file can be used for development, but it is ignored and must not be committed.

Example values:

```env
JWT_SECRET=AI-Sports-Analytics-Development-JWT-Secret-Change-Me-2026
JWT_ISSUER=AI Sports Analytics
JWT_AUDIENCE=AI Sports Analytics Frontend

ASPNETCORE_ENVIRONMENT=Development
ASPNETCORE_URLS=http://localhost:5067
ConnectionStrings__DefaultConnection=Server=localhost\SQLEXPRESS;Database=SportsAnalyticsDB;Trusted_Connection=True;TrustServerCertificate=True;

DOTNET_API_BASE=http://localhost:5067

# Optional AI CSV behavior
# SKIP_FULL_EVENT_CSV=1
# ENABLE_FULL_EVENT_CSV=1
```

Make sure the same JWT settings are used by both the ASP.NET API and the Flask AI backend, otherwise authenticated AI requests can fail.

## Install Dependencies

### Frontend

```powershell
cd frontend
npm install
```

### ASP.NET API

```powershell
dotnet restore backend\SA\SA\SA.csproj
dotnet build backend\SA\SA\SA.csproj
```

### Flask AI Backend

```powershell
cd backend\Ai
python -m pip install -r ..\requirements.txt
```

## Run Locally

Start the ASP.NET API:

```powershell
dotnet run --project backend\SA\SA\SA.csproj --urls http://localhost:5067
```

Start the Flask AI backend:

```powershell
cd backend\Ai
python app.py
```

Or use:

```powershell
backend\Ai\start_server.bat
```

Start the Angular frontend:

```powershell
cd frontend
npm start
```

Open:

```text
http://localhost:4200
```

## Match Event Spotting Flow

The Match Event Spotting screen sends the uploaded video to the Flask AI backend endpoint:

```text
POST /ball_action_video
```

The current ball-action spotting path uses the ball match event model:

```text
backend/Ai/ball_model_FULL_OBJECT.pt
```

It does not run the full football analyzer module for this feature.

During processing, the AI backend writes ball-action outputs to `backend/Ai/outputs/`, including:

```text
<job_id>_ball_action_predictions.json
<job_id>_ball_action_events.jsonl
```

The JSON file contains the full prediction output, while the JSONL file is written incrementally as events are detected.

## Git Notes

The repository ignores local secrets, generated outputs, build artifacts, dependency folders, video uploads, and large model files.

Do not commit:

```text
.env
backend/Ai/outputs/
node_modules/
frontend/dist/
*.pt
*.pth
*.onnx
*.keras
*.h5
```

If model files need to be versioned later, use Git LFS or a separate release/download process.
