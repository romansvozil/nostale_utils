# A set of utils that can be used with Nostale PacketLogger

## Example 1:
Inject packet logger into all Nostale instances, hide packetlogger and rename Nostale client to this format 
`Nostale CHAR_ID: {character_name} PL_PORT: {pl_port}`
![alt text](https://raw.githubusercontent.com/romansvozil/nostale_packet_logger_utils/master/images/example_1.PNG "Example 1")

```python
from utils import setup_all_clients
from asyncio import run

run(setup_all_clients())
```

# Links:
- [PacketLogger](https://www.elitepvpers.com/forum/nostale-hacks-bots-cheats-exploits/4297215-release-packetlogger.html)
- [Injector](https://github.com/numaru/injector/blob/master/injector.pya)