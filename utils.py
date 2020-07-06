import asyncio
from ctypes import *
from typing import List, Dict
import win32api, win32process, win32con, win32gui
import psutil

from injector import Injector

ReadProcessMemory = windll.kernel32.ReadProcessMemory

__NOSTALE_EXE_BASE_ADDRESS = 0x400000

# first account name pointer
# "NostaleClientX.exe"+00486014  + 80  + 0
__FIRST_CHARACTER = [0x00486014, 0x80, 0x0]

# second account name pointer
# "NostaleClientX.exe"+00486014  + 12C + 0
__SECOND_CHARACTER = [0x00486014, 0x12C, 0x0]

# third account name pointer
# "NostaleClientX.exe"+00486014  + 1D8 + 0
__THIRD_CHARACTER = [0x00486014, 0x1D8, 0x0]

# fourth account name pointer
# "NostaleClientX.exe"+00486014  + 284 + 0
__FOURTH_CHARACTER = [0x00486014, 0x284, 0x0]

# current account index pointer
# "NostaleClientX.exe"+00486014  + 68
__CHARACTER_INDEX = [0x00486014, 0x68]

__INDEXES = {
    0: __FIRST_CHARACTER,
    1: __SECOND_CHARACTER,
    2: __THIRD_CHARACTER,
    3: __FOURTH_CHARACTER,
}

# should be able to get it from process.exe()
__PACKET_LOGGER_PATH = r"C:\Program Files (x86)\GameforgeClient\Nostale\en-GB\PacketLogger.dll"


def _read_pointers(process_handle, base: int, offsets: List[int], pointer_size: int = 4) -> int:
    # returns final address
    for index, offset in enumerate(offsets):
        base += offset
        if index == len(offsets)-1:
            return base
        buffer = c_char_p()
        ReadProcessMemory(process_handle.handle, base, byref(buffer), pointer_size, 0)
        base = int.from_bytes(buffer, 'little')
    return base


def _read_bytes(process_handle, address: int, size: int = 4) -> bytes:
    buffer = create_string_buffer(size)
    ReadProcessMemory(process_handle.handle, address, byref(buffer), size, 0)
    return bytes(buffer)


def _read_ascii_string(process_handle, address: int) -> str:
    result = b""
    current_byte = _read_bytes(process_handle, address, 1)
    while int.from_bytes(current_byte, 'little'):
        address += 1
        result += current_byte
        current_byte = _read_bytes(process_handle, address, 1)
    return result.decode("ascii")


def read_current_name(pid: int) -> str:
    process_handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)
    assert process_handle
    account_index = _read_bytes(
        process_handle,
        _read_pointers(
            process_handle,
            __NOSTALE_EXE_BASE_ADDRESS,
            __CHARACTER_INDEX
        )
    )
    account_index = int.from_bytes(account_index, 'little')
    if account_index == 255:
        return "Character not selected"

    result = _read_ascii_string(
        process_handle,
        _read_pointers(
            process_handle,
            __NOSTALE_EXE_BASE_ADDRESS,
            __INDEXES[account_index]
        ),
    )

    win32api.CloseHandle(process_handle.handle)
    return result


def get_nostale_windows():
    def callback(hwnd, hwnds):
        if not win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
            return
        if win32gui.GetWindowText(hwnd) != "NosTale":
            return
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        hwnds.append({"pid": pid, "hwnd": hwnd})

    windows = []
    win32gui.EnumWindows(callback, windows)
    return windows


def get_nostale_windows_wo_packet_logger():
    windows = []
    for window in get_nostale_windows():
        process = psutil.Process(window["pid"])
        for connection in process.connections():
            if connection.laddr and connection.laddr.ip == "127.0.0.1":
                break
        else:
            windows.append(window)
    return windows


def get_packet_logger_port(packet_logger: Dict[str, int]):
    process = psutil.Process(packet_logger["pid"])
    for connection in process.connections():
        if connection.laddr and connection.laddr.ip == "127.0.0.1":
            return connection.laddr.port
    return 0


def get_packet_logger_windows():
    def callback(hwnd, hwnds):
        if not win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
            return
        if "PacketLogger" not in win32gui.GetWindowText(hwnd):
            return
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        hwnds.append({"pid": pid, "hwnd": hwnd})

    windows = []
    win32gui.EnumWindows(callback, windows)
    return windows


def inject_packet_logger(pid: int):
    injector = Injector()
    injector.load_from_pid(pid)
    injector.inject_dll(__PACKET_LOGGER_PATH)


def hide_window(window: Dict[str, int]):
    style = win32gui.GetWindowLong(window["hwnd"], win32con.GWL_STYLE)
    style &= ~(win32con.WS_VISIBLE)
    style |= win32con.WS_EX_TOOLWINDOW
    style &= ~(win32con.WS_EX_APPWINDOW)
    win32gui.ShowWindow(window["hwnd"], win32con.SW_HIDE)
    win32gui.SetWindowLong(window["hwnd"], win32con.GWL_STYLE, style)
    win32gui.ShowWindow(window["hwnd"], win32con.SW_SHOW)
    win32gui.ShowWindow(window["hwnd"], win32con.SW_HIDE)


def rename_nostale_window(window: Dict[str, int], packet_logger_port: int):
    win32gui.SetWindowText(
        window["hwnd"],
        f"Nostale CHAR_ID: {read_current_name(window['pid'])} PL_PORT: {packet_logger_port}"
    )


async def setup_client(window):
    inject_packet_logger(window["pid"])
    await asyncio.sleep(1)  # wait for packet logger to start
    packet_logger = list(filter(lambda x: x["pid"] == window["pid"], get_packet_logger_windows()))[0]
    hide_window(packet_logger)
    rename_nostale_window(window, get_packet_logger_port(packet_logger))


async def setup_all_clients():
    windows = get_nostale_windows_wo_packet_logger()
    await asyncio.gather(*[setup_client(window) for window in windows])

if __name__ == '__main__':
    asyncio.run(setup_all_clients())