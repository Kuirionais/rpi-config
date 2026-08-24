#!/bin/bash

# File: monitor_temp.sh
# Logs CPU temp every 10 seconds

LOGFILE="/srv/scripts/pi_temp.log"
THRESHOLD=75  # max safe temp in Celsius

while true; do
    TEMP=$(vcgencmd measure_temp | egrep -o '[0-9]+\.[0-9]+')
    DATE=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$DATE - Temp: $TEMP°C" | tee -a $LOGFILE

    # Optional warning
    TEMP_INT=${TEMP%.*}  # integer part
    if [ "$TEMP_INT" -ge "$THRESHOLD" ]; then
        echo "$DATE - WARNING: CPU temp exceeded $THRESHOLD°C!" | tee -a $LOGFILE
    fi

    sleep 10
done