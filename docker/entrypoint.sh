#!/bin/bash
echo "---$0---"
num_middleware=$1
num_queries=${2:-50000}
threads=20
repetitions=$(( num_queries / threads ))

echo -----------------------------------------
echo "number of middlewares : ${num_middleware:?}"
python --version
pip list | grep -i fastapi
pip list | grep -i starlette
pip list | grep -i uvicorn
echo -----------------------------------------

nohup python server.py $num_middleware &
sleep 1
siege -r $repetitions -c $threads http://127.0.0.1:14000/_ping
curl http://127.0.0.1:14000/garbage_collect
sleep 5
echo -----------------------------------------
echo "number of middlewares : $num_middleware"
python --version
pip list | grep -i fastapi
pip list | grep -i starlette
pip list | grep -i uvicorn
echo -----------------------------------------
ps aux