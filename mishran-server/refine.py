import subprocess
import os

def main():
    input_video = "final_output.mp4"
    output_video = "refined_output.mp4"
    
    if not os.path.exists(input_video):
        print(f"Error: {input_video} not found. Run merge.py or audio_cut.py first.")
        return

    # Filter explanation:
    # 1. hqdn3d: Light denoise to clean up grain
    # 2. crop: Cut to 2.39:1 aspect ratio
    # 3. eq: +10% saturation, +5% brightness
    # 4. curves: S-Curve for contrast
    # 5. vignette: Cinematic corner darkening
    # 6. pad: Add black bars back to 16:9
    # 7. unsharp: Final sharpening
    
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
    print("Applying: Denoise -> 2.39:1 Crop -> Brightness(+5%)/Sat(+10%) -> S-Curve -> Vignette -> Black Bars -> Sharpen")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"\nSuccess! Created {output_video}")
    except subprocess.CalledProcessError as e:
        print(f"Error during FFmpeg processing: {e}")

if __name__ == "__main__":
    main()
