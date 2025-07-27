#!/bin/bash

echo "🧹 Cleaning up system for fresh start..."

# Kill all processes on relevant ports
sudo kill -9 $(sudo lsof -t -i:5000,5001,6000,1883) 2>/dev/null || echo "No processes to kill"

# Clear MQTT broker retained messages (if using mosquitto)
if command -v mosquitto_pub &> /dev/null; then
    echo "🧽 Clearing MQTT retained messages..."
    mosquitto_pub -h localhost -t "BCC362" -r -n
fi

# Wait a moment
sleep 2

echo "✅ System ready for fresh start!"
echo "Start in this order:"
echo "1. mosquitto -v"
echo "2. python3 application_gateway.py 5000"
echo "3. python3 mobile_monitor/app.py"
echo "4. python3 clients.py"
