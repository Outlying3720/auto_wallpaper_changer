import os
import sys
import time
import datetime
import ctypes
import signal
import argparse
from urllib.parse import unquote
from threading import Thread, Event

import logging
import requests

def parse_config():
    parser = argparse.ArgumentParser(description='arg parser')
    parser.add_argument('--path', type=str, default='./images', help='wallpaper download path')

    parser.add_argument('--source', type=str, default='FengYun4BWallpaperProvider', help='wallpaper provider')
    parser.add_argument('--interval', type=int, default=-1, help='check interval (minutes), negative value to disable')
    parser.add_argument('--verbose', action='store_true', default=False, help='verbose mode')
    parser.add_argument('--show_source', action='store_true', default=False, help='show all wallpaper provider and exit')

    args = parser.parse_args()

    if not args.path or args.path.startswith('.'):
        pwd = os.getcwd()
        args.path = os.path.join(pwd, args.path)

    return args

class WallpaperChanger:
    def __init__(self, savepath, wallpaper_provider, interval = -1) -> None:
        self.savepath = savepath
        self.wallpaper_provider = wallpaper_provider
        self.interval = interval

    def start_auto(self):
        logging.info('Start auto run with interval {} minutes.'.format(self.interval))
        if self.interval > 0:
            t = Thread(target=self._autorun)
            t.start()

    def _autorun(self):
        if self.interval < 0:
            return
        
        event = Event()
        
        while True:
            self.update_wallpaper()
            event.wait(self.interval * 60)

    def update_wallpaper(self):
        logging.info('Get new wallpaper...')
        new_wallpaper = self.wallpaper_provider.get_wallpaper()
        if new_wallpaper:
            filename = self.wallpaper_provider.get_filename()
            fullpath = self.save(filename, new_wallpaper)
            self.set_paper(fullpath)
        elif self.wallpaper_provider.reason:
            logging.error(self.wallpaper_provider.reason)

    def save(self, filename, content) -> str:
        fullpath = os.path.join(self.savepath, filename)
        with open(fullpath, 'wb') as f:
            f.write(content)
        
        return fullpath

    def set_paper(self, filepath: str):
        logging.info('Set wallpaper to {}'.format(filepath))
        ctypes.windll.user32.SystemParametersInfoW(20, 0, filepath, 0)

class WallpaperProvider:
    def __init__(self) -> None:
        self.url = ''
        self.respone = None
        self.updated = False
        self.reason = ''

    def get_wallpaper(self) -> bytes:
        if self.is_update(self.url):
            logging.info('Get new wallpaper')
            return self._download(self.url)
        
        logging.info('No update or error.')
        return None

    def _download(self, url: str) -> bytes:
        response = requests.get(url, allow_redirects=True)
        
        logging.debug(response.headers)
        if response.status_code == 200:
            self.respone = response
            self.reason = ''
            return response.content
        self.reason = response.status_code
        return None
        # filename = get_file_name(url, content.headers)
        # save_path = f'{PATH}\\{filename}'
        # if filename:
        #     with open(save_path, 'wb') as f:
        #         f.write(content.content)

        # # wget.download(url, PATH)
        # return save_path
    
    def is_update(self, url) -> bool:
        new_respone = requests.head(url, allow_redirects=True)
        
        logging.debug(new_respone.headers)
        if self.respone:
            if self.respone.headers['Last-Modified'] == new_respone.headers['Last-Modified']:
                self.updated = False
                return False
            
        self.updated = True
        return True

    def get_filename(self) -> str:
        headers = self.respone.headers
        url = self.url

        prefix = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')

        filename = ''
        if 'Content-Disposition' in headers and headers['Content-Disposition']:
            disposition_split = headers['Content-Disposition'].split(';')
            if len(disposition_split) > 1:
                if disposition_split[1].strip().lower().startswith('filename='):
                    file_name = disposition_split[1].split('=')
                    if len(file_name) > 1:
                        filename = unquote(file_name[1])
        if not filename and os.path.basename(url):
            filename = os.path.basename(url).split("?")[0]
        if not filename:
            return int(time.time())
        filename = filename.replace('\"', '')

        filename = prefix + '_' + filename
        return filename

