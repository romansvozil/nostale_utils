# NosTale utils

## Installation:
```shell script
pip install -r requrements.txt
```

## Example 1:
Get nostale Client and ClientX info
```python
from nostale_version import NostaleDownloader
from asyncio import run

print(run(NostaleDownloader.get_client_info('en')))

# Output: 
# ClientInfo(locale='en', client_x_hash='2888e0c5e363dfedeb4e43c58de795c0', 
#   client_hash='64b96f54059c7a5830be0c376558048a', client_version='0.9.3.3131')
```

## Example 2:
Creating PacketLoggerWrapper instance and wait on map change
```python
from utils import TCPClient, Selector
from asyncio import run

async def wait_for_map_change():
    packet_logger = TCPClient(8787)
    packet_logger.serve()
    while True:
        print("Waiting for map change.")
        if await packet_logger.wait_for_packet(Selector.header("c_map")):
            print("Map has been changed.")

run(wait_for_map_change())
```

## Example 3:
You can also create custom classes that represents for example your Character
```python
from dataclasses import dataclass
from utils import TCPClient
from time import sleep

@dataclass
class Player:
    id: int = 0
    name: str = 0
    x: int = 0
    y: int = 0
    speed: int = 0

packet_logger = TCPClient(63337)
packet_logger.serve()

player = Player()

def handle_basic_packets(packet):
    if len(packet) < 2:
        # ignore
        return
    if packet[1] == "c_info":
        player.name = packet[2]
        player.id = int(packet[7])
    elif packet[1] == "walk":
        player.x = int(packet[2])
        player.y = int(packet[3])
        player.speed = int(packet[5])
    # and many more packets

packet_logger.add_callback(handle_basic_packets)

while True:
    print(player)
    sleep(1)
```

## Example 4:
If you want to hide packetlogger windows, you can do it like this.
```python
from utils import hide_window, get_packet_logger_windows 

for window in get_packet_logger_windows():
    hide_window(window)
```

## Example 5:
Read Nostale client names without having to inject packetlogger
```python
from utils import get_nostale_windows, read_current_name

pid_name_pairs = [(window["pid"], read_current_name(window["pid"])) for window in get_nostale_windows()]
```

# Links:
- [PacketLogger](https://www.elitepvpers.com/forum/nostale-hacks-bots-cheats-exploits/4297215-release-packetlogger.html)
- [Injector](https://github.com/numaru/injector/blob/master/injector.pya)