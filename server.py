from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import whisper
import tempfile
import subprocess
import os
import uuid
import json

app = FastAPI()

# Model load (startup par ek baar)
model = whisper.load_model("base")

@app.get("/", response_class=HTMLResponse)
def ui():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Transcribe AI Pro</title>
<style>
  :root {
    --primary: #00ffd5;
    --primary-hover: #00d2ff;
    --glass: rgba(255, 255, 255, 0.05);
    --glass-border: rgba(255, 255, 255, 0.1);
    --bg-dark: #09090b;
    --text: #ffffff;
    --text-muted: #9ca3af;
  }

  * { box-sizing: border-box; }

  body {
    margin: 0;
    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background: linear-gradient(135deg, #09090b, #111827, #1e1b4b);
    min-height: 100vh;
    color: var(--text);
    padding: 20px;
    display: flex;
    justify-content: center;
    align-items: flex-start;
  }

  .container {
    width: 100%;
    max-width: 800px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    margin-top: 40px;
  }

  /* --- Cards --- */
  .card {
    background: var(--glass);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--glass-border);
    border-radius: 20px;
    padding: 30px;
    box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.5);
  }

  h2 {
    margin: 0 0 20px 0;
    text-align: center;
    background: linear-gradient(to right, #fff, #a5f3fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 28px;
    font-weight: 800;
  }

  /* --- Input Area --- */
  .input-group { display: flex; gap: 10px; margin-bottom: 0; }
  
  input {
    flex: 1;
    padding: 16px;
    border-radius: 12px;
    border: 1px solid var(--glass-border);
    background: rgba(0, 0, 0, 0.4);
    color: white;
    font-size: 16px;
    outline: none;
    transition: 0.3s;
  }
  input:focus { border-color: var(--primary); background: rgba(0, 0, 0, 0.6); }

  button {
    padding: 16px 30px;
    border: none;
    border-radius: 12px;
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-hover) 100%);
    color: #000;
    font-weight: 700;
    cursor: pointer;
    text-transform: uppercase;
    transition: transform 0.2s;
  }
  button:hover { transform: translateY(-2px); filter: brightness(1.1); }
  button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

  /* --- Video & Metadata Section --- */
  #result-area { display: none; flex-direction: column; gap: 20px; }

  .video-container-card {
    padding: 0;
    overflow: hidden; 
    border: none;
    background: #000;
    display: flex;
    justify-content: center;
  }

  /* Default 16:9 for YouTube */
  .video-wrapper {
    position: relative;
    width: 100%;
    padding-bottom: 56.25%; /* 16:9 */
    height: 0;
  }

  /* Vertical Mode for Instagram */
  .video-wrapper.vertical {
    padding-bottom: 120%; /* Taller aspect ratio for Reels */
    max-width: 400px;     /* Limit width so it doesn't look huge */
    margin: 0 auto;       /* Center it */
  }

  .video-wrapper iframe {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    border: 0;
  }

  .meta-box {
    display: flex;
    align-items: center;
    gap: 15px;
    padding: 15px;
    background: rgba(255,255,255,0.03);
    border-radius: 12px;
    border: 1px solid var(--glass-border);
  }
  .meta-thumb {
    width: 80px;
    height: 60px;
    object-fit: cover;
    border-radius: 8px;
  }
  .meta-info h3 { margin: 0; font-size: 16px; line-height: 1.4; }
  .meta-info p { margin: 5px 0 0 0; font-size: 13px; color: var(--text-muted); }

  /* --- Transcript Section --- */
  .transcript-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }
  .transcript-title { font-weight: 600; color: var(--primary); }
  
  .copy-btn {
    background: rgba(255,255,255,0.1);
    color: white;
    padding: 8px 16px;
    font-size: 12px;
    border: 1px solid var(--glass-border);
    cursor: pointer;
  }
  .copy-btn:hover { background: rgba(255,255,255,0.2); transform: none; }

  pre {
    white-space: pre-wrap;
    font-size: 15px;
    color: #e2e8f0;
    background: rgba(0, 0, 0, 0.4);
    padding: 20px;
    border-radius: 12px;
    border: 1px solid var(--glass-border);
    max-height: 400px;
    overflow-y: auto;
    margin: 0;
    line-height: 1.6;
  }

  ::-webkit-scrollbar { width: 8px; }
  ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 4px; }
  
  .loader { text-align: center; color: var(--primary); margin-top: 20px; display: none; }
</style>
</head>
<body>

<div class="container">
  
  <div class="card">
    <h2>🎙 Transcribe AI</h2>
    <div class="input-group">
      <input id="link" placeholder="Paste YouTube or Instagram link..." autocomplete="off"/>
      <button id="btn" onclick="processVideo()">Transcribe</button>
    </div>
    <div id="loader" class="loader">
      ⏳ Downloading & Transcribing... Please wait.
    </div>
  </div>

  <div id="result-area">
    
    <div class="card video-container-card">
      <div id="video-wrapper" class="video-wrapper">
        <div id="video-placeholder"></div>
      </div>
    </div>

    <div class="card">
      <div class="meta-box">
        <img id="meta-img" class="meta-thumb" src="" alt="Thumbnail">
        <div class="meta-info">
          <h3 id="meta-title">Video Title</h3>
          <p id="meta-detail">Channel Name • 0 Views</p>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="transcript-header">
        <span class="transcript-title">TRANSCRIPT</span>
        <button class="copy-btn" onclick="copyText()">📋 Copy Text</button>
      </div>
      <pre id="out">Waiting for input...</pre>
    </div>

  </div>
