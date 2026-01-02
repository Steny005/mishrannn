# Mishran: AI-Driven Multi-Camera Production Suite

## Overview
Mishran is an automated multi-camera video production and editing system designed for high-quality content creation. The project consists of a distributed architecture including a centralized server, a host monitoring interface, and multiple camera clients. It leverages audio analysis and artificial intelligence to automate the editing process, mimicking a professional director's decisions.

## Project Structure

### 1. mishran-server
The core backend of the system, responsible for coordinating communication, managing recordings, and executing the automated editing pipeline.
- **server.js**: Node.js WebSocket server that manages connections from the host and camera clients. It handles real-time data streaming and command distribution.
- **audio_cut.py**: The primary automation script. It performs the following sequence:
    1. Analyzes the host audio track using librosa to identify natural speech patterns and pauses.
    2. Segments the session based on these audio cues with a minimum shot duration.
    3. Extracts representative frames from all camera angles at the midpoint of each segment.
    4. Submits frames to an AI scoring service to determine the optimal camera for each segment.
    5. Assembles the final video using FFmpeg with advanced visual techniques (Digital Punch-ins and Ken Burns effects).
- **refine.py**: A post-processing script that applies cinematic color grading, noise reduction, and a 2.39:1 anamorphic crop.
- **recordings/**: Directory where raw .mkv streams from clients and host are stored.
- **cut_frames/**: Temporary directory for frames extracted during the AI scoring phase.

### 2. mishran-host
A SvelteKit-based web application (and mobile app via Capacitor) designed for the session operator.
- Provides a dashboard to monitor connected camera clients.
- Initiates and terminates global recording sessions.
- Captures and streams high-quality host audio directly to the server.

### 3. mishran-camera
A SvelteKit-based application (and mobile app via Capacitor) that transforms mobile devices into synchronized camera clients.
- Streams 720p/1080p video and audio data to the server via WebSockets.
- Receives remote commands for synchronized starting and stopping of recording.

## Production Workflow

### 1. Capture Phase
- The Node.js server is initialized.
- Camera clients connect via mobile devices and enter a standby state.
- The Host interface connects and provides a master start command.
- Real-time streams are recorded as Matroska (.mkv) files on the server, indexed by session timestamp.

### 2. Analysis and Scoring Phase
- `audio_cut.py` is executed against the latest session.
- The script identifies logical "cuts" based on silence and speech breaks.
- AI scoring is performed per segment, ensuring the camera choice aligns with the visual context of the scene.

### 3. Assembly Phase
- The system generates a cutting plan based on AI scores.
- **Digital Punch-Ins**: The script alternates between Wide and Tight (110% zoom) shots to maintain visual energy and hide jump cuts.
- **Animated Zoom**: Every Tight shot includes a 500ms smooth ramp from 100% to 110% zoom, followed by a subtle Ken Burns creep.
- The Host Audio is merged as the master continuous track.

### 4. Post-Production Phase
- `refine.py` is executed to apply professional-grade filters:
    - 2.39:1 Cinematic Crop.
    - HQDN3D Noise Reduction.
    - S-Curve Contrast and Saturation adjustments.
    - Vignette and final Sharpening.

## Requirements
- Node.js 18+
- Python 3.10+
- FFmpeg (with libx264 support)
- Python Libraries: librosa, requests, numpy, soundfile

## Installation and Execution
1. Install dependencies:
   ```bash
   cd mishran-server && npm install
   pip install librosa requests numpy soundfile
   ```
2. Start the server:
   ```bash
   node server.js
   ```
3. Connect clients and host via their respective web/mobile interfaces.
4. After recording, run the automated pipeline:
   ```bash
   python audio_cut.py
   python refine.py
   ```
   The final output will be available as `refined_output.mp4` in the server directory.
