import asyncio
from typing import List

import utils
from dataclasses import dataclass

pl_1_port = 23121
pl_2_port = 3234

@dataclass
class Player:
    skills: List  # List of cast_id, self_cast pairs
    id: int = -1


def create_id_handler(player: Player):
    def inner(packet: List[str]):
        if packet[1] == "c_info":
            player.id = int(packet[7])
    return inner


def setup_pl_wrapper(port: int, player: Player):
    pl_wrapper = utils.TCPClient(port)
    pl_wrapper.serve()
    pl_wrapper.add_callback(create_id_handler(player))
    return pl_wrapper


async def cast_all_spells(pl_wrapper: utils.TCPClient, player: Player, target_id: int):
    for skill in player.skills:
        target_id = player.id if skill[1] else target_id
        pl_wrapper.send(f"u_s {skill[0]} 1 {target_id}")
        await asyncio.sleep(1)

async def main():
    # create player instance for each client
    player_1 = Player([])  # here you have to initialize skills
    player_2 = Player([])  # here you have to initialize skills
    # setup packet logger wrappers
    pl_1 = setup_pl_wrapper(pl_1_port, player_1)
    pl_2 = setup_pl_wrapper(pl_2_port, player_2)
    while True:
        # wait for some signal, could be setup_pl_wrapper.wait_for_packet(Sel..)
        input("Press enter for invite.")
        # send invite
        # TODO: idk the packet :(
        # alt_1.send(the send invite packet)

        # wait for player to accept invite
        packet = await pl_1.wait_for_packet([utils.Selector.header("in"),        # if someone walks on map
                                             utils.Selector.index_eq(2, "1")])  # select only player entities

        player_id = int(packet[5])

        await asyncio.sleep(2)  # wait few secs
        # cast all spells
        await asyncio.gather(cast_all_spells(pl_1, player_1, player_id),
                             cast_all_spells(pl_2, player_2, player_id))
