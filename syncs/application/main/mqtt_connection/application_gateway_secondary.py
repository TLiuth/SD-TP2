import threading
import queue
import time
import json
import socket
import os
import datetime

# Assuming your mqtt_client_connection.py is in a directory named 'mqtt' or similar
# Adjust import path if necessary based on your project structure
# For example, if mqtt_client_connection.py is directly in the same folder:
from mqtt_client_connection import MqttClientConnection
import callbacks # Import the callbacks module for direct reference if needed
                 # Or just rely on it being set in MqttClientConnection


# --- Configuration ---
# MQTT Broker Details
MQTT_BROKER_HOST = "192.168.15.7"
MQTT_BROKER_PORT = 1883
MQTT_CLIENT_NAME = "MyApplicationGateway2"
MQTT_USER = "your_mqtt_user"
MQTT_PASSWORD = "your_mqtt_password"
MQTT_TOPIC = "BCC362" # Already handled by your callbacks.py

PROCESS_ID = os.getpid()


# Network Listener Details
NETWORK_LISTEN_HOST = "0.0.0.0" # Listen on all available interfaces
NETWORK_LISTEN_PORT = 5001      # Choose an unused port for your client app

# --- Shared Queues ---
incoming_network_messages_queue = queue.Queue()
incoming_mqtt_messages_queue = queue.Queue()
outgoing_mqtt_publish_queue = queue.Queue() # For messages to be published by the MQTT client

# --- Global MQTT Client Manager Instance ---
mqtt_connection_manager = None

# --- Thread Functions ---

