import sqlite3
con = sqlite3.connect(":memory:")
levels = con.execute("""
    select * from pragma_compile_options
""").fetchall()

print(levels)