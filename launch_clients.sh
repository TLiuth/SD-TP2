#!/bin/bash
    
    python3 clients_with_monitor.py 5000 &
    sleep 0.5
    python3 clients_with_monitor.py 5001 &
    sleep 0.5
    python3 clients_with_monitor.py 5002 &
    sleep 0.5
    python3 clients_with_monitor.py 5003 &
    sleep 0.5
    python3 clients_with_monitor.py 5004 &
    
    