</div>

<script>
async function processVideo(){
  const link = document.getElementById("link").value;
  const btn = document.getElementById("btn");
  const loader = document.getElementById("loader");
  const resultArea = document.getElementById("result-area");
  const out = document.getElementById("out");
  const videoWrapper = document.getElementById("video-wrapper");

  if(!link) return alert("Please enter a link!");

  // Reset UI
  btn.disabled = true;
  loader.style.display = "block";
  resultArea.style.display = "none";
  out.textContent = "";
  videoWrapper.innerHTML = "";
  videoWrapper.className = "video-wrapper"; // Reset class

  try {
    const res = await fetch("/transcribe-link", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({link})
    });
    
    const data = await res.json();

    if(!data.success) {
      alert("Error: " + data.error);
      return;
    }

    // 1. Populate Transcript
    out.textContent = data.transcript;

    // 2. Populate Metadata
    if(data.meta) {
        document.getElementById("meta-title").textContent = data.meta.title || "Unknown Title";
        document.getElementById("meta-img").src = data.meta.thumbnail || "";
        document.getElementById("meta-detail").textContent = 
            `${data.meta.uploader || "Unknown"} • ${data.meta.view_count || 0} views`;
    }

    // 3. Handle Video Embed Logic
    if (link.includes("youtube.com") || link.includes("youtu.be")) {
        // --- YOUTUBE ---
        const videoId = getYouTubeID(link);
        videoWrapper.innerHTML = `<iframe src="https://www.youtube.com/embed/${videoId}" allowfullscreen></iframe>`;
    
    } else if (link.includes("instagram.com")) {
        // --- INSTAGRAM ---
        const instaId = getInstaID(link);
        if (instaId) {
            // Add 'vertical' class to fix aspect ratio for Reels
            videoWrapper.classList.add("vertical");
            // Use Instagram Embed URL
            videoWrapper.innerHTML = `<iframe src="https://www.instagram.com/p/${instaId}/embed/captioned/" allowtransparency="true" frameborder="0" scrolling="no"></iframe>`;
        } else {
             videoWrapper.innerHTML = `<div style="color:#aaa; display:flex; justify-content:center; align-items:center; height:100%;">Could not load Instagram embed.</div>`;
        }

    } else {
        // --- OTHERS ---
        videoWrapper.innerHTML = `<div style="color:#aaa; display:flex; justify-content:center; align-items:center; height:100%; padding:20px;">Video preview not available for this source.<br>Check metadata below.</div>`;
    }

    // Show Results
    resultArea.style.display = "flex";

  } catch (e) {
    alert("Network Error: " + e);
  } finally {
    btn.disabled = false;
    loader.style.display = "none";
  }
}

function copyText() {
    const text = document.getElementById("out").textContent;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.querySelector(".copy-btn");
        const original = btn.textContent;
        btn.textContent = "✅ Copied!";
        setTimeout(() => btn.textContent = original, 2000);
    });
}

function getYouTubeID(url) {
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
    const match = url.match(regExp);
    return (match && match[2].length === 11) ? match[2] : null;
}

function getInstaID(url) {
    // Matches /p/ID, /reel/ID, /tv/ID
    const regExp = /(?:p|reel|tv)\/([a-zA-Z0-9_-]+)/;
    const match = url.match(regExp);
    return match ? match[1] : null;
}
</script>
</body>
</html>
"""

@app.post("/transcribe-link")
async def transcribe_link(data: dict):
    link = data.get("link")
    if not link:
        return JSONResponse({"success": False, "error": "No link provided"}, status_code=400)

    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, f"{uuid.uuid4()}.wav")
    meta_data = {}

    try:
        # Step 1: Fetch Metadata
        # yt-dlp works for Instagram too!
        print("Fetching metadata...")
        meta_process = subprocess.run([
            "yt-dlp",
            "--dump-json",
            "--no-playlist",
            link
        ], capture_output=True, text=True)

        if meta_process.returncode == 0:
            info = json.loads(meta_process.stdout)
            meta_data = {
                "title": info.get("title") or info.get("description") or "Instagram Video",
                "uploader": info.get("uploader"),
                "view_count": info.get("view_count"),
                "thumbnail": info.get("thumbnail"),
                "webpage_url": info.get("webpage_url")
            }

        # Step 2: Download Audio
        print("Downloading audio...")
        subprocess.run([
            "yt-dlp",
            "-x",
            "--audio-format", "wav",
            "-o", audio_path,
            link
        ], check=True)

        # Step 3: Transcribe
        print("Transcribing...")
        result = model.transcribe(audio_path)

        return {
            "success": True,
            "transcript": result["text"],
            "meta": meta_data
        }

    except subprocess.CalledProcessError as e:
        return {"success": False, "error": "Could not download video. Make sure profile is public."}
    except Exception as e:
        return {"success": False, "error": str(e)}

    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)