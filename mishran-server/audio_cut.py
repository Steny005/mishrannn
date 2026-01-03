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

def analyze_audio_for_cuts(audio_path, min_duration=3.0, max_shot_duration=7.0):
    """Analyzes audio to find cut points based on silence/pauses."""
    print(f"Analyzing audio for cuts: {audio_path}")
    sys.stdout.flush()
    try:
        y, sr = librosa.load(audio_path, sr=None)
        total_duration = librosa.get_duration(y=y, sr=sr)
        
        # Detect speech segments (non-silent)
        # top_db=20 is more sensitive to silence than 30
        intervals = librosa.effects.split(y, top_db=20, frame_length=2048, hop_length=512)
        speech_segments = librosa.samples_to_time(intervals, sr=sr)
        
        # Candidate cut points: midpoints of silence gaps
        candidate_times = []
        for i in range(len(speech_segments) - 1):
            gap_start = speech_segments[i][1]
            gap_end = speech_segments[i+1][0]
            candidate_times.append((gap_start + gap_end) / 2.0)
        
        candidate_times.append(total_duration)
        candidate_times.sort()
        
        final_segments = []
        last_cut = 0.0
        
        # Walk through time and pick best cut point (natural gap or forced)
        while last_cut < total_duration:
            # 1. Look for a natural pause within the [min, max] window
            next_cut = -1
            for t in candidate_times:
                if (last_cut + min_duration) <= t <= (last_cut + max_shot_duration):
                    next_cut = t
                    break
            
            # 2. If no natural pause, force a cut at max_shot_duration
            if next_cut == -1:
                next_cut = min(last_cut + max_shot_duration, total_duration)
            
            if next_cut > last_cut:
                final_segments.append((last_cut, next_cut))
                last_cut = next_cut
            else:
                break
                
        print(f"Generated {len(final_segments)} optimized segments.")
        sys.stdout.flush()
        return final_segments
    except Exception as e:
        print(f"Audio analysis failed: {e}. Fallback to 5s chunks.")
        sys.stdout.flush()
        return [(i*5.0, min((i+1)*5.0, 15.0)) for i in range(3)] 

def extract_and_score_segments(segments, video_files, session_id):
...
    # 3. Build Plan
    final_plan = []
    
    for i, (start, end) in enumerate(audio_segments):
        win_id = winners.get(i, 1)
        if win_id < 1 or win_id > len(video_files): win_id = 1
        video_path = video_files[win_id - 1]
        
        # We NO LONGER coalesce segments here. 
        # Every audio-driven segment becomes a new clip entry.
        # This ensures the Punch-In (Wide/Tight) toggles every single time there is a cut.
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
