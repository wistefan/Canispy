import os
from pathlib import Path
from typing import Tuple
import hashlib
import struct
import logging
import time
import asyncio

# The default file name and location
# The default location is in the same directory as this python module
DEFAULT_DIR: Path = Path(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FILE: Path = DEFAULT_DIR / "fifo_file.que"

from merklelib import MerkleTree, beautify

# Create logger
logging.basicConfig(
    format='%(levelname)s - %(asctime)s - %(message)s', level=logging.INFO)
log = logging.getLogger(__name__)

class FullError(Exception):
    pass

class EmptyError(Exception):
    pass

class InvalidFileError(Exception):
    pass

class InvalidHeaderError(Exception):
    pass

class FIFOFile:

    def __init__(self, name: Path = DEFAULT_FILE, truncate: bool = False, maxsize: int = 1000, fsync_time: int = 1) -> None:
        self.name = name
        self.size = maxsize
        self.HEADER_SIZE = 8
        self.RECORD_SIZE = 2 * 32
        self.MIN_OFFSET = self.HEADER_SIZE
        self.MAX_OFFSET = self.HEADER_SIZE + maxsize*self.RECORD_SIZE
        self.merkle_tree = None
        self.merkle_root = None
        self.fsync_time = fsync_time
        self.last_fsync_time = time.monotonic()
        self.header_dirty = False

        # Create the file if it does not exist or we have to truncate it
        if (not name.exists()) or (truncate):
            with open(name, "wb") as f:
                # Write an initial header
                h = self._header_pack(self.HEADER_SIZE, self.HEADER_SIZE)
                f.write(h)
                # Close the file: We need to open the file in "r+b" mode to use "seek"
                f.close()

        # Perform some sanity checks before opening the file
        statinfo = os.stat(name)
        filesize = statinfo.st_size
        if filesize < self.HEADER_SIZE:
            raise InvalidFileError("File size smaller than header")

        payload = filesize - self.HEADER_SIZE
        if (payload % self.RECORD_SIZE) > 0:
            raise InvalidFileError("File size not a multiple of record size")

        # Open the file in read/write mode so we can seek
        # Leave the file open until the FIFO queue is explicitly closed
        self.f = open(name, "r+b")

        # Read the header
        h = self.f.read(self.HEADER_SIZE)
        if len(h) != self.HEADER_SIZE:
            self.f.close()
            raise InvalidHeaderError(f"Invalid header length, read {len(h)} bytes")
        # Unpack it
        self.head, self.tail = self._header_unpack(h)

        # Check if head pointer seems valid
        if self.head < self.HEADER_SIZE or self.head > filesize:
            self.f.close()
            raise InvalidHeaderError("Head value is invalid")
        payload = self.head - self.HEADER_SIZE
        if (payload % self.RECORD_SIZE) > 0:
            self.f.close()
            raise InvalidHeaderError("Head value not a multiple of record size")

        # Check if tail pointer seems valid
        if self.tail < self.HEADER_SIZE or self.tail > filesize:
            self.f.close()
            raise InvalidHeaderError("Tail value is invalid")
        payload = self.tail - self.HEADER_SIZE
        if (payload % self.RECORD_SIZE) > 0:
            self.f.close()
            raise InvalidHeaderError("Tail value not a multiple of record size")
        
        self.fsync_task = None

    def close(self):
        self.fsync_task.cancel()
        self.f.close()
                
    def put(self, id: str, value: str):

        # On first put, create a background task which fsyncs every fsync_time (or 1 sec as a minimum)
        if self.fsync_task is None and self.fsync_time > 0:
            self.fsync_task = asyncio.create_task(self.fsync_background_task(max(self.fsync_time, 1)))

        # The queue is full if incrementing the head it is equal to the tail
        next_head = self._next_offset(self.head)
        if next_head == self.tail:
            raise FullError("Queue is full")

        # Build the record to store
        r = self._record_pack(id, value)

        # Write to where the head points
        self.f.seek(self.head)
        self.f.write(r)

        # Update the head
        self.head = next_head

        # Write to disk the updated header
        self._write_header()

    def get(self) -> Tuple:

        # Get the first element
        id_hash, value_hash = self.peek()

        # Update the tail
        self.tail = self._next_offset(self.tail)

        # Write the updated header
        self._write_header()

        return (id_hash, value_hash)

    def peek(self) -> Tuple:

        # The queue is empty if head and tail are equal
        if self.head == self.tail:
            raise EmptyError("Queue empty")
        
        # Read from the tail
        self.f.seek(self.tail)
        r_raw = self.f.read(self.RECORD_SIZE)
        if len(r_raw) != self.RECORD_SIZE:
            raise Exception(f"Error reading record, read {len(r_raw)} bytes")
        
        # Read from the byte array
        id_hash, value_hash = self._record_unpack(r_raw)

        return (id_hash, value_hash)

    def _write_header(self):
        # Write the updated header, flushing all buffers to disk
        h = self._header_pack(self.head, self.tail)
        self.f.seek(0)
        self.f.write(h)
        current_time = time.monotonic()
        elapsed = current_time - self.last_fsync_time

        if self.fsync_time == 0 or elapsed > self.fsync_time:
            self.f.flush()
            os.fsync(self.f.fileno())
            self.last_fsync_time = current_time
            self.header_dirty = False
        else:
            self.header_dirty = True

    def _force_write_header(self):
        # Write the updated header, flushing all buffers to disk
        h = self._header_pack(self.head, self.tail)
        self.f.seek(0)
        self.f.write(h)
        self.f.flush()
        os.fsync(self.f.fileno())
        self.last_fsync_time = time.monotonic()
        self.header_dirty = False

    def num_elements(self) -> int:
        if self.head >= self.tail:
            s = (self.head - self.tail) // self.RECORD_SIZE
        else:
            s = self.size - ((self.tail - self.head) // self.RECORD_SIZE) + 1
        return s

    def empty(self) -> bool:
        # If head == tail then the queue is empty
        return (self.head == self.tail)

    def full(self) -> bool:
        n = self._next_offset(self.head)
        return (n == self.tail)
        
    def _next_offset(self, offset) -> int:
        t = offset + self.RECORD_SIZE
        if t > self.MAX_OFFSET:
            t = self.MIN_OFFSET
        return t

    def _hash(self, text: str) -> bytes:
        btext = bytes(text, "utf-8")
        h = hashlib.sha256()
        h.update(btext)
        d = h.digest()
        return d

    def _record_pack(self, id: str, value: str) -> bytes:
        id_hash = self._hash(id)
        value_hash = self._hash(value)
        h = struct.pack("32s32s", id_hash, value_hash)
        return h

    def _record_unpack(self, rec: bytes) -> Tuple:
        r = struct.unpack("32s32s", rec)
        return r

    def _header_pack(self, head: int, tail: int) -> bytes:
        h = struct.pack(">LL", head, tail)
        return h

    def _header_unpack(self, rec: bytes) -> Tuple:
        r = struct.unpack(">LL", rec)
        return r


    # Create a background task to make sure fsync is called for the last put,
    # even if no more puts are coming
    async def fsync_background_task(self, frequency: int):
        while True:
            print("Inside background task")
            # Check if the header should be flushed and synced to the disk
            if self.header_dirty:
                self._force_write_header()
            # Go to sleep
            await asyncio.sleep(frequency)





#################################

async def main():

    f = FIFOFile(Path("perico.txt"), truncate=True, maxsize=20000, fsync_time=1)

    operations = 0
    global_iterations = 100
    iterations = 1000
    start_time = time.monotonic()

    for j in range(global_iterations):
        for i in range(iterations):
            f.put("12345", "Hola que tal")
            id, value = f.get()
            f.put("12345", "Hola que tal")
            id, value = f.get()
            operations += 4
        await asyncio.sleep(0)

    elapsed_time = time.monotonic() - start_time
    operations_second = (operations) / elapsed_time

    print(f"{operations} performed in {elapsed_time} seconds")
    print(f"Iterations/second: {operations_second}")

    print("Sleeping for the first time")
    await asyncio.sleep(3)
    print("last put")
    f.put("acaca", "Hola")
    f.put("acaca", "Hola")
    print("Sleeping for the second time")
    await asyncio.sleep(3)
    f.close()

if __name__ == '__main__':
    asyncio.run(main())

