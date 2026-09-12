# remxr42 🎛️
### Dual Circular Polar Vinyl DJ Workstation

> An authentic Teenage Engineering inspired hardware-aesthetic DJ workstation with real-time 2D circular polar spectrogram vinyl platters, bi-directional audio scratch synthesis, optical telemetry monitors, and AI hand gesture tracking.

---

## 🌐 Hosting & Running on GitHub (2 Ways)

### 1. Host Free on GitHub Pages (Zero Install, Anyone Can Play)
You can host `remxr42` directly on GitHub Pages so anyone in the world can open and play it in their browser with **no installation**:

1. Create a new GitHub repository (e.g. `remxr42`).
2. Push or upload this project folder to your repository.
3. In your repo, go to **Settings** ⚙️ ➔ **Pages** (left sidebar).
4. Under **Build and deployment**:
   - **Source**: Select **GitHub Actions** (the included `.github/workflows/deploy.yml` will deploy automatically)
   - *OR* select **Deploy from a branch** ➔ Branch: `main` ➔ Folder: `/ (root)` ➔ Click **Save**.
5. Within 1 minute, GitHub will give you a live URL:
   ```
   https://<your-username>.github.io/remxr42/
   ```
Anyone visiting that URL gets the full dual-turntable console, live polar spectrograms, audio drag-and-drop, and AI hand tracking!

---

### 2. Run Full Python Workstation in GitHub Codespaces (1 Click in the Cloud)
To run the full Python backend (including YouTube downloading/search and Griffin-Lim phase retrieval) without installing Python locally:

1. On your GitHub repository page, click the green **`<> Code`** button.
2. Select the **Codespaces** tab ➔ Click **Create codespace on main**.
3. GitHub will automatically:
   - Launch an isolated cloud container configured via `.devcontainer/devcontainer.json`.
   - Install all audio dependencies (`libsndfile`, `ffmpeg`, Python packages).
   - Start the `remxr42` server on port 8542.
   - Automatically forward the port and open the live workstation in a browser tab.

---

## ⚡ Running Locally

### Option A: Zero-Install Standalone (Local Browser)
Double-click **`remxr42.html`** or **`index.html`** in any browser.
- No Python, no server, no installation required.
- Drag & drop any `.mp3`, `.wav`, `.ogg`, or `.flac` file directly onto either platter to start DJing.

### Option B: One-Click Windows Launcher (`run_remxr42.bat`)
Double-click **`run_remxr42.bat`**:
- Auto-configures an isolated virtual environment (`.venv`).
- Launches the workstation at `http://localhost:8542`.

### Option C: One Command via `uvx` / `pipx`
```bash
uvx --from . remxr42
# or
pipx run --spec . remxr42
```

### Option D: Standard Pip
```bash
pip install -e .
remxr42
```

---

## 🕹️ Controls & Features

| Feature | Control | Description |
| :--- | :--- | :--- |
| **Platter Scratching** | Mouse / Touch on Vinyl | Bidirectional audio scratching with needle drop sound and velocity pitch |
| **Track Ingestion** | Drag & Drop / 📂 OPEN | Drop any MP3, WAV, FLAC, or OGG file directly onto either platter |
| **Splicing & Loop** | `IN` / `OUT` / Presets | Set loop slice boundaries (`.5s`, `1s`, `2s`, `4s`, `ALL`) |
| **Hot Cues** | `C1`, `C2`, `C3`, `C4` | Set mode + tap cue button to drop instant jump markers |
| **Master Crossfader** | Horizontal Slider | Equal-power sine/cosine crossfade between Deck A and Deck B |
| **3-Band Studio EQ** | `HI` / `MID` / `LOW` | Equalizer filters with -12dB cut to +12dB boost per channel |
| **Master WAV Export** | `EXPORT MASTER WAV` | Offline mixdown rendering of both channels to 16-bit WAV PCM |
| **AI Hand Gestures** | Camera Toggle (`🖐️`) | MediaPipe computer vision (Pinch = Scratch, ☝️ = Play, ✊ = Stop, ✌️ = Loop) |

---

## 📂 Repository Structure
```
remxr42/
├── index.html              # GitHub Pages entrypoint (Zero-install web app)
├── remxr42.html            # Standalone standalone HTML distribution
├── run_remxr42.bat         # One-click Windows launcher
├── pyproject.toml          # Standard Python packaging configuration
├── README.md               # Quickstart & GitHub guide
├── .github/
│   └── workflows/
│       └── deploy.yml      # Automated GitHub Pages CI/CD workflow
├── .devcontainer/
│   └── devcontainer.json   # GitHub Codespaces cloud config
└── src/
    └── remxr42/
        ├── __init__.py
        ├── cli.py          # Console entrypoint (remxr42 command)
        ├── __main__.py     # python -m remxr42 support
        ├── app.py          # Full Streamlit workstation & conversion lab
        ├── spectrogram_engine.py # STFT & polar spectrogram engine
        └── console_component.py  # Dual turntable component generator
```

---
*Inspired by Teenage Engineering industrial design (EP-133 K.O. II, OP-1, TX-6) and the original polar spectrogram audio reconstruction architecture.*
