import subprocess
import os
import sys

def main():
    input_video = "final_output.mp4"
    output_video = "refined_output.mp4"
    
    if not os.path.exists(input_video):
        print(f"Error: {input_video} not found. Run merge.py or audio_cut.py first.")
        sys.stdout.flush()
        return

    # ... (filter_chain remains same) ...
    
    filter_chain = (
        "hqdn3d=1.5:1.5:6:6, "
        "crop=iw:iw/2.39, "
        "eq=saturation=1.1:brightness=0.05, "
        "curves=master='0/0 0.25/0.2 0.75/0.8 1/1', "
        "vignette, "
        "pad=iw:720:0:(oh-ih)/2, "
        "unsharp=5:5:0.2"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_video,
        "-vf", filter_chain,
        "-c:v", "libx264",
        "-crf", "18",       # High quality
        "-preset", "slow",
        "-c:a", "copy",     # Keep original audio
        output_video
    ]

    print(f"Refining video: {input_video} -> {output_video}")
    sys.stdout.flush()
    print("Applying: Denoise -> 2.39:1 Crop -> Brightness(+5%)/Sat(+10%) -> S-Curve -> Vignette -> Black Bars -> Sharpen")
    sys.stdout.flush()
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Success! Created {output_video}")
        sys.stdout.flush()
    except subprocess.CalledProcessError as e:
        print(f"Error during FFmpeg processing: {e}")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
