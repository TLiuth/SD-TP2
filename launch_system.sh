#!/bin/bash
    python3 syncs/application/main/mqtt_connection/application_gateway.py 5000 &
    python3 syncs/application/main/mqtt_connection/application_gateway.py 5001 &
    python3 syncs/application/main/mqtt_connection/application_gateway.py 5002 &
    python3 syncs/application/main/mqtt_connection/application_gateway.py 5003 &
    python3 syncs/application/main/mqtt_connection/application_gateway.py 5004 &
    
    sleep 1

    python3 mobile_monitor/app.py
    
    sleep 2
    
    python3 clients_with_monitor.py 5000 &
    python3 clients_with_monitor.py 5001 &
    python3 clients_with_monitor.py 5002 &
    python3 clients_with_monitor.py 5003 &
    python3 clients_with_monitor.py 5004 &
    
    
