import os
import glob
import subprocess
import json
import numpy as np
import librosa
import csv
import sys
import requests
import shutil

# Configuration
N8N_URL = os.environ.get("AI_DIRECTOR_URL", "https://hari-n8n.laddu.cc/webhook/ai-director-input")
FRAMES_DIR = "cut_frames"

def get_latest_session_files():
    """Finds the latest session files in recordings/."""
    all_files = glob.glob(os.path.join("recordings", "recording_*.mkv"))
    if not all_files: return None, [], None

    timestamps = set()
    for f in all_files:
        try:
            parts = os.path.basename(f).split('_')
            if len(parts) >= 2 and parts[1].isdigit():
                timestamps.add(parts[1])
        except: continue
    
    if not timestamps: return None, [], None

    latest_ts = max(timestamps, key=int)
    print(f"Detected Session: {latest_ts}")
    
    video_files = sorted([f for f in all_files if latest_ts in f and "host_audio" not in f])
    host_audio = next((f for f in all_files if latest_ts in f and "host_audio" in f), None)
    
    return latest_ts, video_files, host_audio

def analyze_audio_for_cuts(audio_path, min_duration=3.0):
    """Analyzes audio to find cut points based on silence/pauses."""
    print(f"Analyzing audio for cuts: {audio_path}")
    sys.stdout.flush()
    try:
        y, sr = librosa.load(audio_path, sr=None)
        total_duration = librosa.get_duration(y=y, sr=sr)
        
        # Detect speech segments (non-silent)
        intervals = librosa.effects.split(y, top_db=30, frame_length=2048, hop_length=512)
        speech_segments = librosa.samples_to_time(intervals, sr=sr)
        
        candidate_times = [0.0]
        for start, end in speech_segments:
            candidate_times.append(end) # Cut at end of speech
        
        candidate_times.append(total_duration)
        candidate_times.sort()
        
        final_segments = []
        last_cut = 0.0
        
        for t in candidate_times:
            if t <= last_cut: continue
            if (t - last_cut) >= min_duration:
                final_segments.append((last_cut, t))
                last_cut = t
        
        # Handle remainder
        if last_cut < total_duration:
            if final_segments:
                prev_start, prev_end = final_segments.pop()
                final_segments.append((prev_start, total_duration))
            else:
                final_segments.append((0.0, total_duration))
                
        print(f"Generated {len(final_segments)} audio-driven segments.")
        sys.stdout.flush()
        return final_segments
    except Exception as e:
        print(f"Audio analysis failed: {e}. Fallback to 5s chunks.")
        return [(i*5.0, (i+1)*5.0) for i in range(10)] # Fallback

def extract_and_score_segments(segments, video_files, session_id):
    """
    Extracts frames for each segment and sends to AI for scoring.
    Returns a dict {segment_index: winner_cam_id}
    """
    # 1. Setup Directory
    if os.path.exists(FRAMES_DIR):
        shutil.rmtree(FRAMES_DIR)
    os.makedirs(FRAMES_DIR)
    
    segment_winners = {}
    
    print(f"Extracting frames and scoring {len(segments)} segments...")
    sys.stdout.flush()
    
    for i, (start, end) in enumerate(segments):
        midpoint = (start + end) / 2.0
        files_to_send = []
        opened_files = []
        
        print(f"\n--- Segment {i} ({start:.2f}s - {end:.2f}s) ---")
        
        # 2. Extract Frames from each camera
        for idx, v_file in enumerate(video_files):
            cam_id = idx + 1
            frame_path = os.path.join(FRAMES_DIR, f"seg{i}_cam{cam_id}.jpg")
            
            # Extract high-quality frame, resized for token efficiency
            cmd = [
                "ffmpeg", "-y", "-ss", str(midpoint), "-i", v_file,
                "-frames:v", "1", "-q:v", "5", 
                "-vf", "scale='if(gt(iw,ih),min(1024,iw),-1)':'if(gt(iw,ih),-1,min(1024,ih))'",
                "-loglevel", "error", frame_path
            ]
            subprocess.run(cmd)
            
            if os.path.exists(frame_path):
                f = open(frame_path, 'rb')
                opened_files.append(f)
                # Form field name: 'image_1', 'image_2' matches expectation
                files_to_send.append((f'image_{cam_id}', (os.path.basename(frame_path), f, 'image/jpeg')))
        
        # 3. Send to AI
        winner_id = 1 # Default
        if files_to_send:
            try:
                payload = {'timestamp_index': str(i), 'session_id': str(session_id)}
                print(f"Sending {len(files_to_send)} frames to AI Director...")
                sys.stdout.flush()
                
                resp = requests.post(N8N_URL, files=files_to_send, data=payload)
                resp.raise_for_status()
                
                # Parse response: {"winner_id": 2, "leaderboard": ...}
                try:
                    data = resp.json()
                    w = data.get("winner_id")
                    # Clean up "image_2" -> 2
                    if isinstance(w, str):
                        w = w.replace("image_", "").replace('"', "")
                    if w:
                        winner_id = int(w)
                    print(f"AI Decision: Camera {winner_id}")
                except:
                    print(f"Raw response (parse error): {resp.text}")
                    
            except Exception as e:
                print(f"AI Request failed: {e}")
        
        segment_winners[i] = winner_id
        
        # Cleanup file handles
        for f in opened_files: f.close()
        
    return segment_winners

