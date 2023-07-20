import sys

from ext.BackgroundWindows import Helper
import os
import winshell
from win32com.client import Dispatch
import psutil
import json

if __name__ == '__main__':
    if not os.path.isfile("settings.json"):
        with open("settings.json", "w", encoding="utf-8") as f:
            f.write('{ "python_path": "" }')
    if not os.path.isfile("data.json"):
        with open("data.json", "w", encoding="utf-8") as f:
            f.write('{ "last_pid": 0 }')
    last_pid: int = json.load(open("data.json", "r", encoding="utf-8"))["last_pid"]
    for proc in psutil.process_iter():
        if proc.pid == last_pid and last_pid != 0:
            print(f"{proc.name()} is running.\n")
            import tkinter, tkinter.messagebox
            root = tkinter.Tk()
            root.withdraw()
            tkinter.messagebox.showerror("Error", "Another instance of AnyWallpapers is running. "
                                                  "Please start the app via the tray icon in the taskbar.")
            root.destroy()
            sys.exit()
    with open("data.json", "w", encoding="utf-8") as f:
        f.write(json.dumps({"last_pid": os.getpid()}))
    helper = Helper()
    helper.start_helper()
