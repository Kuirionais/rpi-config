#!/bin/sh

PORT=$(cat /tmp/gluetun/forwarded_port)

echo "Updating Transmission peer port to $PORT"

if [ -z "$PORT" ]; then
    echo "No forwarded port found"
    exit 1
fi

AUTH=$(echo -n "$RPCUSER:$RPCPWD" | base64)

SESSION_ID=$(wget -S -O /dev/null \
  --header="Authorization: Basic $AUTH" \
  http://localhost:9091/transmission/rpc 2>&1 \
  | awk '/X-Transmission-Session-Id/ {print $2}')

if [ -z "$SESSION_ID" ]; then
    echo "Could not get Transmission session ID"
    exit 1
fi

wget -qO- \
  --header="Authorization: Basic $AUTH" \
  --header="X-Transmission-Session-Id: $SESSION_ID" \
  --header="Content-Type: application/json" \
  --post-data="{\"method\":\"session-set\",\"arguments\":{\"peer-port\":$PORT}}" \
  http://localhost:9091/transmission/rpc

echo "Transmission peer port updated to $PORT"