import os
from pathlib import Path
from typing import Tuple, Union

import hashlib
import struct
import logging
import time
import asyncio


class MerkleLog:
    def __init__(self, name: str = 'mklog.txt', mkItems: int = 1024, durability:int=2) -> None:
        self.name = name
        self.mkItems = mkItems
        self.durability = durability
        self.records = 0
        self.total_records = 0

        # If required, create a background task which fsyncs every durability secs (or 1 sec as a minimum)
        if self.durability > 0:
            self.fsync_task = asyncio.create_task(self.fsync_background_task(max(self.durability, 1)))

        self.f = open(name, 'w', encoding='utf-8')

    def close(self):
        self.f.close()

    def _hash(self, text: str) -> bytes:
        btext = bytes(text, "utf-8")
        h = hashlib.sha256()
        h.update(btext)
        d = h.digest()
        return d

    def _get_record(self, id: str, value: str) -> str:
        # calculate hashes
        id_hash = self._hash(id)
        value_hash = self._hash(value)

        # Create a parseable string with them
        h= f'{id_hash.hex()}-{value_hash.hex()}\n'
        return h

    async def put(self, id: str, value: str):

        # Get the record to write
        r = self._get_record(id, value)

        # Write the record
        self.f.write(r)

        # Flush the application cache to the operating system
        self.f.flush()

        # Increment the number of records
        self.records += 1
        self.total_records += 1

        # Rotate the files if needed
        if self._need_rotation():
            self._rotate()
            await asyncio.sleep(0)

        # if self.records > 800:
        #     await asyncio.sleep(0)

    def _need_rotation(self) -> bool:

        # Check if maximum number of elements reached
        return True if (self.records >= self.mkItems) else False

    def _rotate(self):

        # Rotate the file:
        # 1. Close current file
        # 2. Rename it, replacing any existing one
        # 3. Create a new file to continue appending to it
        # 4. Reset the counter of records in this file
#        print(f'Rotating with {self.records} record(s)')
        self.f.close()
        os.replace(self.name, self.name + '.1')
        self.f = open(self.name, 'w', encoding='utf-8')
        self.records = 0

        # Process the old file, possibly asynchronously
        self.processFile(self.name + '.1')

        return

    def processFile(self, fileName):
        # This method has to be implemented by a subclass
        pass

    # Create a background task to make sure fsync is called for the last put,
    # even if no more puts are coming
    async def fsync_background_task(self, frequency: int):
        while True:
            await asyncio.sleep(frequency)
            if self.records > 0:
                print(f'BKG: Rotating with {self.total_records}-{self.records} record(s)')
                self._rotate()



async def main():
    outer_loop = 11
    inner_loop = 100000
    operations = outer_loop * inner_loop

    start_time = time.monotonic()
    
    f = MerkleLog(mkItems=1000)

    ops = 0
    for i in range(outer_loop):
        st2 = time.monotonic()
        for j in range(inner_loop):
            await f.put('Identifier', 'This is the value')
            ops += 1

    f.close()

    now = time.monotonic()
    e2 = now - st2

    print(f'Innerloop: {inner_loop/e2}')

    elapsed_time = now - start_time
    operations_second = (operations) / elapsed_time

    print(f"{operations} performed in {elapsed_time} seconds")
    print(f"Iterations/second: {operations_second}")


if __name__ == '__main__':
    asyncio.run(main())