class BingWallpaperProvider(WallpaperProvider):
    def __init__(self) -> None:
        super().__init__()
        self.fullstartdate = None
        self.url = 'https://cn.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1'

    def _download(self, url: str) -> bytes:
        response = requests.get(url, allow_redirects=True)
        logging.debug(response.headers)
        if response.status_code == 200:
            result = response.json()
            self.fullstartdate = result['images'][0]['fullstartdate']

            url_prefix = 'https://cn.bing.com/'
            image_url = result['images'][0]['url']
            self.filename = result['images'][0]['copyright'].split(' ')[0] + '.jpg'  # 去掉copyright

            return super()._download(url_prefix + image_url)
        self.reason = response.status_code

        return None
    
    def is_update(self, url) -> bool:
        response = requests.get(url, allow_redirects=True)
        logging.debug(response.headers)

        if response.status_code == 200:
            result = response.json()
            fullstartdate = result['images'][0]['fullstartdate']

            return fullstartdate != self.fullstartdate

        return False

    def get_filename(self) -> str:
        if self.fullstartdate and self.filename:
            return self.fullstartdate + self.filename
        
        return None

class FengYun4BWallpaperProvider(WallpaperProvider):
    def __init__(self) -> None:
        super().__init__()
        self.url = 'https://img.nsmc.org.cn/CLOUDIMAGE/FY4B/AGRI/GCLR/FY4B_DISK_GCLR.JPG'

class FengYun4AWallpaperProvider(WallpaperProvider):
    def __init__(self) -> None:
        super().__init__()
        self.url = 'https://img.nsmc.org.cn/CLOUDIMAGE/FY4A/MTCC/FY4A_DISK.JPG'

class FengYun3DWallpaperProvider(WallpaperProvider):
    def __init__(self) -> None:
        super().__init__()
        self.url = 'https://img.nsmc.org.cn/CLOUDIMAGE/FY3D/MIPS/FY3D_MERSI_GLOBAL.jpg'

class FengYun2HWallpaperProvider(WallpaperProvider):
    def __init__(self) -> None:
        super().__init__()
        self.url = 'https://img.nsmc.org.cn/CLOUDIMAGE/FY2H/NOM/FY2H_ETV_NOM.jpg'

class FengYun2HRegionalWallpaperProvider(WallpaperProvider):
    def __init__(self) -> None:
        super().__init__()
        self.url = 'https://img.nsmc.org.cn/CLOUDIMAGE/FY2H/GLL/FY2H_ETV_SEC_GLB.jpg'

class GEOsWallpaperProvider(WallpaperProvider):
    def __init__(self) -> None:
        super().__init__()
        self.url = 'https://img.nsmc.org.cn/CLOUDIMAGE/GEOS/MOS/IRX/PIC/GBAL/GEOS_IMAGR_GBAL_L2_MOS_IRX_GLL_YYYYMMDD_HHmm_10KM_MS.jpg'

# def get_old_paper(path: str):
#     file = os.listdir(path)
#     filepath = path+random.choice(file)

#     return filepath

def main():
    args = parse_config()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(filename)s %(lineno)s %(funcName)s %(levelname)s - %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(filename)s %(lineno)s %(funcName)s %(levelname)s - %(message)s")


    mod = sys.modules[__name__]

    avaliable_source = [s for s in dir(mod) if s.endswith('Provider') and s != 'WallpaperProvider']
    logging.info('Avaliable source: {}'.format(', '.join(avaliable_source)))

    if args.show_source:
        exit(0)

    logging.info('Start auto wallpaper changer! ')

    try:
        provider = getattr(mod, args.source)()
    except AttributeError as e:
        logging.critical('{} not found!'.format(args.source))
        
        exit(1)
    changer = WallpaperChanger(savepath=args.path, wallpaper_provider=provider, interval=args.interval)

    if args.interval > 0:
        changer.start_auto()
    else:
        changer.update_wallpaper()

    logging.info('Finished!')
    

if __name__ == '__main__':
    main()