def main():
    ts, video_files, host_audio = get_latest_session_files()
    if not video_files or not host_audio:
        print("Error: Missing video or host audio files.")
        return

    # 1. Analyze Audio
    audio_segments = analyze_audio_for_cuts(host_audio, min_duration=3.0)
    
    # 2. Extract & Score
    winners = extract_and_score_segments(audio_segments, video_files, ts)

    # 3. Build Plan
    final_plan = []
    
    # Map Cam ID to File Path
    # winners returns IDs like 1, 2. video_files is 0-indexed.
    # Map: 1 -> video_files[0], 2 -> video_files[1]
    
    for i, (start, end) in enumerate(audio_segments):
        win_id = winners.get(i, 1)
        # Safety clamp
        if win_id < 1 or win_id > len(video_files): win_id = 1
        
        video_path = video_files[win_id - 1]
        
        final_plan.append({
            'path': video_path,
            'start': start,
            'end': end
        })

    # 4. Render with FFmpeg (Concat + Punch-In + Ken Burns)
    output_video = "final_output.mp4"
    
    cmd = ["ffmpeg", "-y"]
    for f in video_files: cmd.extend(["-i", f])
    
    # Add host audio
    cmd.extend(["-i", host_audio])
    host_audio_idx = len(video_files)
    
    path_to_idx = {path: i for i, path in enumerate(video_files)}
    
    filter_parts = []
    concat_inputs = []
    
    is_zoomed = False
    ramp_frames = 15
    
    for i, clip in enumerate(final_plan):
        in_idx = path_to_idx[clip['path']]
        start = clip['start']
        end = clip['end']
        dur = end - start
        total_frames = int(dur * 30)
        
        v_name = f"v{i}"
        
        filters = [
            f"trim=start={start}:end={end}",
            "setpts=PTS-STARTPTS",
            "fps=30"
        ]
        
        # Logic: Alternating Punch-In + Animated Zoom
        if is_zoomed:
            # TIGHT: Zoom 1.0 -> 1.1 (0.5s) -> 1.15 (creep)
            zoom_expr = f"if(lte(n,{ramp_frames}),1.0+0.1*n/{ramp_frames},1.1+0.05*(n-{ramp_frames})/{total_frames})"
        else:
            # WIDE: Zoom 1.0 -> 1.04
            zoom_expr = f"(1.0+0.04*n/{total_frames})"
            
        filters.append(f"crop='iw/{zoom_expr}':'ih/{zoom_expr}':'(iw-ow)/2':'(ih-oh)/2'")
        filters.append("scale=1280:720")
        filters.append("format=yuv420p")
        filters.append("setsar=1")
        
        filter_parts.append(f"[{in_idx}:v]{','.join(filters)}[{v_name}]")
        concat_inputs.append(f"[{v_name}]")
        
        is_zoomed = not is_zoomed

    concat_str = "".join(concat_inputs)
    filter_parts.append(f"{concat_str}concat=n={len(final_plan)}:v=1:a=0[v]")
    
    # Map host audio (trimmed to total video duration)
    total_dur = final_plan[-1]['end']
    filter_parts.append(f"[{host_audio_idx}:a]atrim=start=0:end={total_dur},asetpts=PTS-STARTPTS[a]")
    
    cmd.extend([
        "-filter_complex", "; ".join(filter_parts),
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast",
        "-c:a", "aac",
        output_video
    ])
    
    print(f"Rendering {output_video}...")
    sys.stdout.flush()
    subprocess.run(cmd)
    print("Done.")
    sys.stdout.flush()

if __name__ == "__main__":
    main()
