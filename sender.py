# sender.py
import zmq
import numpy as np
import time
import argparse


def main(mps: int, rows: int):
    ctx = zmq.Context()
    socket = ctx.socket(zmq.PUSH)
    socket.connect("ipc://@simple-stream")

    interval = 1.0 / mps

    while True:
        # create batch (rows x 2 columns)
        ts = np.full((rows, 1), time.time(), dtype=np.float64)
        val = np.random.rand(rows, 1)

        batch = np.hstack([ts, val])  # shape (rows, 2)
        # print("sending batch:", batch)

        # send as raw bytes (same idea as your original)
        socket.send_multipart(
            [
                batch.astype(np.float64, order="F").tobytes(),
                str(rows).encode(),
                b"2",  # number of columns
            ]
        )

        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mps", type=int, default=10)
    parser.add_argument("--rows", type=int, default=1000)
    args = parser.parse_args()

    main(args.mps, args.rows)
