import socket
import time
import json
import os
import random
import datetime
import sys

# --- Configuration for the Client ---
# - Host Configuration -
SERVER_HOST = os.environ.get('SERVER_HOST', 'localhost')
SERVER_PORT = int(os.environ.get('SERVER_PORT', 5000))

# - Monitor Configuration
MONITOR_HOST = os.environ.get('MONITOR_HOST', 'localhost')
MONITOR_PORT = 6000
# Client Identification
client_id = os.getenv("CLIENT_ID", "0")

def log_event(event_type, client_id, message=""):
    """Log events to log.txt file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_entry = f"[{timestamp}] Client {client_id}: {event_type}"
    if message:
        log_entry += f" - {message}"
    log_entry += "\n"
    
    try:
        with open("log.txt", "a", encoding="utf-8") as log_file:
            log_file.write(log_entry)
    except Exception as e:
        print(f"Error writing to log: {e}")

def send_monitor_update(status):
    """Send status update to monitor app"""
    try:
        monitor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        monitor_socket.settimeout(5)  # 5 second timeout
        monitor_socket.connect((MONITOR_HOST, MONITOR_PORT))
        
        message = json.dumps({
            "client_id": client_id,
            "status": status,
            "timestamp": time.time()
        })
        
        monitor_socket.sendall(message.encode('utf-8'))
        monitor_socket.close()
        print(f"✅ Monitor update sent: {status}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send monitor update: {e}")
        return False

# Defines the Client object and it's functions
class PersistentClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
    
    def connect(self):
        """Establish connection to the sync server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"Client: Connected to server at {self.host}:{self.port}")
            return True
        except ConnectionRefusedError:
            print(f"Client: Connection refused. Is the server running on {self.host}:{self.port}?")
            return False
        except Exception as e:
            print(f"Client: Connection error: {e}")
            return False
    
    def send_message_and_wait_response(self, message, timeout=30):
        """Send message and wait for response from sync."""
        if not self.connected:
            print("Client: Not connected to server.")
            return None
            
        try:
            self.socket.sendall(message.encode('utf-8'))
            print(f"Client: Sent message: '{message}'")
            
            self.socket.settimeout(timeout)
            response_data = self.socket.recv(1024)
            if response_data:
                response = response_data.decode('utf-8')
                print(f"Client: Received response: '{response}'")
                return response
            else:
                print("Client: No response received.")
                return None
                
        except socket.timeout:
            print(f"Client: Timeout waiting for response ({timeout}s)")
            return None
        except Exception as e:
            print(f"Client: Error during communication: {e}")
            return None
    
    def disconnect(self):
        """Close the connection."""
        if self.socket and self.connected:
            self.socket.close()
            self.connected = False
            print("Client: Connection closed.")

if __name__ == "__main__":
    print(f"--- Starting Client Application (PID: {client_id}) ---")
    
    # Test monitor connection first
    print("🔍 Testing monitor connection...")
    if send_monitor_update("TEST_CONNECTION"):
        print("✅ Monitor connection successful!")
    else:
        print("❌ Monitor connection failed - continuing anyway...")
    
    client = PersistentClient(SERVER_HOST, SERVER_PORT)
    
    if not client.connect():
        print("Client: Failed to connect. Exiting.")
        exit(1)
    
    try:
        for request_number in range(1, 50):  # The client accesses the resource 50 times
            print(f"\n=== Request {request_number}/50 ===")
            
            json_message = {"command": "REQUEST_ACCESS", "client_id": f"{client_id}"}
            log_event("ACCESS_REQUEST", client_id, f"Request #{request_number}")
            
            response = client.send_message_and_wait_response(json.dumps(json_message))

            # proccess the response for the access request
            if response:
                try:
                    response_data = json.loads(response)
                    if response_data.get("status") == "GRANTED":
                        log_event("ACCESS_GRANTED", client_id, f"Request #{request_number}")
                        
                        print(f"🎉 Client {client_id}: Access granted for request {request_number}!")
                        
                        # Notify monitor: entering critical section
                        send_monitor_update("ENTERING_CRITICAL")
                        
                        work_time = random.uniform(0.2, 2)  # Longer time for visibility
                        print(f"⚡ Working in critical section for {work_time:.1f}s...")
                        time.sleep(work_time)
                        
                        print(f"✅ Client {client_id}: Work completed!")
                        
                        # Notify monitor: leaving critical section
                        send_monitor_update("LEAVING_CRITICAL")
                        
                        json_message = {"command": "DONE", "client_id": f"{client_id}"}
                        done_response = client.send_message_and_wait_response(json.dumps(json_message))
                        
                        log_event("DONE", client_id, f"Request #{request_number} - Work completed in {work_time:.2f}s")
                        
                        time.sleep(random.uniform(1, 3))  # Pause between requests
                        
                    elif response_data.get("status") == "WAIT":
                        log_event("ACCESS_DENIED", client_id, f"Request #{request_number}")
                        print(f"⏳ Client {client_id}: Access denied, need to wait.")
                        break
                    else:
                        log_event("UNEXPECTED_RESPONSE", client_id, f"Request #{request_number} - Response: {response}")
                        print(f"❓ Unexpected response: {response}")
                        break
                        
                except json.JSONDecodeError:
                    log_event("ERROR", client_id, f"Request #{request_number} - Invalid JSON response: {response}")
                    print(f"❌ Invalid JSON response: {response}")
                    break
            else:
                log_event("ERROR", client_id, f"Request #{request_number} - No response received")
                print(f"❌ No response received")
                break
        
        print(f"\n🏁 Client {client_id}: Completed all requests.")
        log_event("COMPLETED", client_id, "Finished all requests")
            
    except KeyboardInterrupt:
        log_event("INTERRUPTED", client_id, "Client interrupted by user")
        print(f"\n⏹️ Client {client_id}: Interrupted by user.")
    finally:
        # Notify monitor that client is done
        send_monitor_update("CLIENT_FINISHED")
        client.disconnect()
        print(f"--- Client {client_id} application finished. ---")
