import ctypes
import io
import os
import socket
import subprocess
import threading
import time

import psutil
import pyautogui
import pyperclip
from comtypes import CLSCTX_ALL
from ctypes import POINTER, cast
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


# ─── Процессы ──────────────────────────────────────────────────────────────────

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


def top_processes(limit=15):
    """Топ процессов по CPU + RAM в виде таблицы."""
    procs = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
        try:
            cpu = proc.info["cpu_percent"] or 0.0
            mem = (proc.info["memory_info"].rss / 1024 / 1024) if proc.info["memory_info"] else 0.0
            procs.append((proc.info["name"] or "?", proc.info["pid"], cpu, mem))
        except (psutil.Error, AttributeError):
            continue
    # сортируем по CPU, потом RAM
    procs.sort(key=lambda x: (x[2], x[3]), reverse=True)
    procs = procs[:limit]
    header = f"{'Процесс':<22} {'PID':>6} {'CPU':>6} {'RAM':>8}"
    sep = "─" * len(header)
    lines = [header, sep]
    for name, pid, cpu, mem in procs:
        name_trunc = name[:21] if len(name) > 21 else name
        lines.append(f"{name_trunc:<22} {pid:>6} {cpu:>5.1f}% {mem:>6.0f}MB")
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


# ─── Команды / ввод ────────────────────────────────────────────────────────────

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


def hotkey(keys: str):
    """Нажать горячую клавишу. keys — строка вида 'win+l' или 'alt+f4'."""
    parts = [k.strip().lower() for k in keys.replace("+", " ").split()]
    pyautogui.hotkey(*parts)


def switch_tab():
    """Alt+Tab — переключение между окнами."""
    pyautogui.hotkey("alt", "tab")


# ─── Скриншот ──────────────────────────────────────────────────────────────────

def take_screenshot():
    image = pyautogui.screenshot()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


# ─── Система ───────────────────────────────────────────────────────────────────

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
            lines.append(
                f"Диск {part.device}: {usage.percent}% "
                f"({usage.used // 1024 ** 3} / {usage.total // 1024 ** 3} GB)"
            )
        except (PermissionError, OSError):
            continue
    return "\n".join(lines)


def active_window_title():
    """Заголовок активного окна."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value or "(без заголовка)"
    except Exception as e:
        return f"Ошибка: {e}"


def clipboard_get():
    try:
        return pyperclip.paste() or "(буфер пуст)"
    except Exception as e:
        return f"Ошибка: {e}"


# ─── Питание ───────────────────────────────────────────────────────────────────

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


# ─── Звук ──────────────────────────────────────────────────────────────────────

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


# ─── Файлы ─────────────────────────────────────────────────────────────────────

def list_drives():
    """Список дисков (This PC)."""
    lines = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            free_gb = usage.free // 1024 ** 3
            total_gb = usage.total // 1024 ** 3
            lines.append(f"{part.device}  {free_gb} GB свободно из {total_gb} GB")
        except (PermissionError, OSError):
            lines.append(f"{part.device}  (нет доступа)")
    return lines  # список строк


def list_dir(path: str):
    """Содержимое папки. Возвращает (dirs, files)."""
    dirs, files = [], []
    try:
        for entry in sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower())):
            if entry.is_dir(follow_symlinks=False):
                dirs.append(entry.name)
            else:
                size = entry.stat().st_size
                if size >= 1024 ** 3:
                    size_str = f"{size / 1024 ** 3:.1f} GB"
                elif size >= 1024 ** 2:
                    size_str = f"{size / 1024 ** 2:.1f} MB"
                elif size >= 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size} B"
                files.append((entry.name, size_str))
    except PermissionError:
        pass
    return dirs, files


def get_file(path: str) -> io.BytesIO:
    """Читает файл и возвращает BytesIO для отправки в Telegram."""
    buf = io.BytesIO()
    with open(path, "rb") as f:
        buf.write(f.read())
    buf.seek(0)
    buf.name = os.path.basename(path)
    return buf


def save_file(path: str, data: bytes):
    """Сохраняет байты в файл."""
    with open(path, "wb") as f:
        f.write(data)


# ─── Сеть ──────────────────────────────────────────────────────────────────────

def get_external_ip():
    """Внешний IP через подключение к DNS Google (без HTTP)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(3)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        return f"Ошибка: {e}"


def get_network_interfaces():
    """Список сетевых интерфейсов и их IP."""
    lines = []
    for iface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                lines.append(f"{iface}: {addr.address}")
    return lines or ["Интерфейсы не найдены"]


def get_connections():
    """Активные TCP-соединения."""
    lines = []
    try:
        for conn in psutil.net_connections(kind="tcp"):
            if conn.status == "ESTABLISHED" and conn.raddr:
                laddr = f"{conn.laddr.ip}:{conn.laddr.port}"
                raddr = f"{conn.raddr.ip}:{conn.raddr.port}"
                # имя процесса
                try:
                    pname = psutil.Process(conn.pid).name() if conn.pid else "?"
                except psutil.Error:
                    pname = "?"
                lines.append(f"{pname}  {laddr} → {raddr}")
    except (psutil.AccessDenied, PermissionError):
        return ["Нет доступа (запусти от администратора)"]
    return lines[:40] or ["Нет активных соединений"]