def network_listener_thread_func():
    """Thread function for listening for incoming network connections."""
    print(f"Network Listener started on {NETWORK_LISTEN_HOST}:{NETWORK_LISTEN_PORT}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((NETWORK_LISTEN_HOST, NETWORK_LISTEN_PORT))
            s.listen(5) # Allow up to 5 queued connections

            while True:
                conn, addr = s.accept() # Blocks until a client connects
                # Handle each client connection in a new thread
                client_handler_thread = threading.Thread(target=handle_network_client_connection, args=(conn, addr))
                client_handler_thread.daemon = True # Allows main program to exit even if thread is running
                client_handler_thread.start()
    except Exception as e:
        print(f"Error in network listener thread: {e}")

def handle_network_client_connection(conn, addr):
    """Handles data exchange with a single connected network client."""
    print(f"Accepted network connection from {addr}")
    try:
        while True:
            data = conn.recv(1024) # Read up to 1024 bytes
            if not data:
                print(f"Client {addr} disconnected.")
                break
            message_content = data.decode('utf-8').strip()
            print(f"Raw Network Message from {addr}: '{message_content}'")

            message_data = {
                "source": "network",
                "client_address": addr[0],
                "client_port": addr[1],
                "payload": message_content
            }
            incoming_network_messages_queue.put(message_data)
            print(f"Network message queued for processing: {message_content}")

    except Exception as e:
        print(f"Error handling network client {addr}: {e}")
    finally:
        conn.close()

def mqtt_publisher_loop_func(mqtt_client_instance):
    """
    This function will be run in a thread to process outgoing MQTT publish requests.
    It takes the actual paho-mqtt client instance as an argument.
    """
    print("MQTT Publisher Loop Thread started.")
    while True:
        try:
            # Get messages from the outgoing publish queue
            message_to_publish = outgoing_mqtt_publish_queue.get(timeout=1) # Blocks for up to 1 second
            topic = message_to_publish["topic"]
            payload = message_to_publish["payload"]
            qos = message_to_publish.get("qos", 1) # Default QoS to 1

            # Check if client is connected and ready
            if mqtt_client_instance and hasattr(mqtt_client_instance, '_state') and mqtt_client_instance.is_connected():
                result, mid = mqtt_client_instance.publish(topic, payload, qos)
                if result == 0: # 0 means MQTT_ERR_SUCCESS
                    print(f"MQTT Published: Topic='{topic}', Payload='{payload}', QoS={qos}, MID={mid}")
                else:
                    print(f"MQTT Publish failed for topic {topic} with result {result}")
            else:
                print("MQTT client not connected, requeueing message...")
                # Put the message back in the queue to retry later
                outgoing_mqtt_publish_queue.put(message_to_publish)
                time.sleep(1)  # Wait before retrying

        except queue.Empty:
            pass # No messages to publish, just continue looping
        except Exception as e:
            print(f"Error in MQTT publisher loop: {e}")
        time.sleep(0.01) # Small delay to prevent busy-waiting

def application_logic_thread_func():
    """Main application logic thread."""
    print("Application Logic Thread started.")
    while True:
        try:
            # --- Process Incoming Network Messages ---
            if not incoming_network_messages_queue.empty():
                message = incoming_network_messages_queue.get()
                print(f"Processing Network Message: {message['payload']}")

                try:
                    # Parse JSON payload
                    json_data = json.loads(message['payload'])
                    print(f"Parsed JSON data: {json_data}")
                    
                    # Access specific variables from the JSON
                    command = json_data.get('command', '')
                    client_id = json_data.get('client_id', '')

                    # Depending on message content, react with a publish
                    if command == "REQUEST_ACCESS":
                        access_payload = json.dumps({"command": command, "client_id": client_id, "sync_id": PROCESS_ID, "timestamp": f"{time.time()}"})
                        outgoing_mqtt_publish_queue.put({"topic": MQTT_TOPIC, "payload": access_payload})
                        print("Logic: Queued REQUEST_ACCESS RESPONSE publish to MQTT.")
                    elif command == "DONE":
                        done_payload = json.dumps({"command": command, "client_id": client_id, "sync_id": PROCESS_ID, "timestamp": f"{time.time()}"})
                        outgoing_mqtt_publish_queue.put({"topic": MQTT_TOPIC, "payload": done_payload})
                        print("Logic: Queued DONE RESPONSE publish to MQTT.")
                    else:
                        response_payload = json.dumps({"source": "network_client_echo", "original_message": message['payload']})
                        outgoing_mqtt_publish_queue.put({"topic": MQTT_TOPIC, "payload": response_payload})
                        print("Logic: Queued general response publish to MQTT.")
                        
                except json.JSONDecodeError:
                    # Handle non-JSON messages
                    print("Message is not valid JSON, processing as plain text...")
                    response_payload = json.dumps({
                        "source": "network_client_text", 
                        "original_message": message['payload'],
                        "timestamp": time.time(),
                        "process_id": PROCESS_ID
                    })
                    outgoing_mqtt_publish_queue.put({"topic": MQTT_TOPIC, "payload": response_payload})
                    print("Logic: Queued TEXT response publish to MQTT.")

            # --- Process Incoming MQTT Messages ---
            if not incoming_mqtt_messages_queue.empty():
                message = incoming_mqtt_messages_queue.get()
                print(f"Processing MQTT Message: Topic='{message['topic']}'")

                # React to messages from subscribed topics
                if message['topic'] == "BCC362":
                    payload_str = str(message['payload'])
                    
                    # Try to parse as JSON first
                    try:
                        payload_data = json.loads(message['payload'])
                        command = payload_data.get('command', '')
                        client_id = payload_data.get('client_id', '')
                        sync_id = payload_data.get('sync_id', '')
                        
                        # IMPORTANT: Ignore messages from this same process
                        if sync_id == PROCESS_ID:
                            print(f">> Ignoring message from self (sync_id: {sync_id})")
                            continue
                        
                        if command == "DONE":
                            print(f">> Logic: 'DONE' message received from client {client_id} via sync {sync_id}. Update resource queue and freeing next client.")
                            print("Updating all queues")
                                
                        elif command == "REQUEST_ACCESS":
                            print(f">> Logic: 'REQUEST_ACCESS' message received from client {client_id} via sync {sync_id}. Updating resource queue.")
                            # Don't republish - just update internal state
                            print("Adding client to access queue")
                            
                        else:
                            print(f">> Logic: MQTT JSON message with unknown command: {command}")
                            
                    except json.JSONDecodeError:
                        # Handle plain string payloads
                        print(f">> Logic: MQTT plain text message: {payload_str}")
                        
                        if payload_str == "initiated":
                            print(">> Logic: Process initiated confirmation received.")
                        elif payload_str == "DONE":
                            print(">> Logic: Simple 'DONE' message received.")
                        else:
                            print(f">> Logic: MQTT message on BCC362 with unknown payload: {payload_str}")

            time.sleep(0.1) # Small delay to prevent busy-waiting
        except Exception as e:
            print(f"Error in application logic loop: {e}")
            time.sleep(1) # Wait a bit before retrying

# --- Main Application Entry Point ---
if __name__ == "__main__":
    print("Starting Main Application Gateway...")

    # 1. Initialize MQTT Client Manager
    mqtt_connection_manager = MqttClientConnection(
        broker_ip=MQTT_BROKER_HOST,
        port=MQTT_BROKER_PORT,
        client_name=MQTT_CLIENT_NAME,
        username=MQTT_USER,
        password=MQTT_PASSWORD
    )

    # Pass the incoming_mqtt_messages_queue to the MqttClientConnection
    # so that the on_message callback can use it.
    mqtt_connection_manager.set_callback_userdata("incoming_mqtt_messages_queue", incoming_mqtt_messages_queue)

    # 2. Start MQTT Connection (this will start its internal loop_start() thread)
    mqtt_connection_manager.start_connection()

    # Get the actual paho-mqtt client instance for the publisher thread
    actual_mqtt_paho_client = mqtt_connection_manager.get_mqtt_client_instance()

    # 3. Start MQTT Publisher Loop Thread (to handle outgoing messages)
    if actual_mqtt_paho_client:
        mqtt_publisher_thread = threading.Thread(target=mqtt_publisher_loop_func, args=(actual_mqtt_paho_client,))
        mqtt_publisher_thread.daemon = True
        mqtt_publisher_thread.start()
    else:
        print("Could not start MQTT publisher thread: MQTT client not initialized.")
        exit(1) # Exit if MQTT connection failed at startup

    # 4. Start Network Listener Thread
    network_listener_thread = threading.Thread(target=network_listener_thread_func)
    network_listener_thread.daemon = True
    network_listener_thread.start()

    # 5. Start Application Logic Thread
    application_logic_thread = threading.Thread(target=application_logic_thread_func)
    application_logic_thread.daemon = True
    application_logic_thread.start()

    try:
        # Keep the main thread alive indefinitely to allow daemon threads to run
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Shutting down application...")
    finally:
        # Graceful shutdown for MQTT connection
        if mqtt_connection_manager:
            mqtt_connection_manager.end_connection()
        print("Application Gateway stopped.")
