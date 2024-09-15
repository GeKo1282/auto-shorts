import os, json, math
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, clips_array, ColorClip, AudioFileClip
from typing import Tuple, List, Union, Dict

# Temporary
INTERPUNCTION = [".", ",", "!", "?", ":", ";", "(", ")", "[", "]", "{", "}", "<", ">", "\"", "'", "-"]
LIMIT_SECONDS = None
FPS = 60
LIMIT_SUB_WORDS = None
SUBTITLE_PAGE_CHARACTER_LIMIT = 8
ESTIMATION_IT_PER_SEC = 10
FONT_PATH = os.path.abspath("KOMIKAX_.ttf")
RESOLUTIONS = [
    144,
    240,
    360,
    480,
    720,
    1080,
    1440,
    2160
]

def format_time(seconds: float):
    hours = int(seconds // 3600)
    minutes = int(seconds % 3600 // 60)
    seconds = int(seconds % 60)

    return (f"{hours:02}:" if hours > 0 else "") + (f"{minutes:02}:" if minutes > 0 else "") + f"{seconds:02}" + (f".{str(seconds).split('.')[1][:2]}" if seconds % 1 != 0 else "")

def check_magick():
    if os.system("magick --version >/dev/null 2>&1") != 0:
        print("Error: ImageMagick is not installed. Please install it before running the script.")
        return False

    return True

def clip_max_crop(clip_height, clip_width, ratio, zoom):
    """Find the maximum dimensions that clip can be cropped to for specified ratio."""

    return (int(clip_height / zoom), int(clip_height * ratio / zoom)) if clip_height * ratio <= clip_width else (int(clip_width / ratio / zoom), int(clip_width / zoom))

def compile_background(*source_clips: List[Dict[str, Union[str, VideoFileClip, int]]]):
    clips = []

    for clip in source_clips:
        if isinstance(clip["clip"], str):
            clips.append({
                "clip": VideoFileClip(clip["clip"]),
                "weight": clip["weight"],
                "zoom": clip["zoom"],
                "start_at": clip["start_at"]
            })
        else:
            clips.append(clip)

        clips[-1]["clip"] = clips[-1]["clip"].subclip(clips[-1]["start_at"], clips[-1]["clip"].duration)

        clips.append({
            "clip": None,
            "weight": 1,
            "zoom": 1
        })

    clips = clips[:-1]

    final_clip = {
        "ratio": 9 / 16,
        "line_width": 4,
        "line_color": (255, 255, 255),
        "total_weight": sum([clip["weight"] for clip in clips])
    }

    if math.log(final_clip["total_weight"], 10) % 1 != 0:
        print("Warning: The total weight is not a power of 10. You may have mispelled some weights.")

    for clip in clips:
        if final_clip["ratio"] < 1:
            clip["ratio"] = final_clip["ratio"] * (final_clip["total_weight"] / clip["weight"])
        else:
            clip["ratio"] = final_clip["ratio"] / (final_clip["total_weight"] / clip["weight"])

        if not clip["clip"]:
            continue

        clip["origin"] = {
            "height": clip["clip"].h,
            "width": clip["clip"].w
        }

        clip["crop"] = {k: v for k, v in zip(("height", "width"), list(clip_max_crop(clip["clip"].h, clip["clip"].w, clip["ratio"], clip['zoom'])))}

    final_clip["min_subclip_width"] = min([clip["crop"]["width"] for clip in clips if clip["clip"]])
    final_clip["min_subclip_height"] = min([clip["crop"]["height"] for clip in clips if clip["clip"]])

    if final_clip["ratio"] < 1:
        final_clip["total_subclip_height"] = sum([clip["crop"]["height"] for clip in clips if clip["clip"]])

        final_clip["desired_height"] = max([h for h in RESOLUTIONS if h <= final_clip["total_subclip_height"]])
        final_clip["desired_width"] = int(final_clip["desired_height"] * final_clip["ratio"])
        
        if final_clip["total_subclip_height"] * final_clip["ratio"] <= final_clip["desired_width"]:
            print(f"Warning: The vertically smallest clip ({final_clip['min_subclip_width']}px, \"{[clip for clip in clips if clip['clip'] and clip['crop']['width'] == final_clip['min_subclip_width']][0]['clip'].filename}\")"
             f" is too small to make desired clip size of [{final_clip['desired_width']}x{final_clip['desired_height']}].", end="")
            
            final_clip["desired_width"] = max([int(h * final_clip["ratio"]) for h in RESOLUTIONS if h * final_clip["ratio"] <= final_clip["min_subclip_width"]])
            final_clip["desired_height"] = int(final_clip["desired_width"] / final_clip["ratio"])

            print(f" The resolution will be reduced to [{final_clip['desired_width']}x{final_clip['desired_height']}].")
    else:
        final_clip["total_subclip_width"] = sum([clip["crop"]["width"] for clip in clips if clip["clip"]])

        final_clip["desired_width"] = max([w for w in RESOLUTIONS if w <= final_clip["total_subclip_width"]])
        final_clip["desired_height"] = int(final_clip["desired_width"] / final_clip["ratio"])

        if final_clip["total_subclip_width"] / final_clip["ratio"] <= final_clip["desired_height"]:
            print(f"Warning: The horizontally smallest clip ({final_clip['min_subclip_height']}px, \"{[clip for clip in clips if clip['clip'] and clip['crop']['height'] == final_clip['min_subclip_height']][0]['clip'].filename}\")"
             f" is too small to make desired clip size of [{final_clip['desired_width']}x{final_clip['desired_height']}].", end="")
            
            final_clip["desired_height"] = max([w / final_clip["ratio"] for w in RESOLUTIONS if w / final_clip["ratio"] <= final_clip["min_subclip_height"]])
            final_clip["desired_width"] = int(final_clip["desired_height"] * final_clip["ratio"])

            print(f" The resolution will be reduced to [{final_clip['desired_width']}x{final_clip['desired_height']}].")

    print(f"The resulting clip will be [{final_clip['desired_width']}x{final_clip['desired_height']}].")

    for clip in clips:
        if not clip["clip"]:
            clip["clip"] = ColorClip(((final_clip["desired_width"], final_clip["line_width"]) if final_clip["ratio"] < 1 else (final_clip["line_width"], final_clip["desired_height"])), color=final_clip["line_color"], duration=min([clip["clip"].duration for clip in clips if clip["clip"]]))
            clip["crop"] = {"height": clip["clip"].h, "width": clip["clip"].w}
            clip["origin"] = {"height": clip["clip"].h, "width": clip["clip"].w}

        clip["clip"] = clip["clip"].crop(x1=clip["origin"]["width"] // 2 - clip["crop"]["width"] // 2, y1=clip["origin"]["height"] // 2 - clip["crop"]["height"] // 2, x2=clip["origin"]["width"] // 2 + clip["crop"]["width"] // 2, y2=clip["origin"]["height"] // 2 + clip["crop"]["height"] // 2)

    for clip in clips:
        if type(clip["clip"]) == ColorClip:
            continue

        clip["clip"] = clip["clip"].resize((final_clip["desired_width"], final_clip["desired_height"] * (clip["weight"] / final_clip["total_weight"])) if final_clip["ratio"] < 1 else (final_clip["desired_width"] * (clip["weight"] / final_clip["total_weight"]), final_clip["desired_height"]))
        clip["clip"] = clip["clip"].subclip(0, min([clip["clip"].duration for clip in clips]))

    final_clip["clip"] = clips_array([[clip["clip"]] for clip in clips] if final_clip["ratio"] < 1 else [[clip["clip"] for clip in clips]])

    if LIMIT_SECONDS:
        final_clip["clip"] = final_clip["clip"].subclip(0, LIMIT_SECONDS)

    return final_clip

def compile_subtitles(sub_file_path: str, video_dimentions: Tuple[int, int], font_size: int = 170, font_color: str = "white", stroke_color: Tuple[int, int, int] = "black", stroke_width: int = 7, *, fix_interpunction: bool = True, fixed_inter_path: str = None):
    def find_leading_interpunction(text: str):
        final_interpunction = ""
        
        while any([text.startswith(i) for i in INTERPUNCTION]):
            found_interpunction = None
            
            for i in INTERPUNCTION:
                if text.startswith(i):
                    found_interpunction = i
                    break

            if found_interpunction:
                final_interpunction += found_interpunction
                text = text.removeprefix(i).strip()

        return final_interpunction, text
    
    if fix_interpunction and not fixed_inter_path:
        print("Error: You must provide a path to the fixed interpunction file.")
        return
    
    with open(sub_file_path, "r") as f:
        subs = f.read()

    with open(fixed_inter_path, "r") as f:
        fixed_inter = f.read()

    fixed_inter = fixed_inter.replace("\n", " ").strip()

    subs = subs.split("\n\n")[:LIMIT_SUB_WORDS]
    subtitles = []

    for sub in subs:
        if not " --> " in sub:
            continue

        start, end = sub.split("\n")[0].split(" --> ")
        text = sub.replace(f"{start} --> {end}\n", "").strip()

        if fix_interpunction:
            fixed_inter = fixed_inter.strip()

            leading_interpunction, fixed_inter = find_leading_interpunction(fixed_inter)
            fixed_inter = fixed_inter.removeprefix(text)
            
            trailing_interpunction = ""
            while any([fixed_inter.startswith(i) for i in INTERPUNCTION]):
                trailing_interpunction += fixed_inter[0]
                fixed_inter = fixed_inter[1:]

                if fixed_inter.startswith(" "):
                    break

            fixed_inter = fixed_inter.removeprefix(trailing_interpunction).strip()

            text = f"{leading_interpunction}{text}{trailing_interpunction}"

        start = start.split(":")
        end = end.split(":")

        start = int(start[0]) * 3600 + int(start[1]) * 60 + float(start[2].replace(",", "."))
        end = int(end[0]) * 3600 + int(end[1]) * 60 + float(end[2].replace(",", "."))

        subtitles.append({
            "start": start,
            "end": end,
            "text": text
        })

    pages = [[]]

    while True:
        if not subtitles:
            break

        if len(pages[-1]) > 0 and (sum([len(sub['text']) for sub in pages[-1]]) + len(subtitles[0]['text']) >= SUBTITLE_PAGE_CHARACTER_LIMIT or any([pages[-1][-1]['text'].endswith(i) for i in INTERPUNCTION])):
            pages.append([])

        sub = subtitles.pop(0)
        pages[-1].append(sub)

    clips = []

    for page in pages:
        page_text = " ".join([sub["text"] for sub in page])

        clips.append(TextClip(page_text, fontsize=font_size, color=font_color, stroke_color=stroke_color, stroke_width=stroke_width, size=(video_dimentions[0], None), method='caption', font=FONT_PATH).set_duration(page[-1]["end"] - page[0]["start"]).set_start(page[0]["start"]).set_position(("center", "center")))

        print(f"Subtitle clips created: {len(clips)}/{len(pages)}", end=("\r" if len(clips) != len(pages) else "\n"))

    print("Subtitles compiled.")

    return clips

def compile_final():
    background_clip = compile_background(*[{k:v for k, v in zip(("clip", "weight", "zoom", "start_at"), (path, weight, zoom, start_at))} for path, weight, zoom, start_at in zip(
        [f"source/{p}" for p in os.listdir("source")],
        [39, 60],
        [1.5, 1],
        [60, 60]
    )])
    subtitle_clips = compile_subtitles("audio/5.vtt", (background_clip["desired_width"], background_clip["desired_height"]), 100, fix_interpunction=True, fixed_inter_path="stories/5.txt")

    audio = AudioFileClip("audio/5.mp3")

    final_clip = CompositeVideoClip([background_clip['clip']] + subtitle_clips)
    final_clip = final_clip.set_audio(audio)

    if LIMIT_SECONDS:
        final_clip = final_clip.subclip(0, LIMIT_SECONDS)
    else:
        final_clip = final_clip.subclip(0, audio.duration)

    print(f"Compiling final video ({format_time(audio.duration)}). Estimated compilation time: ~{format_time(audio.duration * FPS / ESTIMATION_IT_PER_SEC)}. Please wait...")

    final_clip.write_videofile(f"finals/5-final{FPS}.mp4", codec="libx264", fps=FPS)

def main():
    if not check_magick():
        return
    
    compile_final()

if __name__ == "__main__":
    main()

#TODO: De-hardcode the paths and parameters
#DONE: Automatically adjust length of background clip to audio and subtitles
#TODO: Estimate size of the text and warn if too big
#TODO: Async and add eta timers and progress bars
#TODO: Provide console-based interface
#TODO: Create simple web interface with controls, progress and file uploads and downloads
    #TODO: Add option to remotely download background clips from youtube
#TODO: Fancy layouts