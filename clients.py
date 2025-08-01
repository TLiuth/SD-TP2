# # precisa falar com seu sync (um subscriber/publisher) que quer se conectar
# # O sync recebe seu pedido de acesso, juntamente ao id do client, e o envia ao broker juntamente ao timestamp e ao seu próprio id. 
# # Tods os subscribers/publishers recebem a requisição de acesso e enfileiram o pedido.
# # Se o recurso estiver livre, o cliente com o id do início da fila é liberado para processar.
# # quando seu processamento concluir, ele notifica o sync, que então atualiza o broker. Todos os syncs são notificados, e a fila atualiza

# # se um novo pedido chega ao broker, todos os syncs são notificados ao mesmo tempo


# O exemplo abaixo não mantém a conexão com o sync. Manter a conexão é importante, para aguardar a resposta



import socket
import time
import json
import os
import random
import datetime

# --- Configuration for the Client ---
SERVER_HOST = "localhost"
SERVER_PORT = 5000
CLIENT_ID = os.getpid()  # Fixed: Added parentheses

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
            # Send the message
            self.socket.sendall(message.encode('utf-8'))
            print(f"Client: Sent message: '{message}'")
            
            # Set timeout for receiving response
            self.socket.settimeout(timeout)
            
            # Wait for response
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
    print(f"--- Starting Client Application (PID: {CLIENT_ID}) ---")
    
    # Create persistent client
    client = PersistentClient(SERVER_HOST, SERVER_PORT)
    
    # Connect to sync server
    if not client.connect():
        print("Client: Failed to connect. Exiting.")
        exit(1)
    
    try:
        # Request access up to 50 times
        for request_number in range(1, 51):
            print(f"\n=== Request {request_number}/50 ===")
            
            # Request access and wait for permission
            json_message = {"command": "REQUEST_ACCESS", "client_id": f"{CLIENT_ID}"}
            
            # Log the access request
            log_event("ACCESS_REQUEST", CLIENT_ID, f"Request #{request_number}")
            
            response = client.send_message_and_wait_response(json.dumps(json_message))
            
            if response:
                try:
                    response_data = json.loads(response)
                    if response_data.get("status") == "GRANTED":
                        # Log the access granted
                        log_event("ACCESS_GRANTED", CLIENT_ID, f"Request #{request_number}")
                        
                        print(f"Client {CLIENT_ID}: Access granted for request {request_number}! Starting critical section...")
                        
                        # Simulate some work in critical section
                        work_time = random.uniform(1, 3)
                        time.sleep(work_time)
                        print(f"Client {CLIENT_ID}: Work completed in critical section (took {work_time:.2f}s).")
                        
                        # Notify completion
                        json_message = {"command": "DONE", "client_id": f"{CLIENT_ID}"}
                        done_response = client.send_message_and_wait_response(json.dumps(json_message))
                        
                        # Log the completion
                        log_event("DONE", CLIENT_ID, f"Request #{request_number} - Work completed in {work_time:.2f}s")
                        
                        print(f"Client {CLIENT_ID}: Notified completion to sync for request {request_number}.")
                        
                        # Short pause between requests
                        time.sleep(random.uniform(0.5, 1.5))
                        
                    elif response_data.get("status") == "WAIT":
                        log_event("ACCESS_DENIED", CLIENT_ID, f"Request #{request_number} - Need to wait in queue")
                        print(f"Client {CLIENT_ID}: Access denied for request {request_number}. Need to wait in queue.")
                        break  # Exit if we need to wait
                    else:
                        log_event("UNEXPECTED_RESPONSE", CLIENT_ID, f"Request #{request_number} - Response: {response}")
                        print(f"Client {CLIENT_ID}: Unexpected response for request {request_number}: {response}")
                        
                except json.JSONDecodeError:
                    log_event("ERROR", CLIENT_ID, f"Request #{request_number} - Invalid JSON response: {response}")
                    print(f"Client {CLIENT_ID}: Invalid JSON response for request {request_number}: {response}")
            else:
                log_event("ERROR", CLIENT_ID, f"Request #{request_number} - No response received")
                print(f"Client {CLIENT_ID}: No response received for request {request_number}.")
                break  # Exit if no response
        
        print(f"\nClient {CLIENT_ID}: Completed all access requests.")
        log_event("COMPLETED", CLIENT_ID, "Finished all 50 access requests")
            
    except KeyboardInterrupt:
        log_event("INTERRUPTED", CLIENT_ID, "Client interrupted by user")
        print(f"\nClient {CLIENT_ID}: Interrupted by user.")
    finally:
        # Always disconnect
        client.disconnect()
        print(f"--- Client {CLIENT_ID} application finished. ---")
