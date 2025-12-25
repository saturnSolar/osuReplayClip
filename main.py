#Attempt at a rewrite using a python wrapper for osu! api

import os, shutil
import json
from ossapi import Ossapi, GameMode, ScoreType
from osrparse import Replay
from functions2 import *
from osustrain import get_strains
import subprocess
import time
from videogen import create_video

#load configurations
try:
    with open('conf.json', 'r') as conff:
        conf = json.load(conff)
except: raise FileNotFoundError('conf.json is missing!')

#verify configurations
osu_path = conf['osu_path']
try:
    available_beatmaps = os.listdir(osu_path)
except:
    FileNotFoundError('danser-cli.exe does not exist!')

try: api = Ossapi(conf['client_id'], conf['client_secret'])
except: APIException('Invalid credentials.')

#A temp configurations for danser as to not tamper the json itself.
#This alternative patch is added when a beatmap is not available in the osu! folder.
altpatch = {"General": {"OsuSongsDir": os.path.abspath(f"{osu_path}/Songs")}}

#FUNNIEST WAY TO DUPLICATE JSON STRING WITH SLIGHT DIFFERENCES BRUH
with open('danser_conf.json', 'r', encoding="utf-8") as f:
    jsonfile = json.load(f)
    jsonfile.update(altpatch)
    altpatch = json.dumps(jsonfile)
    f.seek(0)
    patch = json.dumps(json.load(f))    

patch = patch.replace('\"', '\\\"').replace('\n', '') #Make it compatible in CLI somehow
altpatch = altpatch.replace('\"', '\\\"').replace('\n', '')

def main():
    match conf['mode']:
        case 'online': 
            scores = online_mode()
        case 'local': 
            scores = local_mode()

    create_video(scores)

    
def local_mode():
    """
    Uses local replays in localreplays folder, regardless of player or anything.

    WARNING: Replays of a local beatmap won't work!

    Returns:
        list: A list of dictionaries containing title, difficulty name, and star rating of each beatmap.
    """
    print('Current Mode: Local')
    print('Using local replays in localreplays folder, regardless of player or anything. (WARNING: Replays of a local beatmap won\'t work!)')
    replay_files = os.listdir('localreplays')
    if not replay_files:
        print('No replays found.')
        quit()
        
    beatmap_data = []
    print('Checking beatmaps...')
    for replay in replay_files:
            raw_replay = Replay.from_path(f'localreplays/{replay}')

            try: beatmap = api.beatmap(checksum=raw_replay.beatmap_hash)
            except: Exception('Beatmap not found LOL')
            print(f'Found beatmap! {beatmap.beatmapset_id}')
            beatmap_data.append(beatmap)

    #Find title, difficulty name, and star rating in a dict.
    scores = fetch_data(beatmap_data)

    #Check if beatmaps are available in the osu! folder or in beatmaps folder.
    check_beatmaps(scores, osu_path)

    #reset all cache data (except beatmaps folder if configured)
    reset_data(conf)

    print(f'Generating local replay clips!')
    start_time = time.time()

    for i, x in enumerate(beatmap_data):
        if conf['debug']: 
            print('[DEBUG MODE - skipped replay clips generator]')
            break
        
        beatmap_dir = scores[i]['path']
        print(beatmap_dir)
        if not beatmap_dir:
            beatmap_dir = download_beatmap(x)

        difficulty_file = find_difficulty(x, beatmap_dir)
        strain_data = get_strains(difficulty_file)
        print("Fetched strain data")
        start, end = peak_timestamps(strain_data, conf['clip_length']) #Using strain data, find what would be the fire moment of the beatmap. (Might work on it again later)

        file_name = f'localreplays/{replay_files[i]}'

        if 'beatmaps\\' in beatmap_dir:
            args = f'{conf['danser_path']} -r=\"{os.path.abspath(file_name).replace('\\', '\\')}\" -end={end} -start={start} -out=\"{i}\" -sPatch=\"{patch}\" -sPatch=\"{altpatch}\" -offset=3 -nodbcheck -noupdatecheck' #For beatmaps downloaded in beatmaps folder (relative)
        else:
            args = f'{conf['danser_path']} -r=\"{os.path.abspath(file_name).replace('\\', '\\')}\" -end={end} -start={start} -out=\"{i}\" -sPatch=\"{patch}\" -offset=3 -noupdatecheck'
        
        process = subprocess.run(args, text=conf['show_danser_output']) #CLI danser
        
    end_time = time.time()
    print(f'Took {end_time - start_time}s!')
    return scores

def online_mode():
    """
    Downloads replays from osu! API and records danser clips of them.
    """
    match conf['replay_type']:
        case 'best': replay_type = ScoreType.BEST
        case 'firsts': replay_type = ScoreType.FIRSTS
        case 'recent': replay_type = ScoreType.RECENT   

    user_id = conf['user_id']
    user = api.user(user_id)
    get_scores = api.user_scores(user_id, replay_type, mode=GameMode.OSU, limit=conf['replays'], offset=conf['scores_offset'])
    if not get_scores:
        print(f'{user.username} doesn\'t have any {conf['replay_type']} replays.')
        quit()

    #Find title, difficulty name, and star rating in a dict.
    scores = fetch_data(get_scores)

    #Check if beatmaps are available in the osu! folder or in beatmaps folder.
    check_beatmaps(scores, osu_path)

    #reset all cache data (except beatmaps folder if configured)
    reset_data(conf)

    print(f'Generating replay clips of {user.username}\'s {conf['replay_type']} plays!')
    start_time = time.time()

    for i, x in enumerate(get_scores):

        if conf['debug']: 
            print('[DEBUG MODE - skipped replay clips generator]')
            break
        score_id = x.id
        try: replay = api.download_score(score_id=score_id, raw=True) #Check if the replay exists first, to prevent downloading beatmap for nothing
        except:
            print('Replay not found. Skipping...')
            continue

        beatmap_dir = scores[i]['path']

        if not beatmap_dir:
            beatmap_dir = download_beatmap(x)

        difficulty_file = find_difficulty(x, beatmap_dir)
        strain_data = get_strains(difficulty_file)
        print("Fetched strain data")
        start, end = peak_timestamps(strain_data, conf['clip_length']) #Using strain data, find what would be the fire moment of the beatmap. (Might work on it again later)

        file_name = f'replays/topplay_{i}.osr'

        if 'beatmaps\\' in beatmap_dir:
            args = f'{conf['danser_path']} -r=\"{os.path.abspath(file_name).replace('\\', '\\')}\" -end={end} -start={start} -out=\"{i}\" -sPatch=\"{patch}\" -sPatch=\"{altpatch}\" -offset=3 -nodbcheck -noupdatecheck' #For beatmaps downloaded in beatmaps folder (relative)
        else:
            args = f'{conf['danser_path']} -r=\"{os.path.abspath(file_name).replace('\\', '\\')}\" -end={end} -start={start} -out=\"{i}\" -sPatch=\"{patch}\" -offset=3 -noupdatecheck'

        
        if replay:
            with open(file_name, mode='wb') as f:
                f.write(replay) 
        
        process = subprocess.run(args, text=conf['show_danser_output']) #CLI danser

    end_time = time.time()
    print(f'Took {end_time - start_time}s!')
    return scores

if __name__ == '__main__':
    main()