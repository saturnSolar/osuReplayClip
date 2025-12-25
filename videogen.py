from moviepy import *
import os

bold_font = "fonts/Abrade-Bold.ttf"
font = "fonts/Abrade-Medium.ttf"
directory = 'vids'

def create_video(replaymetadata):
    if not os.path.exists(directory):
        os.mkdir(directory)

    clips = sorted(os.listdir(directory))
    if not clips:
        print('No replays available, unfortunately.')
        quit()
    demclips = []
    # replaychip1 = VideoFileClip('vids\\0.mp4').subclipped(2)
    # replaychip2 = VideoFileClip('vids\\1.mp4').subclipped(2)
    # replaychip2 = replaychip2.with_start(replaychip1.end)
    text = [item['title'] for item in replaymetadata]
    textdiff = [item['diff'] for item in replaymetadata]
    print(text)
    for i, clip in enumerate(clips):
        clip_index = int(clip.split('.')[0])
        composite_length = len(demclips)
        replayclip = VideoFileClip(f'{directory}\\{clip}').subclipped(2.8)
        if i != 0 and i <= len(clips):
            # print(demclips[composite_length-2])
            # print(f'last clip end: {demclips[composite_length-2].end}')
            replayclip = replayclip.with_start(demclips[composite_length-3].end)
        replayclip = replayclip.with_effects([vfx.FadeIn(1), vfx.FadeOut(1), afx.AudioFadeIn(1), afx.AudioFadeOut(1)])
        # print(f'{i} start at - {replayclip.start}')
        demclips.append(replayclip)
        
        titletext = TextClip(font=bold_font, text=text[clip_index], font_size=50, color='#fff', text_align='center')
        titletext = titletext.with_start(replayclip.start + 1)
        titletext = titletext.with_position(("center", 50))
        titletext = titletext.with_duration(replayclip.duration - 1)
        titletext = titletext.with_effects([vfx.CrossFadeIn(1), vfx.CrossFadeOut(3)])

        difftext = TextClip(font=font, text=textdiff[clip_index], font_size=30, text_align='center', color='#fff')
        difftext = difftext.with_start(titletext.start + 1).with_position(('center', (50 + titletext.h + 10))).with_duration(titletext.duration - 1).with_effects([vfx.CrossFadeIn(1), vfx.CrossFadeOut(3)])
        # print(f'text start at - {titletext.start}')
        demclips.append(titletext)
        demclips.append(difftext)

    composition = CompositeVideoClip(demclips)
    composition = composition.resized(0.5)
    # composition.preview(fps=10)
    composition.write_videofile("the2.mp4", fps=30, threads=4, codec='h264_nvenc')

print