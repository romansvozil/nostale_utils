import hashlib
import random
import timeit
from typing import List

import numba as nb

"""
SOURCES:
    - https://www.elitepvpers.com/forum/nostale/3935929-eu-client-cryptography.html
    - https://github.com/Gilgames000/go-noscrypto
    - https://github.com/morsisko/NosTale-Auth
"""


KEYS = ' -.0123456789n'


@nb.njit
def world_decrypt(data: bytes):
    output = []
    current_packet = ""
    index = 0

    while index < len(data):
        current_byte = data[index]
        index += 1
        if current_byte == 0xFF:
            output.append(current_packet)
            current_packet = ""
            continue

        length = current_byte & 0x7F

        if (current_byte & 0x80) != 0:
            while length != 0:
                if index <= len(data):
                    current_byte = data[index]
                    index += 1
                    firstIndex = ((current_byte & 0xF0) >> 4) - 1
                    first = KEYS[firstIndex] if firstIndex != 14 else '\u0000' if firstIndex != 255 else '?'
                    if (ord(first) != 0x6E):
                        current_packet += first
                    if (length <= 1):
                        break
                    second_index = (current_byte & 0xF) - 1
                    second = KEYS[second_index] if second_index != 14 else '\u0000' if second_index != 255 else '?'
                    if (ord(second) != 0x6E):
                        current_packet += second
                    length -= 2
                else:
                    length -= 1
        else:
            while length != 0:
                if index < len(data):
                    current_packet += chr(data[index] ^ 0xFF)
                    index += 1
                elif index == len(data):
                    current_packet += chr(0xFF)
                    index += 1
                length -= 1
    return output


def world_encrypt(packet: str, session_number: int, session=False) -> bytes:
    fst = first_encryption(packet)
    snd = second_encryption(bytes(fst), session_number, session)
    return bytes(snd)


@nb.njit
def first_encryption(packet: str) -> List[int]:
    encrypted_packet = []
    packet_mask = generate_packet_mask(packet)
    packet_length = len(packet)

    sequence_counter = 0
    current_position = 0

    while current_position <= packet_length:
        last_position = current_position
        while current_position < packet_length and not packet_mask[current_position]:
            current_position += 1

        if current_position > 0:
            length = current_position - last_position
            sequences = length // 0x7E
            for i in range(length):
                if i == sequence_counter * 0x7E:
                    if sequences == 0:
                        encrypted_packet.append(length-i)
                    else:
                        encrypted_packet.append(0x7E)
                        sequences -= 1
                        sequence_counter += 1
                encrypted_packet.append(ord(packet[last_position]) ^ 0xFF)
                last_position += 1

        if current_position >= packet_length:
            break

        last_position = current_position
        while current_position < packet_length and packet_mask[current_position]:
            current_position += 1

        if current_position > 0:
            length = current_position - last_position
            sequences = length // 0x7E
            for i in range(length):
                if i == sequence_counter * 0x7E:
                    if sequences == 0:
                        encrypted_packet.append((length-i) | 0x80)
                    else:
                        encrypted_packet.append(0x7E | 0x80)
                        sequences -= 1
                        sequence_counter += 1

                current_byte = ord(packet[last_position])
                if current_byte == 0x20:
                    current_byte = 1
                elif current_byte == 0x2D:
                    current_byte = 2
                elif current_byte == 0x2E:
                    current_byte = 3
                elif current_byte == 0xFF:
                    current_byte = 0xE
                else:
                    current_byte -= 0x2C

                if current_byte != 0x00:
                    if i % 2 == 0:
                        encrypted_packet.append(current_byte << 4)
                    else:
                        encrypted_packet[len(encrypted_packet)-1] |= current_byte
                last_position += 1
    encrypted_packet.append(0xFF)
    return encrypted_packet


@nb.njit
def bit_neg(num: int):
    return 256 - num


@nb.njit
def c_byte(num: int):
    return c_byte(num + 256) if num < -128 else (c_byte(num - 256) if num > 127 else num)


@nb.njit
def second_encryption(packet: bytes, session_number: int, session: bool) -> List[int]:
    buffer = []
    session_key = (session_number + 0x40) % 256
    xor_key = 0x00

    session_number = (session_number >> 6) & 0x03

    if session:
        session_number = -1

    if session_number == 1:
        session_key = bit_neg(session_key)
    elif session_number == 2:
        xor_key = 0xC3
    elif session_number == 3:
        session_key = bit_neg(session_key)
        xor_key = 0xC3
    for character in packet:
        buffer.append(((character ^ xor_key) + session_key) % 256)
    return buffer


@nb.njit
def generate_packet_mask(packet: str):
    mask = [True] * len(packet)
    for index, character in enumerate(packet):
        o_character = ord(character)
        if character in "#/%":
            mask[index] = False
            continue
        o_character = c_byte(o_character - 0x20)
        if o_character == 0:
            mask[index] = True
            continue
        o_character = c_byte(o_character + 0xF1)
        if o_character < 0:
            mask[index] = True
            continue
        o_character = c_byte(o_character - 0xB)
        if o_character < 0:
            mask[index] = True
            continue
        if c_byte(o_character - 0xC5) == 0:
            mask[index] = True
            continue
        mask[index] = False
    return mask


@nb.njit
def login_decrypt(packet: bytes) -> str:
    result = ''
    for bt in packet:
        result += chr(bt - 0xF)
    return result


@nb.njit
def login_encrypt(packet: str) -> bytearray:
    result = bytearray(len(packet) + 1)
    encoded_data = bytearray(packet.encode("ascii"))
    for i, value in enumerate(encoded_data):
        result[i] = ((value ^ 0xC3) + 0xF) % 256
    result[-1] = 0xD8
    return result


def create_login_packet(session_token: str, installation_guid: str,
                        region_code: int, version: str,
                        nostale_client_x_hash: str, nostale_client_hash: str):
    random_value = str(hex(random.randint(0, 16**8)))
    client_md5 = hashlib.md5((nostale_client_x_hash.upper() + nostale_client_hash.upper()).encode("ascii"))
    return f"NoS0577 {session_token} {installation_guid} {random_value:08x} {region_code}\xB{version} 0 {client_md5}"


if __name__ == '__main__':
    print(world_encrypt("pulse 60", 5))
    print(timeit.timeit(lambda: world_encrypt("pulse 60", 5), number=100000))