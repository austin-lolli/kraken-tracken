#!/bin/bash
TZ="America/Los_Angeles" nohup python3 -u trade_tracker_eth.py > bot.log 2> >(ts '[%Y-%m-%d %H:%M:%S]' >> error.log) &
