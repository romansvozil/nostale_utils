# A set of utils that can be used with Nostale PacketLogger

## Example 1:
Inject packet logger into all Nostale instances, hide packetlogger and rename Nostale client to this format 
`Nostale CHAR_ID: {character_name} PL_PORT: {pl_port}`

```python
from utils import setup_all_clients
from asyncio import run

run(setup_all_clients())
```