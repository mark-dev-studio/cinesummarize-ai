print(">>> CURRENTLY RUNNING FILE:", __file__)
import sys
import subprocess
import os  # <-- 1. Add 'import os' here at the top
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Define your base directory here
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
def read_index():
    print("ROUTE HIT: Successfully reached root URL!")
    html_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return f"Error: index.html not found at {html_path}", 404

@app.post("/api/render-video")
@app.post("/api/render-video/")
async def render_video(payload: dict):
    print("Received render request from frontend:", payload)
    
    video_input = payload.get("videoUrl") or payload.get("url")
    reference_url = payload.get("referenceUrl")
    selected_style = payload.get("selectedStyle", "Summarize")

    # If the user provided a link instead of a local file path, download it locally first
    if video_input and video_input.startswith("http"):
        print(f"Downloading video from URL via yt-dlp: {video_input}")
        output_template = "downloaded_source.mp4"
        
        download_command = [
            sys.executable, "-m", "yt_dlp",
            "-f", "bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
            "-o", output_template,
            "--force-overwrites",
            video_input
        ]
        
        try:
            subprocess.run(download_command, check=True, capture_output=True, text=True)
            video_input = output_template  # Point your editing pipeline to the newly downloaded local file
            print("Successfully downloaded source video for editing.")
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=400, detail=f"Failed to download video from URL: {e.stderr}")

    if not video_input:
        raise HTTPException(status_code=400, detail="No video provided.")

    style_metadata = {}
    if reference_url and reference_url.startswith("http"):
        try:
            # Extract detailed JSON metadata from the reference link for accurate style analysis
            ref_command = [sys.executable, "-m", "yt_dlp", "--dump-json", reference_url]
            result = subprocess.run(ref_command, capture_output=True, text=True, check=True)
            
            import json
            meta = json.loads(result.stdout)
            
            style_metadata = {
                "source_reference": reference_url,
                "title": meta.get("title"),
                "duration": meta.get("duration"),
                "categories": meta.get("categories"),
                "tags": meta.get("tags"),
                "applied_style": selected_style
            }
            print(f"Successfully analyzed reference video style metrics for: {meta.get('title')}")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not parse reference video metadata: {e.stderr}")
        except Exception as ex:
            print(f"Error parsing reference JSON: {ex}")

    # If the input is a local file path (and not a web URL)
    if video_input and not video_input.startswith("http"):
        print(f"Successfully processed local file: {video_input}")
        return {
            "success": True,
            "message": f"Local media '{video_input}' processed successfully with style: {selected_style}!",
            "outputVideoUrl": video_input,
            "styleMetadata": style_metadata
        }

    # Otherwise, process via yt-dlp for web links
    # Otherwise, process via yt-dlp for web links
    try:
        output_template = "downloaded_source.mp4"
        download_command = [
            sys.executable, "-m", "yt_dlp",
            "-f", "bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
            "-o", output_template,
            "--force-overwrites",
            video_input
        ]
        subprocess.run(download_command, check=True, capture_output=True, text=True)
        
        return {
        "success": True,
        "message": f"Stream processed successfully with style: {selected_style}!",
        "outputVideoUrl": "downloaded_source.mp4",
        "styleMetadata": style_metadata
    }
    except subprocess.CalledProcessError as e:
    	print(f"Processing error: {e.stderr}")
    	raise HTTPException(status_code=500, detail=f"Failed to process stream: {e.stderr}")

# Comment out this line completely:
# app.mount("/", StaticFiles(directory="."), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
