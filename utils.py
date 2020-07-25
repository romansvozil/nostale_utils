import asyncio
import os.path
import queue
import threading
from typing import List, Dict, Tuple, Callable, Optional

import psutil
import win32con
import win32gui
import win32process

from injector import Injector


def get_nostale_windows() -> List[Dict[str, int]]:
    def callback(hwnd, hwnds):
        if not win32gui.IsWindowEnabled(hwnd):
            return
        if "NosTale" not in win32gui.GetWindowText(hwnd):
            return
        if "[BladeTiger12]" in win32gui.GetWindowText(hwnd):
            return
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        hwnds.append({"pid": pid, "hwnd": hwnd})

    windows = []
    win32gui.EnumWindows(callback, windows)
    return windows


def get_window_pid(window: int) -> int:
    _, pid = win32process.GetWindowThreadProcessId(window)
    return pid


def get_nostale_windows_wo_packet_logger() -> List[Dict[str, int]]:
    windows = []
    for window in get_nostale_windows():
        process = psutil.Process(window["pid"])
        for connection in process.connections():
            if connection.laddr and connection.laddr.ip == "127.0.0.1":
                break
        else:
            windows.append(window)
    return windows


def get_packet_logger_path(nostale_pid: int) -> str:
    process = psutil.Process(nostale_pid)
    return os.path.dirname(process.exe()) + "/PacketLogger.dll"


def get_packet_logger_port(packet_logger: Dict[str, int]) -> int:
    process = psutil.Process(packet_logger["pid"])
    for connection in process.connections():
        if connection.laddr and connection.laddr.ip == "127.0.0.1":
            return connection.laddr.port
    return 0


def get_packet_logger_windows() -> List[Dict[str, int]]:
    def callback(hwnd, hwnds):
        if not win32gui.IsWindowEnabled(hwnd):
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
    injector.inject_dll(get_packet_logger_path(pid))


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
        f"NosTale PL_PORT: {packet_logger_port}"
    )


async def setup_client(window) -> Tuple[int, int]:
    inject_packet_logger(window["pid"])
    await asyncio.sleep(3)  # wait for packet logger to start
    packet_logger = [x for x in get_packet_logger_windows() if x["pid"] == window["pid"]][0]
    hide_window(packet_logger)
    rename_nostale_window(window, get_packet_logger_port(packet_logger))
    return window["pid"], get_packet_logger_port(packet_logger)


async def setup_all_clients() -> List[Tuple[int, int]]:
    windows = get_nostale_windows_wo_packet_logger()
    return await asyncio.gather(*[setup_client(window) for window in windows])


class TCPClient:
    IP: str = "127.0.0.1"
    PACKET_SIZE: int = 4096
    ENCODING: str = "windows-1252"

    def __init__(self, port: int):
        self._port = port
        self._callbacks: List[Callable] = []
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._send_queue: queue.Queue = queue.Queue()

    async def _handle_packet(self, packet: List[str]):
        for callback in self._callbacks:
            callback(packet)

    async def _receive_task(self):
        while True:
            data = await self._reader.read(self.PACKET_SIZE)
            for packet in data.strip().decode(self.ENCODING).split("\r"):
                await self._handle_packet(packet.split())

    async def _send_task(self):
        while True:
            if not self._send_queue.empty():
                self._writer.write((self._send_queue.get() + "\r").encode(self.ENCODING))
                await self._writer.drain()
            else:
                await asyncio.sleep(0.01)

    async def _serve(self):
        self._reader, self._writer = await asyncio.open_connection(self.IP, self._port)
        await asyncio.gather(self._receive_task(), self._send_task())

    def serve(self):
        threading.Thread(target=lambda: asyncio.run(self._serve())).start()

    def send_raw(self, packet: str):
        self._send_queue.put(packet)

    def send(self, packet: str):
        self.send_raw(" ".join(["1", packet]))

    def recv(self, packet: str):
        self.send_raw(" ".join(["0", packet]))

    def add_callback(self, callback: Callable):
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable):
        self._callbacks.remove(callback)

    async def wait_for_packet(self, selectors,
                              timeout: float = None) -> Optional[List[str]]:
        # selectors are functions that takes packet as parameter and returns bool

        result = None
        if not isinstance(selectors, list):
            selectors = [selectors]

        def callback(packet: List[str]):
            nonlocal result
            if all(selector(packet) for selector in selectors):
                result = packet
                self.remove_callback(callback)

        self.add_callback(callback)

        while result is None and (timeout is None or timeout > 0):
            await asyncio.sleep(0.05)
            timeout -= 0.05

        return result


class Selector:
    @classmethod
    def header(cls, header: str) -> Callable:
        def inner(packet: List[str]):
            return len(packet) > 1 and packet[1] == header

        return inner

    @classmethod
    def index_eq(cls, index: int, value: str) -> Callable:
        def inner(packet: List[str]):
            return len(packet) > index and packet[index] == value

        return inner


if __name__ == '__main__':
    ports = asyncio.run(setup_all_clients())
    print(ports)
