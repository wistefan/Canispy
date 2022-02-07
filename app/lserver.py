# Imports from standard library
import os
from typing import Optional, Union
import asyncio
import time
import sqlite3
import hashlib

# Import these utilities
from utils.merkletree import MerkleTree, MerkleError

# Import the HTTP app server
from fastapi import FastAPI, BackgroundTasks

##################################

from sqlmodel import Field, SQLModel, create_engine

class MerkleTable(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: int
    ngsi_id_hash: str
    ngsi_value_hash: str
    ngsi_receipt: Optional[str] = None


# The table scripts

drop_table_script = """
DROP TABLE IF EXISTS testing;
"""

create_table_script = """
CREATE TABLE IF NOT EXISTS testing (
    id INTEGER PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    ngsi_id_hash TEXT NOT NULL,
    ngsi_value_hash TEXT NOT NULL,
    ngsi_receipt TEXT
);
"""

set_journal_wal = 'PRAGMA journal_mode=WAL'
query_journal_mode = """PRAGMA journal_mode"""


class MerkleBuffer:
    def __init__(self, 
        db_name: str = 'mkbuffer.db',   # Name of the database
        db_max_elements: int = 10000,   # Maximum size of database, in number of records
        maxLeaves: int = 1024,          # Maximum number of leaves of the Merkle Tree to notarize
        maxInterval: int = 60,          # Notarize every maxInterval (seconds) even if not enough leaves received yet
        durability: int = 10            # Commit database every durability seconds, to make data permanent
    ) -> None:
        self.db_name = db_name
        self.maxLeaves = maxLeaves
        self.db_max_elements = db_max_elements
        self.maxInterval = maxInterval
        self.durability = durability
        self.next_record = 1
        self.leaves = 0
        self.last_notarization = time.time()

        print(f'MaxLeaves: {maxLeaves}')

        self.open()

        # Create a background task which commits the db every durability secs (or 2 sec as a minimum),
        # and registers the Merkle Tree even if not enough entries have been received
        if durability > 0 or maxInterval > 0:
            self.commit_task = asyncio.create_task(self.commit_background_task(min(durability, maxInterval)))

    def db_name(self):
        self.db_name

    def open(self):

        sqlite_file_name = "sqlmodel.db"
        sqlite_url = f"sqlite:///{sqlite_file_name}"

        engine = create_engine(sqlite_url, echo=True)


        # # Connect to db
        # self.db = sqlite3.connect(self.db_name,
        #     detect_types=sqlite3.PARSE_DECLTYPES,)
        # self.db.row_factory = sqlite3.Row
        # self.db.close()
        # self.db = sqlite3.connect(self.db_name,
        #     detect_types=sqlite3.PARSE_DECLTYPES,)
        # self.db.row_factory = sqlite3.Row


    def open_erase(self):
        # Erase the database
        if os.path.exists(self.db_name):
            os.remove(self.db_name)

        # Connect to db
        self.db = sqlite3.connect(self.db_name,
            detect_types=sqlite3.PARSE_DECLTYPES,)
        self.db.row_factory = sqlite3.Row

        # Create the table, dropping it before.
        self.db.executescript(drop_table_script)
        self.db.executescript(create_table_script)

        # Set the db to WAL mode for better performance
        self.db.execute(set_journal_wal)

    def commit(self):
        self.db.commit()

    def close(self):
        self.next_record = 1
        self.leaves = 0
        self.commit_task.cancel()
        self.db.close()

    def _hash(self, text: Union[str, bytes]) -> bytes:
        if isinstance(text, str):
            text = bytes(text, "utf-8")
        h = hashlib.sha256()
        h.update(text)
        d = h.digest()
        return d

    def put(self, id: str, value: str):

        need_process_batch = False

        # calculate hashes
        id_hash = self._hash(id)
        value_hash = self._hash(value)

        # Insert the record
        try:

            # Execute the INSERT or REPLACE
            self.db.execute(
                '''insert or replace into testing
                (id, timestamp, ngsi_id_hash, ngsi_value_hash) values (?, ?, ?, ?)''',
                (self.next_record, time.time_ns(), id_hash, value_hash))

            # Increment the record number
            self.next_record += 1
            self.leaves += 1

        except Exception as e:
            raise e

        # Check if we should create the Merkle Tree and notarize
        if self.leaves >= self.maxLeaves:

            # Process the batch of records, possibly asynchronously
            need_process_batch = True
#            self.processBatch()
            self.leaves = 0

        # Check if the database size has reached the maximum and start reusing rows
        if self.next_record > self.db_max_elements:
            print("Rotate the database")
            self.next_record = 1

        return need_process_batch

    def processBatch(self, db):
        # stmt = 'select * from testing where ngsi_receipt is null limit 100'
        stmt = 'select * from testing'
        result = db.execute(stmt)
        rows = result.fetchall()
        print(f'Rows: {len(rows)}')
        # for row in rows:
        #     print(f'{row["timestamp"]}-{row["ngsi_id_hash"].hex()}-{row["ngsi_value_hash"].hex()}')

        # Update last notarization
        self.last_notarization = time.time()

    # Create a background task to make sure commit is called for the last put,
    # even if no more puts are coming
    async def commit_background_task(self, frequency: int):
        while True:
            await asyncio.sleep(frequency)
            print("BKG Task: committing")

            # Commit the database
            self.db.commit()

            # Check if must notarize even though not enough records have arrived
            now = time.time()
            if now - self.last_notarization > self.maxInterval:
                self.processBatch(self.db)
                self.last_notarization = now


f: MerkleBuffer = None

app = FastAPI()

def processBatch():
    global f
    print(f'In return from call process')
    # Connect to db
    db = sqlite3.connect(f.db_name,
        detect_types=sqlite3.PARSE_DECLTYPES,)
    db.row_factory = sqlite3.Row

    f.processBatch(db)

@app.on_event("startup")
async def startup_event():
    global f
    f = MerkleBuffer()

@app.on_event("shutdown")
def shutdown_event():
    print("SHUTDOWN: closing the database")
    global f
    f.close()

@app.get("/store/initialize")
async def store_initialize():
    global f
    f = MerkleBuffer(maxLeaves=4)
    return {"result": "OK"}


@app.get("/store/{item_id}/{value_id}")
async def store_item(item_id: str = "Hello", value_id: str = "Pepe", background_tasks: BackgroundTasks = None):
    global f
    result = f.put(item_id, item_id)
    if result:
        background_tasks.add_task(processBatch)

    return {"result": "OK"}


import uvicorn

if __name__ == "__main__":
    uvicorn.run("lserver:app", host="127.0.0.1", port=8000, log_level="warning")