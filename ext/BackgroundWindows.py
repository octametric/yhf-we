import ctypes
import json
from pathlib import Path
import os
import re
from tkinter import filedialog
import win32api
from bs4 import BeautifulSoup as Bs
import shutil
import tkinter.messagebox
import pystray
from PIL import Image
import threading
import win32gui
import win32con
import time
import webview
from screeninfo import get_monitors
import cv2


class Helper:

    def __init__(self) -> None:
        self.__booster_thread = None
        self.__screen_windows: dict = {}
        self.__screens: list = get_monitors()
        self.__screen_amount: int = len(self.__screens)
        self.__webview_booted: bool = False
        self.__ui = None
        self.__icon = None
        self.worker: int = 0
        self.all_workers: list = []
        self.__video_path: str = ""
        self.__start_booster: bool = False
        self.__current_wallpaper: str = ""
        self.__filter_types: list = ["blur", "brightness", "contrast", "grayscale", "hue-rotate",
                                     "invert", "saturate", "sepia"]
        self.blacklist: list = ["Microsoft Text Input Application", "Unbenannt ‎- Paint 3D", "Unbenannt - Paint 3D",
                                "Window", ""]
        self.__paused_screens: list = []

    def __get_dominant_color(self, img_path: str) -> dict:
        img = cv2.imread(img_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        color: tuple = cv2.mean(img)[:3]
        color = (color[0] + 10, color[1] + 10, color[2] + 10)
        background_color_str: str = f"rgb({color[0]}, {color[1]}, {color[2]})"
        return {"tuple": tuple(int(c) for c in color), "rgb_str": background_color_str}

    def __handle_finder(self) -> None:
        while not self.__webview_booted:
            time.sleep(0.1)

        move: int = 0
        cur_i: int = 0
        for window in self.__screen_windows.values():
            handle = win32gui.FindWindow(None, window['window'].title)
            i: int = 0
            while handle == 0:
                if handle == 0:
                    handle = win32gui.FindWindow(None, window['window'].title)
                    i += 1
                    if i > 10:
                        raise Exception("Couldn't find the window. Look's like a big problem, create an issue on "
                                        "GitHub.")
                    time.sleep(0.1)
            window['handle'] = handle
            self.__send_behind(handle)
            window['window'].hide()
            m = self.__screens[cur_i]
            win32gui.MoveWindow(handle, move, 0, m.width, m.height, True)
            move += window['window'].width
            cur_i += 1

    def __show_ui(self) -> None:
        try:
            self.__ui.show()
        except KeyError:
            self.__ui = webview.create_window("YHF-WE", "src/index.html", width=1100, height=650, js_api=self)
            self.__ui.events.shown += self.__ui_shown
            self.__ui.show()

    def __ui_shown(self) -> None:
        self.__ui.events.shown -= self.__ui_shown
        try:
            self.__set_icon(win32gui.FindWindow(None, "YHF-WE"), "src/img/logo.ico")
        except Exception:
            pass

    def __quit(self) -> None:
        if self.__ui is not None:
            try:
                self.__ui.destroy()
            except KeyError:
                pass
        for window in self.__screen_windows.values():
            try:
                window["window"].destroy()
            except KeyError:
                pass
        try:
            self.__icon.stop()
        except Exception:
            pass
        print("INFO: The KeyError can be ignored. It's normal and happens when a window is already closed.")

    def stop_engine(self) -> None:
        self.__quit()

    def __tray_icon(self) -> None:
        image = Image.open("src/img/logo.png")
        menu = (pystray.MenuItem('Change Wallpaper', self.__show_ui), pystray.MenuItem('Quit', self.__quit))
        self.__icon = pystray.Icon(name="AnyWallpaper", icon=image, title="AnyWallpaper", menu=menu)
        self.__icon.run()

    def start_helper(self) -> None:
        for screen in self.__screens:
            window: webview.Window = webview.create_window(screen.name, "", frameless=True, width=screen.width,
                                                           height=screen.height)
            self.__screen_windows[screen.name.replace("\\", "").replace(".", "")] = {'window': window, 'handle': 0,
                                                                                     'name': screen.name}
        threading.Thread(target=self.__handle_finder).start()
        self.__ui = webview.create_window("YHF-WE", "src/index.html", width=1100, height=650, js_api=self)
        self.__ui.events.shown += self.__ui_shown
        threading.Thread(target=self.__tray_icon).start()
        webview.start(func=self.__set, gui="edgechromium", debug=True)

    def log(self, msg: str) -> None:
        print(msg)

    def build_filter(self, given_filters=None) -> str:
        if given_filters is None:
            given_filters = {}
        filter_string: str = ""
        config: dict = json.loads(open(self.__current_wallpaper.replace("index.html", "video_config.json"), "r").read())
        for filter_type in self.__filter_types:
            if filter_type in config:
                if filter_type in given_filters:
                    filter_string += f"{filter_type}({given_filters[filter_type]})"
                else:
                    filter_string += f"{filter_type}({config[filter_type]})"
                if filter_type != self.__filter_types[-1]:
                    filter_string += " "
        return filter_string

    def close_ui(self) -> None:
        try:
            if self.__ui is not None:
                self.__ui.destroy()
        except KeyError:
            pass

    def __set_icon(self, hwnd: int, ico_path: str) -> None:
        ico_path = ico_path.replace('\\', '/')
        hicon = win32gui.LoadImage(0, ico_path, win32con.IMAGE_ICON, 0, 0, win32con.LR_LOADFROMFILE)
        win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, hicon)
        win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, hicon)

        win32gui.SendMessage(win32gui.GetWindow(hwnd, win32con.GW_OWNER), win32con.WM_SETICON, win32con.ICON_SMALL,
                             hicon)
        win32gui.SendMessage(win32gui.GetWindow(hwnd, win32con.GW_OWNER), win32con.WM_SETICON, win32con.ICON_BIG, hicon)

    def set_yt_wallpaper(self, url: str, mon: str) -> None:
        print(mon)
        monitor = int(mon)
        print(monitor)
        video_id: str = re.findall(r'(?<=v=)[^&#]+', url)[0]
        embed_url: str = f"https://www.youtube.com/embed/{video_id}?autoplay=1&mute=1&controls=0&loop=1&fs=0&playlist={video_id}"
        keys_iter = iter(self.__screen_windows)
        if monitor == 1:
            first_key = next(keys_iter)
            self.__screen_windows[first_key]['window'].load_url(embed_url)
            self.__screen_windows[first_key]['window'].show()
        if monitor == 2:
            first_key = next(keys_iter)
            second_key = next(keys_iter)
            self.__screen_windows[second_key]['window'].load_url(embed_url)
            self.__screen_windows[second_key]['window'].show()
        if monitor == 3:
            first_key = next(keys_iter)
            self.__screen_windows[first_key]['window'].load_url(embed_url)
            self.__screen_windows[first_key]['window'].show()
            second_key = next(keys_iter)
            self.__screen_windows[second_key]['window'].load_url(embed_url)
            self.__screen_windows[second_key]['window'].show()
        if monitor == 4:
            first_key = next(keys_iter)
            second_key = next(keys_iter)
            window_data = self.__screen_windows[second_key]['window']
            window_data.load_url("data.html")
            window_data.show()
        if not self.__start_booster:
            self.__start_booster = True
            self.__booster_thread = threading.Thread(target=self.booster)
            self.__booster_thread.start()
        self.__current_wallpaper = ""

    def __show_error(self, title: str, msg: str) -> None:
        try:
            if self.__ui is not None:
                ctypes.windll.user32.MessageBoxW(0, msg, title, 0)
        except KeyError:
            pass
    def select_video_file(self) -> None:
        root = tkinter.Tk()
        root.iconbitmap(default="src/img/logo.ico")
        root.withdraw()

        downloads_path = str(Path.home() / "Downloads")
        file_types = ('Video Files (*.mp4;*.webm;*.ogg;*.gif)', 'Image Files (*.gif)')
        res: str = filedialog.askopenfilename(initialdir=downloads_path, title="Select Video File",
                                              filetypes=((file_types[0], '*.mp4;*.webm;*.ogg;*.gif'),))
        root.destroy()
        if res.strip() == "" or res is None:
            return

        self.__video_path = res

    def incorrect_name(self) -> None:
        self.__show_error("Error", "The name is invalid.")

    def repair_wallpaper(self) -> None:
        highest_time: int = 0
        for w in self.__screen_windows.values():
            window_time: int = w["window"].evaluate_js("document.getElementsByTagName('video')[0].currentTime;")
            if window_time > highest_time:
                highest_time = window_time

        for window in self.__screen_windows.values():
            self.__send_behind(window["handle"])
            window["window"].evaluate_js("let video = document.getElementsByTagName('video')[0]; video.play(); "
                                         "video.currentTime = {};".format(highest_time))

        self.__paused_screens = []

    def create_range_with_label(self, name: str, label_str: str, span_str: str, min_val: int, max_val: int,
                                value: int, step, data_type: str, setting: str) -> tuple:
        soup = Bs(open("src/index.html", "rb"), "html.parser")

        label_current = soup.new_tag("label", **{'id': 'span' + name + setting, 'style': 'padding-bottom: 10px;'})
        label_current.string = label_str
        label_current_span = soup.new_tag("span")
        label_current_span.string = span_str
        label_current.append(label_current_span)
        input_current = soup.new_tag("input", **{'class': 'slider', 'data-value-type': data_type, 'max': str(max_val),
                                                 'min': str(min_val),
                                                 'onchange': "changed('" + name + "', '" + setting + "')",
                                                 'type': 'range',
                                                 'value': str(value), 'step': str(step), 'id': name + setting,
                                                 'oninput': "update_span(this); changed('"+name+"', '"+setting+"', false);"})
        return input_current, label_current


    def reload_ui(self) -> None:
        # load_url is not working, so we read the index.html file and replace the content.
        if self.__ui is not None:
            html = open("src/index.html", "r", encoding="utf-8")
            try:
                self.__ui.evualate_js(f"document.location.reload(true);")
            except KeyError:
                # The UI is already closed.
                pass


    def __callb(self, hwnd, ctx) -> None:
        tmp_tg = win32gui.FindWindowEx(hwnd, None, "SHELLDLL_DefView", None)
        if tmp_tg != 0 and tmp_tg is not None:
            self.all_workers[0] = win32gui.FindWindowEx(None, hwnd, "WorkerW", None)

    def __send_behind(self, hwnd: int) -> None:
        prog_man = win32gui.FindWindow("Progman", "Program Manager")

        win32gui.SendMessageTimeout(prog_man, 0x52C,
                                    0, 0, win32con.SMTO_NORMAL, 1000)

        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

        win32gui.SetParent(hwnd, prog_man)

        self.all_workers = [0]
        win32gui.EnumWindows(self.__callb, None)

        win32gui.ShowWindow(self.all_workers[0], win32con.SW_HIDE)

        win32gui.SetParent(hwnd, prog_man)

        win32gui.ShowWindow(self.worker, win32con.SW_SHOW)

    def __enum(self, hwnd, ctx) -> None:
        shelldll = win32gui.FindWindowEx(0, 0, "SHELLDLL_DefView", None)
        if shelldll != 0:
            ctx[0] = win32gui.FindWindowEx(0, ctx[0], "WorkerW", None)

    def load_url(self, url: str, css_config_path: str) -> None:
        json_css: dict = json.loads(open(css_config_path, "r", encoding="utf-8").read())
        wallpaper_data: dict = json.loads(
            open(url.replace("index.html", "wallpaper.json"), "r", encoding="utf-8").read())
        self.__current_wallpaper = url
        for window in self.__screen_windows.values():
            window['window'].load_url(url)
            self.__send_behind(window['handle'])
            window['window'].show()
            for key, value in json_css.items():
                setting = key
                if setting not in self.__filter_types and setting != "rotation" and setting != "zoom":
                    key_setting = setting.title().replace("-", "")
                    key_setting = key_setting[0].lower() + key_setting[1:]
                    if "gif" in wallpaper_data["extension"]:
                        window['window'].evaluate_js(f"let video = document.getElementsByTagName('img')[0];"
                                                     f"video.style.{key_setting} = '{value}';")
                    else:
                        window['window'].evaluate_js(f"let video = document.getElementsByTagName('video')[0];"
                                                     f"video.style.{key_setting} = '{value}';")
                elif setting in self.__filter_types:
                    if "gif" in wallpaper_data["extension"]:
                        window['window'].evaluate_js(f"let video = document.getElementsByTagName('img')[0];"
                                                     f"video.style.filter = '{self.build_filter()}';")
                    else:
                        window['window'].evaluate_js(f"let video = document.getElementsByTagName('video')[0];"
                                                     f"video.style.filter = '{self.build_filter()}';")
                elif setting == "rotation":
                    if "gif" in wallpaper_data["extension"]:
                        window['window'].evaluate_js(f"let video = document.getElementsByTagName('img')[0];"
                                                     f"video.style.transform = 'rotate({value})';")
                    else:
                        window['window'].evaluate_js(f"let video = document.getElementsByTagName('video')[0];"
                                                     f"video.style.transform = 'rotate({value}) "
                                                     f"scale({json_css['zoom']})';")
                elif setting == "zoom":
                    if "gif" in wallpaper_data["extension"]:
                        window["window"].evaluate_js(f"let video = document.getElementsByTagName('img')[0];"
                                                     f"video.style.transform = 'rotate({json_css['rotation']}) "
                                                     f"scale({value})';")
                    else:
                        window["window"].evaluate_js(f"let video = document.getElementsByTagName('video')[0];"
                                                     f"video.style.transform = 'rotate({json_css['rotation']}) "
                                                     f"scale({value})';")

    def __set(self) -> None:
        self.__webview_booted = True

    def booster(self) -> None:
        # How does the booster work? Well, it's a simple algorithm. We take all visible windows and look if they are
        # maximized or in fullscreen. If they are, we pause the Video at the screen where the background window is.
        def window_callback(hwnd: int, extra: list):
            if win32gui.IsWindowVisible(hwnd):
                title: str = win32gui.GetWindowText(hwnd)
                if title not in self.blacklist and "overlay" not in title.lower():
                    extra.append(hwnd)
            return True

        windows: list = []
        pause_state: dict = {}
        # Insert screens into the dict
        for screen in self.__screens:
            pause_state[screen.name] = False
        while True:
            if not self.__start_booster:
                return
            win32gui.EnumWindows(window_callback, windows)
            for window in windows:
                # Okay, the following is a bit of a hack. But it works. :)
                screen_monitor = self.__screens[
                    int(win32api.GetMonitorInfo(win32api.MonitorFromWindow(window))["Device"]
                        .replace("\\", "") \
                        .replace(".", "") \
                        .replace("DISPLAY", ""))
                    - 1]

                rect = win32gui.GetWindowRect(window)
                width = rect[2] - rect[0]
                height = rect[3] - rect[1]
                tup = win32gui.GetWindowPlacement(window)
                if tup[1] == win32con.SW_SHOWMAXIMIZED:
                    pause_state[screen_monitor.name] = True
                elif width == screen_monitor.width and height == screen_monitor.height:
                    pause_state[screen_monitor.name] = True
            windows.clear()
            for screen in pause_state:
                if pause_state[screen]:
                    self.__pause_video(screen)
                else:
                    self.__resume_video(screen)

            for screen in self.__screens:
                pause_state[screen.name] = False
            time.sleep(0.65)

    def __pause_video(self, screen):
        screen = screen.replace("\\", "").replace(".", "")
        if screen not in self.__paused_screens:
            self.__paused_screens.append(screen)
            window = self.__screen_windows[screen]
            window["window"].evaluate_js("let video = document.getElementsByTagName('video')[0];"
                                         "video.pause();")

    def __resume_video(self, screen):
        screen = screen.replace("\\", "").replace(".", "")
        if screen in self.__paused_screens:
            max_time: int = 0
            for w in self.__screen_windows.values():
                tmp_time: str = w["window"].evaluate_js("document.getElementsByTagName('video')[0].currentTime;")
                if int(tmp_time) > max_time:
                    max_time = int(tmp_time)
            self.__paused_screens.remove(screen)
            window = self.__screen_windows[screen]
            window["window"].evaluate_js("let video = document.getElementsByTagName('video')[0]; "
                                         "video.play(); video.currentTime = {max_time};")
