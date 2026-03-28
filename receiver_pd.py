# receiver_pandas.py
import json

import zmq
import numpy as np
import pandas as pd
import time

def main():
    ctx = zmq.Context()
    socket = ctx.socket(zmq.PULL)
    socket.bind("ipc://@simple-stream")

    df = pd.DataFrame(columns=["ts", "value"])

    MESSAGE_THRESHOLD = 100
    count = 0
    total_count = 0

    start_t = time.perf_counter()
    
    while True:
        data, r, c = socket.recv_multipart()
        r, c = int(r.decode()), int(c.decode())
        count += 1

        arr = np.frombuffer(memoryview(data), dtype=np.float64).reshape(r, c, order="F")

        # column views
        ts_col = arr[:, 0]
        val_col = arr[:, 1]

        # ---- pandas ----
        batch_df = pd.DataFrame({
            "ts": ts_col,
            "value": val_col
        })

        df = pd.concat([df, batch_df], ignore_index=True)

        if count >= MESSAGE_THRESHOLD:
            result = (
                count,
                df["value"].mean(),
                df["value"].min(),
                df["value"].max()
            )

            bench_message = {"time_s": time.perf_counter() - start_t, "total_count": total_count}
            print(json.dumps(bench_message))

            total_count += count
            count = 0

            if total_count >= 1000:
                break
            

if __name__ == "__main__":
    main()