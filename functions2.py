#Rewrite with ossapi
from ossapi import *
import glob, os, shutil
import requests
from zipfile import ZipFile
from tqdm import tqdm

directurl = 'https://api.nerinyan.moe'

def fetch_data(score_list:list):
    """Given a list of scores, returns a compact dictionary with the beatmap id as keys and {'path': '', 'title': '', 'diff': '', 'star': 0} as values.
    
    """
    # compact_list = {str(score_list[i].beatmapset.id): {'path': '', 'title': '', 'diff': '', 'star': 0} for i in range(len(score_list))}
    compact_list = []
    # print(len(compact_list))
    if isinstance(score_list[0], Score):
        for x  in score_list:
            temp = {'beatmap_id': x.beatmapset.id ,'path': '', 'title': x.beatmapset.title, 'diff': x.beatmap.version, 'star': x.beatmap.difficulty_rating}
            compact_list.append(temp)
    else:
        for x  in score_list:
            beatmapset = x.beatmapset()
            temp = {'beatmap_id': beatmapset.id ,'path': '', 'title': beatmapset.title, 'diff': x.version, 'star': x.difficulty_rating}
            compact_list.append(temp)
    return compact_list

def check_beatmaps(score_list:list, osu_path:str):
    """Given a list of compacted score data and a path to the osu! installation folder, checks if each beatmap exists in the osu! folder. If so, fills in the 'path' key of the dictionary with the path of the beatmap folder. If not, leaves it empty."""
    
    count = 0
    for i, beatmap in enumerate(score_list):
        beatmap_id = beatmap['beatmap_id']
        # print(beatmap)
        match = glob.glob(f'{osu_path}/{beatmap_id}*') + glob.glob(f'beatmaps/{beatmap_id}*')
        # print(match)
        if match:
            beatmap['path'] = match[0]
            count += 1
    print(f'{count} beatmap(s) found! {len(score_list) - count} beatmap(s) missing.')

def download_beatmap(score:dict):
    """Given a score data, downloads the beatmap using NeriNyan/catboy API if it doesn't already exist in the beatmaps folder. If it does, returns the path of the beatmap in the osu! folder. If beatmap already exists in the beatmaps folder (relative), it will point to that path. This is so that it would run danser with the alternate configuration (when the beatmap hasn't been downloaded even though it already exists)."""
    if isinstance(score, Score):
        beatmapset_id = score.beatmapset.id
        pathname = f'{beatmapset_id} {score.beatmapset.artist} - {score.beatmapset.title}'
    else:
        beatmapset = score.beatmapset()
        beatmapset_id = beatmapset.id
        pathname = f'{beatmapset_id} {beatmapset.artist} - {beatmapset.title}'
    pathname = "".join(i for i in pathname if i not in "\\/:\"*?<>|")
    if glob.glob(f'beatmaps/{beatmapset_id}*'): return os.path.abspath(f'beatmaps/{pathname}') #if it already been downloaded, to prevent duplicates (just in case it didn't passed the first test)
    
    #Download
    # beatmap = requests.get(f'{directurl}/d/{beatmapset_id}?NoHitSound=true')
    # if beatmap.status_code != 200: #If failed, use catboy's
    # print(f"Unsuccessful GET request. Response is {beatmap.status_code}.\nTrying alternative mirror...")
    path = f'beatmaps/{pathname}.zip' #relative path lol
    with requests.get(f'https://us.catboy.best/d/{beatmapset_id}', stream=True) as beatmap:
        beatmap.raise_for_status()
        # if beatmap.status_code != 200: raise ConnectionError(f'Unsuccessful GET request. Response is {beatmap.status_code}.')

        total = beatmap.headers.get("content-length", 0)
        total_size = int(total) if total is not None else None
       
        #Writing it 
        with open(path, 'wb') as f, tqdm(
            desc=f'Downloading {path}',
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in beatmap.iter_content(chunk_size=1024):
                size = f.write(chunk)
                bar.update(size)        

    with ZipFile(path, 'r') as zip:
        try:
            zip.extractall(f'beatmaps/{pathname}')
        except:
            raise Exception('Extraction failed. Maybe the file retrieved is not what you think LOL')
    
    print("Downloaded beatmap!")
    os.remove(path) #Remove the zip file, keep the extracted one
    return os.path.abspath(f'beatmaps/{pathname}')
    
def find_difficulty(score_data:dict, path:str):
    """Given a dict of score data and a path to the osu! installation folder, returns the path of the .osu file with the specified difficulty."""
    if isinstance(score_data, Score): diffname = score_data.beatmap.version
    else: diffname = score_data.version
    diffname = "".join(i for i in diffname if i not in "\\/:*?<>|")
    match = glob.glob(f'{glob.escape(path)}\\*[[]{diffname}[]].osu') #Funny pattern to search for specified difficulty
    if match: 
        print('Found .osu! file')
        return match[0]
    else: raise LookupError(".osu file of the specified beatmap not found.")

def peak_timestamps(strain_data:tuple, range:int = 20):
    """Find the start and end time of peak hard moment in a beatmap, measured by strain."""
    strain = strain_data[2]
    time = strain_data[3]
    max_strain = max(strain)
    index = strain.index(max_strain)
    max_strain_moment = time[index]/1000
    start = max_strain_moment - range*1.3
    end = max_strain_moment + range/3
    return start, end

def reset_data(conf:dict):
    if not conf['debug']:
        for i in ['vids', 'replays', 'beatmaps']:
            if i == 'beatmaps' and conf['keep_beatmaps']: continue
            try: 
                shutil.rmtree(i)
                os.mkdir(i)
            except: continue