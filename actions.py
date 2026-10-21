import ctypes
import io
import subprocess
import threading
import time

import psutil
import pyautogui
import pyperclip
from comtypes import CLSCTX_ALL
from ctypes import POINTER, cast
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


def list_processes(query=""):
    groups = {}
    query = query.lower()
    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            name = proc.info["name"] or ""
            if query and query not in name.lower():
                continue
            mem = proc.info["memory_info"].rss / 1024 / 1024
            entry = groups.setdefault(name, {"count": 0, "mem": 0.0, "pid": proc.info["pid"]})
            entry["count"] += 1
            entry["mem"] += mem
        except (psutil.Error, AttributeError):
            continue
    rows = sorted(groups.items(), key=lambda item: item[1]["mem"], reverse=True)[:40]
    if not rows:
        return "Ничего не найдено"
    lines = []
    for name, data in rows:
        suffix = f" x{data['count']}" if data["count"] > 1 else ""
        lines.append(f"{name}{suffix} | PID {data['pid']} | {data['mem']:.0f} MB")
    return "\n".join(lines)


def kill_process(target):
    target = target.strip().lower()
    killed = 0
    if target.isdigit():
        try:
            psutil.Process(int(target)).kill()
            return 1
        except psutil.Error:
            return 0
    names = {target, target + ".exe"}
    for proc in psutil.process_iter(["name"]):
        try:
            if (proc.info["name"] or "").lower() in names:
                proc.kill()
                killed += 1
        except psutil.Error:
            continue
    return killed


def run_command(command):
    flags = getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen(command, shell=True, creationflags=flags)


def show_message(title, text):
    def worker():
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x10 | 0x40000)

    threading.Thread(target=worker, daemon=True).start()


def type_text(text, press_enter=False):
    pyperclip.copy(text)
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "v")
    if press_enter:
        time.sleep(0.1)
        pyautogui.press("enter")


def take_screenshot():
    image = pyautogui.screenshot()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def system_info():
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    uptime = time.time() - psutil.boot_time()
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)
    lines = [
        f"CPU: {cpu}%",
        f"RAM: {mem.percent}% ({mem.used // 1024 // 1024} / {mem.total // 1024 // 1024} MB)",
        f"Аптайм: {hours}ч {minutes}м",
    ]
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            lines.append(f"Диск {part.device}: {usage.percent}% ({usage.used // 1024 ** 3} / {usage.total // 1024 ** 3} GB)")
        except (PermissionError, OSError):
            continue
    return "\n".join(lines)


def shutdown():
    subprocess.Popen("shutdown /s /t 5", shell=True)


def reboot():
    subprocess.Popen("shutdown /r /t 5", shell=True)


def cancel_shutdown():
    subprocess.Popen("shutdown /a", shell=True)


def lock():
    ctypes.windll.user32.LockWorkStation()


def sleep():
    ctypes.windll.powrprof.SetSuspendState(0, 1, 0)


def _volume_interface():
    device = AudioUtilities.GetSpeakers()
    interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def set_volume(percent):
    percent = max(0, min(100, percent))
    _volume_interface().SetMasterVolumeLevelScalar(percent / 100, None)
    return percent


def get_volume():
    return round(_volume_interface().GetMasterVolumeLevelScalar() * 100)


def set_mute(muted):
    _volume_interface().SetMute(1 if muted else 0, None)
