from multiprocessing import Process, Queue, Pipe
from multiprocessing.connection import Connection
import time

def f(conn: Connection):
    while True:
        req = conn.recv_bytes()
        if req == b'QUIT':
            conn.send_bytes(b'QUITTED')
            exit(1)
        reply = b'mundo'
        conn.send_bytes(reply)

import sys
if __name__ == '__main__':
    print(sys.executable)

    parent_conn, child_conn = Pipe()
    p = Process(target=f, args=(child_conn,))
    p.start()

    start = time.time()
    txs =  200000

    msg = b'Hola'

    for i in range(txs):
        parent_conn.send_bytes(msg)
        reply = parent_conn.recv_bytes()
        if reply != b'mundo':
            print(f"{i} Error: {reply}")

    end = time.time()

    parent_conn.send_bytes(b'QUIT')
    reply = parent_conn.recv_bytes()
    print(f'The child says: {reply}')

    p.join()

    elapsed = end - start
    tx_sec = txs / elapsed

    print(f'Tx/sec: {tx_sec}')