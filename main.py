import os
import sys
import argparse
from pathlib import Path
import r2
import video
import nim

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Query the Nemotron Omni model with a video from Cloudflare R2.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--video", help="Cloudflare R2 object key of the video (optional).")
    p.add_argument("--prompt", default="Describe this video in detail.",
                   help="Text prompt sent with the video.")
    p.add_argument("--api-key", default=os.environ.get("NVIDIA_API_KEY"),
                   help="NVIDIA API key (defaults to $NVIDIA_API_KEY).")
    p.add_argument("--think", action="store_true",
                   help="Enable reasoning (/think); off by default, as recommended for video.")
    p.add_argument("--max-tokens", type=int, default=65536, help="Max generated tokens.")
    p.add_argument("--temperature", type=float, default=None, help="Sampling temperature.")
    p.add_argument("--top-p", type=float, default=None, help="Nucleus sampling top_p.")
    p.add_argument("--reasoning-budget", type=int, default=16384,
                   help="Reasoning token budget (only used with --think).")
    p.add_argument("--stream", action=argparse.BooleanOptionalAction, default=True,
                   help="Stream the response (use --no-stream to disable).")
    p.add_argument("--dry-run", action="store_true",
                   help="Only validate the video; do not call the API.")
    p.add_argument("--model", default=None,
                   help="Override the model id.")
    args = p.parse_args(argv)

    # Recommended sampling defaults per mode
    if args.temperature is None:
        args.temperature = 0.6 if args.think else 0.2
    if args.top_p is None and args.think:
        args.top_p = 0.95
    return args

def select_video_interactively(videos: list[str]) -> str:
    print("Available videos in Cloudflare R2:")
    for idx, video_key in enumerate(videos, 1):
        print(f"  [{idx}] {video_key}")
    
    while True:
        try:
            choice = input(f"\nSelect a video (1-{len(videos)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(videos):
                return videos[idx]
            print(f"Please enter a number between 1 and {len(videos)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    
    # 1. Fetch available videos from R2
    try:
        all_objects = r2.list_objects()
    except Exception as exc:
        print(f"Error listing files from R2: {exc}", file=sys.stderr)
        return 1
        
    videos = [obj for obj in all_objects if obj.lower().endswith(".mp4")]
    
    if not videos:
        print("No .mp4 videos found in Cloudflare R2 bucket.", file=sys.stderr)
        return 1
        
    # 2. Select video
    selected_video = args.video
    if selected_video:
        if selected_video not in videos:
            print(f"Warning: Selected video '{selected_video}' not found in R2 bucket files.")
            # We can still try to download it in case it's a valid key that wasn't in the list
    else:
        try:
            selected_video = select_video_interactively(videos)
        except KeyboardInterrupt:
            print("\nAborted.")
            return 0

    print(f"Selected video: {selected_video}")
    
    # 3. Download the video from R2 to a temporary file
    temp_file = Path(f"temp_{Path(selected_video).name}")
    print(f"Downloading {selected_video} from Cloudflare R2...")
    try:
        r2.download_file(selected_video, temp_file)
    except Exception as exc:
        print(f"Error downloading file from R2: {exc}", file=sys.stderr)
        return 1
        
    temp_compressed_file = Path(f"temp_compressed_{Path(selected_video).name}")
    try:
        # 4. Probe and validate the video
        try:
            info = video.probe_video(str(temp_file))
        except video.ValidationError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        video.print_report(info)
        problems = video.check_constraints(info)
        if problems:
            sys.stdout.flush()
            print("Validation FAILED:", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
            return 2
        print("Validation passed.\n")

        # Check payload size limit (25MB after base64 encoding)
        # raw size * 4/3 > 26214400 bytes, which is ~19.66 MB (use 19,000,000 bytes for safety)
        active_video_file = temp_file
        if info.size_bytes > 19000000:
            print(f"Warning: Video size ({info.size_bytes / 1_048_576:.2f} MiB) will exceed the 25 MB API payload limit when base64 encoded.")
            try:
                video.compress_video(str(temp_file), str(temp_compressed_file), info.duration_s)
                # Re-probe the compressed video
                active_video_file = temp_compressed_file
                info = video.probe_video(str(active_video_file))
                print("\nCompressed video details:")
                video.print_report(info)
            except Exception as exc:
                print(f"Error compressing video: {exc}", file=sys.stderr)
                return 1

        if args.dry_run:
            print("--dry-run set; skipping the API call.")
            return 0

        if not args.api_key:
            print("error: no API key. Set $NVIDIA_API_KEY or pass --api-key.", file=sys.stderr)
            return 2

        # 5. Encode and describe the video
        try:
            video_url = video.to_data_url(str(active_video_file))
            nim.describe_video(
                video_url,
                args.prompt,
                args.api_key,
                model=args.model or nim.MODEL,
                think=args.think,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                top_p=args.top_p,
                reasoning_budget=args.reasoning_budget,
                stream=args.stream,
            )
        except nim.NimError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
            
    finally:
        # 6. Clean up temporary files
        for f in (temp_file, temp_compressed_file):
            if f.exists():
                print(f"Cleaning up temporary file {f}...")
                try:
                    f.unlink()
                except Exception as exc:
                    print(f"Warning: Failed to delete {f}: {exc}", file=sys.stderr)
                
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
