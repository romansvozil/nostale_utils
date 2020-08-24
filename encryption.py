import hashlib
import random
import timeit
from typing import List

"""
SOURCES:
    - https://www.elitepvpers.com/forum/nostale/3935929-eu-client-cryptography.html
    - https://github.com/Gilgames000/go-noscrypto
    - https://github.com/morsisko/NosTale-Auth
"""

KEYS = ' -.0123456789n'


def world_decrypt(data: bytes) -> List[str]:
    output = []
    current_packet = b''
    index = 0

    while index < len(data):
        current_byte = data[index]
        index += 1
        if current_byte == 0xFF:
            output.append(current_packet)
            current_packet = b''
            continue

        length = current_byte & 0x7F

        if (current_byte & 0x80) != 0:
            while length != 0:
                if index <= len(data):
                    current_byte = data[index]
                    index += 1
                    first_index = (((current_byte & 0xF0) >> 4) - 1) % 256
                    first = ord(KEYS[first_index]) if first_index != 14 else ord('\u0000') if first_index != 255 else ord('?')
                    if first != 0x6E:
                        current_packet += first
                    if length <= 1:
                        break
                    second_index = ((current_byte & 0xF) - 1) % 256
                    second = ord(KEYS[second_index]) if second_index != 14 else ord('\u0000') if second_index != 255 else ord('?')
                    if second != 0x6E:
                        current_packet += second
                    length -= 2
                else:
                    length -= 1
        else:
            while length != 0:
                if index < len(data):
                    current_packet += data[index] ^ 0xFF
                    index += 1
                elif index == len(data):
                    current_packet += 0xFF
                    index += 1
                length -= 1
    return [packet.decode('utf-8') for packet in output]


def world_encrypt(packet: str, session_number: int, session=False) -> bytearray:
    fst = first_encryption(packet.encode('utf-8'))
    snd = second_encryption(bytearray(fst), session_number, session)
    return bytearray(snd)


def first_encryption(packet: bytes) -> List[int]:
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
                        encrypted_packet.append(length - i)
                    else:
                        encrypted_packet.append(0x7E)
                        sequences -= 1
                        sequence_counter += 1
                encrypted_packet.append(packet[last_position] ^ 0xFF)
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
                        encrypted_packet.append((length - i) | 0x80)
                    else:
                        encrypted_packet.append(0x7E | 0x80)
                        sequences -= 1
                        sequence_counter += 1

                current_byte = packet[last_position]
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
                        encrypted_packet.append((current_byte << 4) % 256)
                    else:
                        encrypted_packet[len(encrypted_packet) - 1] = (encrypted_packet[len(
                            encrypted_packet) - 1] | current_byte) % 256
                last_position += 1
    encrypted_packet.append(0xFF)
    return encrypted_packet


def bit_neg(num: int) -> int:
    return 256 - num


def c_byte(num: int) -> int:
    return c_byte(num + 256) if num < -128 else (c_byte(num - 256) if num > 127 else num)


def second_encryption(packet: bytes, encryption_key: int, session: bool) -> List[int]:
    session_number = c_byte((encryption_key >> 6) & 0xFF & 0x80000003)

    result = [0] * len(packet)

    if session_number < 0:
        session_number = c_byte(((session_number - 1) | 0xFFFFFFFC) + 1)

    session_key = (encryption_key & 0xFF) % 256

    if session:
        session_number = -1

    if session_number == 0:
        for i in range(len(result)):
            result[i] = (packet[i] + session_key + 0x40) % 256
    elif session_number == 1:
        for i in range(len(packet)):
            result[i] = (packet[i] - (session_key + 0x40)) % 256
    elif session_number == 2:
        for i in range(len(packet)):
            result[i] = ((packet[i] ^ 0xC3) + session_key + 0x40) % 256
    elif session_number == 3:
        for i in range(len(packet)):
            result[i] = ((packet[i] ^ 0xC3) - (session_key + 0x40)) % 256
    else:
        for i in range(len(packet)):
            result[i] = (packet[i] + 0x0F) % 256
    return result


def generate_packet_mask(packet: bytes) -> List[bool]:
    mask = [True] * len(packet)
    for index, character in enumerate(packet):
        if character in [35, 47, 37]:
            mask[index] = False
            continue
        character = c_byte(character - 0x20)
        if character == 0:
            mask[index] = True
            continue
        character = c_byte(character + 0xF1)
        if character < 0:
            mask[index] = True
            continue
        character = c_byte(character - 0xB)
        if character < 0:
            mask[index] = True
            continue
        if c_byte(character - 0xC5) == 0:
            mask[index] = True
            continue
        mask[index] = False
    return mask


def login_decrypt(packet: bytes) -> str:
    result = b''
    for bt in packet:
        result += (bt - 0xF) % 256
    return result.decode('utf-8')


def login_encrypt(packet: str) -> bytearray:
    result = bytearray(len(packet) + 1)
    encoded_data = packet.encode("utf-8")
    for i, value in enumerate(encoded_data):
        result[i] = ((value ^ 0xC3) + 0xF) % 256
    result[-1] = 0xD8
    return result


def create_login_packet(session_token: int, installation_guid: str,
                        region_code: int, version: str,
                        nostale_client_x_hash: str, nostale_client_hash: str):
    random_value = random.randint(0, 16 ** 8)
    client_md5 = hashlib.md5((nostale_client_x_hash.upper() + nostale_client_hash.upper()).encode("ascii"))
    return f"NoS0577 {session_token} {installation_guid} {random_value:08x} {region_code}{chr(0xB)}{version} 0 {client_md5.hexdigest().upper()}"


def use_numba():
    """
    First time you call these functions it can take up to few seconds to compile them with numba
    """
    import numba as nb
    global first_encryption, second_encryption, generate_packet_mask, world_decrypt, c_byte, bit_neg
    first_encryption = nb.njit(first_encryption)
    second_encryption = nb.njit(second_encryption)
    generate_packet_mask = nb.njit(generate_packet_mask)
    world_decrypt = nb.njit(world_decrypt)
    print(nb.typeof(world_decrypt))
    c_byte = nb.njit(c_byte)
    bit_neg = nb.njit(bit_neg)


if __name__ == '__main__':
    print([world_encrypt(f"#u_i^1^{i}^2^{i}^1", i) for i in range(30000)])
    # print(world_encrypt("pulse 60", 5))
    # print(timeit.timeit(lambda: world_encrypt("pulse 60", 5), number=100000))
