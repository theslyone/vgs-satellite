from socket import socket


class DataSizeOverflowError(Exception):
    pass


def read_uint_from_sock(sock: socket) -> int:
    size = 0
    shift = 0

    for i in range(10):
        byte = int.from_bytes(sock.recv(1), "little")
        if byte < 0x80:
            if i == 9 and byte > 1:
                raise DataSizeOverflowError()
            return size | (byte << shift)
        size |= (byte & 0x7F) << shift
        shift += 7

    raise DataSizeOverflowError()


def put_uint_to_sock(unit: int, sock: socket):
    while unit >= 0x80:
        sock.send(((unit & 0xFF) | 0x80).to_bytes(1, "little"))
        unit >>= 7
    sock.send((unit & 0xFF).to_bytes(1, "little"))
