import os
import sys
from dataclasses import dataclass
from random import randint
from threading import Thread
from time import sleep, time
from typing import List
import logging

sys.path.insert(1, os.path.join(sys.path[0], '..'))
from utils import TCPClient


logging.basicConfig(level=logging.INFO)

NPC_TYPE = 2

# packets
MINE_PACKET = 'npc_req 2 {id}'
NCIF_PACKET = 'ncif 2 {id}'


# settings
NPC_ID = 2365           # npc to collect
MINING_TIME = 7         # how long it takes to collect one thing in seconds
MINING_TIMEOUT = 45     # time to wait between collecting the same thing
COLLECT_RANGE = 7       # collect range ;)

# globals
npcs = {}  # carrots currently on map
player_position = (-1, -1)


@dataclass
class NPC:
    x: int
    y: int
    id: int
    last_mine: int  # time in seconds

    @classmethod
    def from_packet(cls, packet: List[str]):
        return cls(int(packet[5]),int(packet[6]), int(packet[4]), 0)

    def mine(self, client: TCPClient):
        client.send(NCIF_PACKET.format(id=self.id))
        client.send(MINE_PACKET.format(id=self.id))

        for _ in range(MINING_TIME):
            sleep(1)
            client.send(NCIF_PACKET.format(id=self.id))
        self.last_mine = time() + randint(3, 10)

    def in_range(self):
        return ((self.x - player_position[0]) ** 2 + (self.y - player_position[1]) ** 2) ** 1/2 <= COLLECT_RANGE

    def can_collect(self):
        return self.last_mine + MINING_TIMEOUT < time()


def sent_packets_logger(packet: List[str]):
    if packet[0] == '1':
        logging.debug(f'Send: {" ".join(packet[1:])}')


def npc_handler(packet: List[str]):
    if len(packet) < 2 or packet[0] != '0' or packet[1] != 'in':
        return
    if int(packet[2]) != NPC_TYPE or int(packet[3]) != NPC_ID:
        return
    npc = NPC.from_packet(packet)
    logging.info(f'Found npc with id: {npc.id} on position ({npc.x}, {npc.y})')
    npcs[npc.id] = npc


def map_change_handler(packet: List[str]):
    if len(packet) < 2 or packet[0] != '0' or packet[1] != 'c_map':
        return
    logging.info('Map has been changed.')
    npcs.clear()


def position_handler(packet: List[str]):
    if len(packet) < 2 or packet[1] != 'walk':
        return
    global player_position
    player_position = int(packet[2]), int(packet[3])


def init_handlers(client: TCPClient):
    for handler in [npc_handler, map_change_handler, position_handler, sent_packets_logger]:
        client.add_callback(handler)


def mine(client: TCPClient):
    while True:
        if not npcs:
            logging.error('No npc\'s on map.')
            return

        for npc in npcs.values():
            if npc.in_range() and npc.can_collect():
                logging.info(f'Mining npc with id: {npc.id}')
                npc.mine(client)
            sleep(1)


def main():
    port = sys.argv[1:]
    if not port or not port[0].isdigit():
        logging.error('Port was not specified or is written in wrong format.')
        return -1

    port = int(port[0])
    client = TCPClient(port)
    init_handlers(client)
    client.serve()

    input('Start/Stop on enter..')
    thread = Thread(target=mine, args=[client])
    thread.daemon = True
    thread.start()
    logging.info('Bot is running..')
    input()
    return 0


if __name__ == '__main__':
    exit(main())