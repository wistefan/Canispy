import os
from pathlib import Path
from typing import Tuple, Union

import hashlib
import struct
import logging
import time
import asyncio


# The default file name and location
# The default location is in the same directory as this python module
DEFAULT_DIR: Path = Path(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FILE: Path = DEFAULT_DIR / "fifo_file.que"


class FullError(Exception):
    pass

class EmptyError(Exception):
    pass

class InvalidFileError(Exception):
    pass

class InvalidHeaderError(Exception):
    pass

class BaseRotatingHandler():
    """
    Base class for handlers that rotate log files at a certain point.
    Not meant to be instantiated directly.  Instead, use RotatingFileHandler
    or TimedRotatingFileHandler.
    """
    namer = None
    rotator = None

    def __init__(self, filename, mode, encoding=None, delay=False, errors=None):
        """
        Use the specified filename for streamed logging
        """
        logging.FileHandler.__init__(self, filename, mode=mode,
                                     encoding=encoding, delay=delay,
                                     errors=errors)
        self.filename = filename
        self.mode = mode
        self.encoding = encoding
        self.delay = delay
        self.errors = errors


    def put(self, id: str, value: str):

        # On first put, create a background task which fsyncs every fsync_time (or 1 sec as a minimum)
        if self.fsync_task is None and self.fsync_time > 0:
            self.fsync_task = asyncio.create_task(self.fsync_background_task(max(self.fsync_time, 1)))

        try:
            if self.shouldRollover(record):
                self.doRollover()
            logging.FileHandler.emit(self, record)
        except Exception:
            self.handleError(record)

    def rotation_filename(self, default_name):
        """
        Modify the filename of a log file when rotating.

        This is provided so that a custom filename can be provided.

        The default implementation calls the 'namer' attribute of the
        handler, if it's callable, passing the default name to
        it. If the attribute isn't callable (the default is None), the name
        is returned unchanged.

        :param default_name: The default name for the log file.
        """
        if not callable(self.namer):
            result = default_name
        else:
            result = self.namer(default_name)
        return result

    def rotate(self, source, dest):
        """
        When rotating, rotate the current log.

        The default implementation calls the 'rotator' attribute of the
        handler, if it's callable, passing the source and dest arguments to
        it. If the attribute isn't callable (the default is None), the source
        is simply renamed to the destination.

        :param source: The source filename. This is normally the base
                       filename, e.g. 'test.log'
        :param dest:   The destination filename. This is normally
                       what the source is rotated to, e.g. 'test.log.1'.
        """
        if not callable(self.rotator):
            # Issue 18940: A file may not have been created if delay is True.
            if os.path.exists(source):
                os.rename(source, dest)
        else:
            self.rotator(source, dest)

class RotatingFileHandler:
    def __init__(self, filename: Union[str, Path], maxBytes: int=1000, backupCount:int=5):

        # Support filenames as Path objects
        filename = os.fspath(filename)
        # Save the absolute path
        self.baseFilename = os.path.abspath(filename)

        # Open the file for appending
        self.f = open(filename, mode='a', encoding='utf-8')

        self.maxBytes = maxBytes
        self.backupCount = backupCount

    def doRollover(self):
        """
        Do a rollover, as described in __init__().
        """
        # Close the current file, if it is open
        if self.stream:
            self.stream.close()
            self.stream = None
        
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = self.rotation_filename("%s.%d" % (self.baseFilename, i))
                dfn = self.rotation_filename("%s.%d" % (self.baseFilename,
                                                        i + 1))
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = self.rotation_filename(self.baseFilename + ".1")
            if os.path.exists(dfn):
                os.remove(dfn)
            self.rotate(self.baseFilename, dfn)
        if not self.delay:
            self.stream = self._open()

    def shouldRollover(self, record):
        """
        Determine if rollover should occur.

        Basically, see if the supplied record would cause the file to exceed
        the size limit we have.
        """
        msg = "%s\n" % self.format(record)
        self.stream.seek(0, 2)  #due to non-posix-compliant Windows feature
        if self.stream.tell() + len(msg) >= self.maxBytes:
            return True
        return False





class FIFOFile:

    def __init__(self, name: Union[str, Path] = DEFAULT_FILE, truncate: bool = False, maxsize: int = 1000, fsync_time: int = 1) -> None:
        self.name = name
        self.maxsize = maxsize
        self.HEADER_SIZE = 8
        self.RECORD_SIZE = 2 * 32
        self.MIN_OFFSET = self.HEADER_SIZE
        self.MAX_OFFSET = self.HEADER_SIZE + maxsize*self.RECORD_SIZE
        self.merkle_tree = None
        self.merkle_root = None
        self.fsync_time = fsync_time
        self.last_fsync_time = time.monotonic()
        self.header_dirty = False
        self.backupCount = 5
        self.numRecords = 0

        # # Perform some sanity checks before opening the file
        # statinfo = os.stat(name)
        # filesize = statinfo.st_size

        # if (filesize % self.RECORD_SIZE) > 0:
        #     raise InvalidFileError("File size not a multiple of record size")

        # Open the file for writing and truncate it if exists
        # Leave the file open until the FIFO queue is explicitly closed

        # Support filenames as Path objects
        name = os.fspath(name)
        # Save the absolute path
        self.name = os.path.abspath(name)

        self.f = open(name, "wb")
        
        self.fsync_task = None

    def close(self):
#        self.fsync_task.cancel()
        self.f.close()
                
    def put(self, id: str, value: str):

        # On first put, create a background task which fsyncs every fsync_time (or 1 sec as a minimum)
        # if self.fsync_task is None and self.fsync_time > 0:
        #     self.fsync_task = asyncio.create_task(self.fsync_background_task(max(self.fsync_time, 1)))

        # Build the record to store
        r = self._record_pack(id, value)

        try:
            if self.shouldRollover(r):
                self.doRollover()

            # Write the record
            self.f.write(r)

            # Make sure it reaches the disk surface
            self.f.flush()
#            os.fsync(self.f.fileno())
            self.numRecords += 1

        except Exception as e:
            raise e


    def doRollover(self):
        """
        Do a rollover
        """
        print("Rollover")
        # Close the current file, if it is open
        if self.f:
            self.f.close()
            self.f = None
        
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = f'{self.name}.{i}'
                dfn = f'{self.name}.{i + 1}'
                print(f'{self.numRecords}: {sfn} -> {dfn}')
                if os.path.exists(sfn):
                    os.replace(sfn, dfn)
            dfn = self.name + ".1"
            os.replace(self.name, dfn)

        self.f = open(self.name, "wb")

    def shouldRollover(self, record: bytes):
        """
        Determine if rollover should occur.

        Basically, see if the supplied record would cause the file to exceed
        the size limit we have.
        """
        if self.numRecords + 1 > self.maxsize:
            return True
        return False




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
            s = self.maxsize - ((self.tail - self.head) // self.RECORD_SIZE) + 1
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

# async def main():

#     f = FIFOFile(Path("perico.txt"), truncate=True, maxsize=10000, fsync_time=1)

#     operations = 0
#     global_iterations = 10
#     iterations = 1000
#     start_time = time.monotonic()

#     for j in range(global_iterations):
#         for i in range(iterations):
#             f.put("12345", "Hola que tal")
#             f.put("12345", "Hola que tal")
#             operations += 2

#     f.close()

#     elapsed_time = time.monotonic() - start_time
#     operations_second = (operations) / elapsed_time

#     print(f"{operations} performed in {elapsed_time} seconds")
#     print(f"Iterations/second: {operations_second}")


drop_table_script = """
DROP TABLE IF EXISTS testing;
"""

create_table_script = """
CREATE TABLE IF NOT EXISTS testing (
    timestamp INTEGER NOT NULL,
    ngsi_id_hash TEXT NOT NULL,
    ngsi_value_hash TEXT NOT NULL
);
"""

set_journal_wal = 'PRAGMA journal_mode=WAL'
query_journal_mode = """PRAGMA journal_mode"""

#########################################################################
#########################################################################
#########################################################################


import sqlite3

if os.path.exists('example.db'):
    os.remove('example.db')

db = sqlite3.connect('example.db',
    detect_types=sqlite3.PARSE_DECLTYPES,)
db.row_factory = sqlite3.Row

db.executescript(drop_table_script)
db.executescript(create_table_script)

db.execute(set_journal_wal)

mode = db.execute(query_journal_mode).fetchone()
print(f'Journal mode: {mode[0]}')

print(f'Isolation: {db.isolation_level}')

async def main():
    outer_loop = 10
    inner_loop = 1000
    operations = outer_loop * inner_loop

    start_time = time.monotonic()

    for i in range(outer_loop):
            for j in range(inner_loop):
                db.execute('insert into testing values (?, ?, ?)', (time.time_ns(),b'pepe', 'juan'))
            db.commit()
    db.commit()
    db.close()


    elapsed_time = time.monotonic() - start_time
    operations_second = (operations) / elapsed_time

    print(f"{operations} performed in {elapsed_time} seconds")
    print(f"Iterations/second: {operations_second}")

#########################################################################
#########################################################################
#########################################################################

# import aiosqlite

# if os.path.exists('example.db'):
#     os.remove('example.db')


# async def main():

#     db = await aiosqlite.connect('example.db',
#         detect_types=sqlite3.PARSE_DECLTYPES,)
#     db.row_factory = sqlite3.Row

#     await db.executescript(drop_table_script)
#     await db.executescript(create_table_script)

#     await db.execute(set_journal_wal)

#     mode = await db.execute(query_journal_mode)
#     mode = await mode.fetchone()
#     print(f'Journal mode: {mode[0]}')

#     print(f'Isolation: {db.isolation_level}')



#     outer_loop = 10
#     inner_loop = 1000
#     operations = outer_loop * inner_loop

#     start_time = time.monotonic()

#     for i in range(outer_loop):
#             for j in range(inner_loop):
#                 await db.execute('insert into testing values (?, ?, ?)', (time.time_ns(),b'pepe', 'juan'))
#             await db.commit()
#     await db.commit()
#     await db.close()


#     elapsed_time = time.monotonic() - start_time
#     operations_second = (operations) / elapsed_time

#     print(f"{operations} performed in {elapsed_time} seconds")
#     print(f"Iterations/second: {operations_second}")





if __name__ == '__main__':
    asyncio.run(main())

