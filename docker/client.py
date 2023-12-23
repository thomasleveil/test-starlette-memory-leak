import requests
import multiprocessing as mp

def do():
    while 1:
        rsp = requests.get("http://127.0.0.1:14000/_ping")
        print(rsp.status_code)

for _ in range(20):
    p = mp.Process(target=do, daemon=True)
    p.start()

import time
time.sleep(1000000)