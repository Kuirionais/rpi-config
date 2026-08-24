#!/bin/bash

echo "==== Checking running Docker containers ===="
running=$(sudo docker ps -q)

if [ -z "$running" ]; then
    echo "No running containers detected."
else
    echo "Running containers:"
    sudo docker ps --format "table {{.Names}}\t{{.Status}}"
    echo
    echo "Stopping all running containers..."
    sudo docker stop $running
    echo "All stop commands sent."
fi

# Give Docker a few seconds to settle
sleep 5

# Re-check running containers
leftover=$(sudo docker ps -q)
if [ -z "$leftover" ]; then
    echo "All containers stopped successfully."
    echo "Shutting down the Raspberry Pi..."
    sudo shutdown now
else
    echo "Warning: Some containers are still running!"
    sudo docker ps --format "table {{.Names}}\t{{.Status}}"
    echo "Aborting shutdown. Please check the containers above."
fi