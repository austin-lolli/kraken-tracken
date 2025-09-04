#!/bin/bash
TZ="America/Los_Angeles" nohup python3 -u runner_rsi_simple.py > bot.log 2> >(ts '[%Y-%m-%d %H:%M:%S]' >> error.log) &
