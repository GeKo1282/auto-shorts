import os, json, math
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, clips_array, ColorClip, AudioFileClip
from typing import Tuple

# Temporary
LIMIT_SECONDS = 59
SUBTITLE_PAGE_CHARACTER_LIMIT = 8
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

def clip_max_crop(clip_height, clip_width, ratio, zoom):
    """Find the maximum dimensions that clip can be cropped to for specified ratio."""

    return (int(clip_height / zoom), int(clip_height * ratio / zoom)) if clip_height * ratio <= clip_width else (int(clip_width / ratio / zoom), int(clip_width / zoom))

def compile_background():
    clips = [{
        "clip": VideoFileClip(f"source/{os.listdir('source')[0]}"),
        "weight": 39,
        "zoom": 1.5
    }, {
        "clip": None,
        "weight": 1,
        "zoom": 1
    },{
        "clip": VideoFileClip(f"source/{os.listdir('source')[1]}"),
        "weight": 60,
        "zoom": 1
    }]

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

def compile_subtitles(sub_file_path: str, video_dimentions: Tuple[int, int]):
    with open(sub_file_path, "r") as f:
        subs = f.read()

    subs = subs.split("\n\n")
    subtitles = []

    for sub in subs:
        if not " --> " in sub:
            continue

        start, end = sub.split("\n")[0].split(" --> ")
        text = sub.replace(f"{start} --> {end}\n", "")

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

        if sum([len(sub['text']) for sub in pages[-1]]) + len(subtitles[0]) >= SUBTITLE_PAGE_CHARACTER_LIMIT and len(pages[-1]) > 0:
            pages.append([])

        sub = subtitles.pop(0)
        pages[-1].append(sub)

    clips = []

    for page in pages:
        page_text = " ".join([sub["text"] for sub in page])
        subclips = []
        for sub in page:
            text_clip = TextClip(page_text, fontsize=170, color='white', size=(video_dimentions[0], None), method='caption', font="Cantarell-Bold")

            text_clip.set_position(("center", "center")).set_duration(sub["end"] - sub["start"])

            subclips.append(text_clip)

            print(f"Subtitle clips created: {len(clips)}/{sum([len(page) for page in pages])}", end=("\r" if len(clips) != sum([len(page) for page in pages]) else "\n"))

        clips.append(CompositeVideoClip(subclips).set_duration(page[-1]["end"] - page[0]["start"]).set_start(page[0]["start"]).set_position(("center", "center")))
    
    print("Subtitles compiled.")

    return clips

def compile_final():
    background_clip = compile_background()
    subtitle_clips = compile_subtitles("out.vtt", (background_clip["desired_width"], background_clip["desired_height"]))

    audio = AudioFileClip("out.mp3")

    final_clip = CompositeVideoClip([background_clip['clip']] + subtitle_clips)
    final_clip = final_clip.set_audio(audio)

    final_clip = final_clip.subclip(0, LIMIT_SECONDS)

    final_clip.write_videofile("final.mp4", codec="libx264", fps=60)

def main():
    compile_final()

if __name__ == "__main__":
    main()

# TODO: Add indentation to subtitles
# TODO: Create per-word subtitle clips, then combine them into a single subtitle clip by measuring their positions.