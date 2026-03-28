# receiver.py
import zmq
import numpy as np
import duckdb
import pyarrow as pa
import time
import json

def main():
    ctx = zmq.Context()
    socket = ctx.socket(zmq.PULL)
    socket.bind("ipc://@simple-stream")

    conn = duckdb.connect()
    conn.execute("""
        CREATE TABLE data (
            ts DOUBLE,
            value DOUBLE
        )
    """)

    MESSAGE_THRESHOLD = 100

    count = 0
    total_count = 0

    start_t = time.perf_counter()
    
    while True:
        data, r, c = socket.recv_multipart()
        r, c = int(r.decode()), int(c.decode())
        count += 1

        # read as Fortran order
        arr = np.frombuffer(memoryview(data), dtype=np.float64).reshape(r, c, order="F")

        # ---- column views ----
        ts_col = arr[:, 0]
        val_col = arr[:, 1]

        table = pa.Table.from_arrays(
            [
                pa.array(ts_col),
                pa.array(val_col),
            ],
            names=["ts", "value"]
        )

        conn.register("incoming", table)

        conn.execute("""
            INSERT INTO data
            SELECT * FROM incoming
        """)

        if count >= MESSAGE_THRESHOLD:
            result = conn.execute("""
                    SELECT COUNT(*), AVG(value)
                    FROM data
                """).fetchall()
            
            bench_message = {"time_s": time.perf_counter() - start_t, "total_count": total_count}
            print(json.dumps(bench_message))

            total_count += count
            count = 0

            if total_count >= 1_000:
                break

if __name__ == "__main__":
    main()