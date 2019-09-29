#!/bin/sh

cd "$(dirname "$0")"
cd ../abe/

if [ -f "abe.pid" ]; then kill -9 `cat abe.pid`; fi

nohup scrapy crawl ABE  > /dev/null 2>&1 & echo $! > abe.pid

echo "running abe"

now=$(date +"%Y%m%d")
readonly LOGFILE="ABE_$now.log"
echo "log file name is $LOGFILE"
tail -f "./$LOGFILE"
