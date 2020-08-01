import os
import sys
from dataclasses import dataclass
from random import randint
from threading import Thread
from time import sleep, time
from typing import List
import logging

logging.basicConfig(level=logging.INFO)

sys.path.insert(1, os.path.join(sys.path[0], '..'))

from utils import TCPClient

NPC_ID = 2
CARROT_ID = 2365

# packets
MINE_CARROT_PACKET = 'npc_req 2 {carrot_id}'
NCIF_PACKET = 'ncif 2 {carrot_id}'

MINING_TIME = 7

# settings
CARROT_TIMEOUT = 45
COLLECT_RANGE = 7


carrots = {}  # carrots currently on map

player_position = (-1, -1)


@dataclass
class Carrot:
    x: int
    y: int
    id: int
    last_mine: int  # time in seconds

    @classmethod
    def from_packet(cls, packet: List[str]):
        return cls(int(packet[5]),int(packet[6]), int(packet[4]), 0)

    def mine(self, client: TCPClient):
        client.send(MINE_CARROT_PACKET.format(carrot_id=self.id))

    def in_range(self):
        return ((self.x - player_position[0]) ** 2 + (self.y - player_position[1]) ** 2) ** 1/2 <= COLLECT_RANGE


def sent_packets_logger(packet: List[str]):
    if packet[0] == '1':
        logging.debug(f'Send: {" ".join(packet[1:])}')


def carrot_handler(packet: List[str]):
    if len(packet) < 2 or packet[0] != '0' or packet[1] != 'in':
        return
    if int(packet[2]) != NPC_ID or int(packet[3]) != CARROT_ID:
        return
    carrot = Carrot.from_packet(packet)
    logging.info(f'Found carrot with id: {carrot.id} on position ({carrot.x}, {carrot.y})')
    carrots[carrot.id] = carrot


def map_change_handler(packet: List[str]):
    if len(packet) < 2 or packet[0] != '0' or packet[1] != 'c_map':
        return
    logging.info('Map has been changed.')
    carrots.clear()


def position_handler(packet: List[str]):
    if len(packet) < 2 or packet[1] != 'walk':
        return
    global player_position
    player_position = int(packet[2]), int(packet[3])


def init_handlers(client: TCPClient):
    for handler in [carrot_handler, map_change_handler, position_handler, sent_packets_logger]:
        client.add_callback(handler)


def mine(client: TCPClient):
    while True:
        if not carrots:
            logging.error('No carrots on map.')
            return

        for carrot in carrots.values():
            if carrot.in_range() and carrot.last_mine + CARROT_TIMEOUT < time():
                client.send(NCIF_PACKET.format(carrot_id=carrot.id))
                logging.info(f'Mining carrot with id: {carrot.id}')
                carrot.mine(client)
                for _ in range(MINING_TIME):
                    sleep(1)
                    client.send(NCIF_PACKET.format(carrot_id=carrot.id))
                carrot.last_mine = time() + randint(3, 10)
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