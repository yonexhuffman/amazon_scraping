#!/bin/sh

cd "$(dirname "$0")"
cd ../ucbc/

pkill -f "UCBC2"
if [ -f "ucbc.pid" ]; then kill -9 `cat ucbc.pid`; fi


nohup sh -c "scrapy crawl UCBC && scrapy crawl UCBC2" > /dev/null 2>&1 & echo $! > ucbc.pid

echo "running ucbc"

now=$(date +"%Y%m%d")
readonly LOGFILE="UCBC_$now.log"
echo "log file name is $LOGFILE"
tail -f "./$LOGFILE"
