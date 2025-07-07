import socket
import json
import threading
import time
from queue import Queue
from syncs.application.main.mqtt_connection.mqtt_client_connection import MqttClientConnection

class SocketMqttBridge:
    def __init__(self, host='localhost', port=8080, mqtt_broker_ip='localhost', mqtt_port=1883, mqtt_client_name='socket_bridge'):
        self.host = host
        self.port = port
        self.mqtt_broker_ip = mqtt_broker_ip
        self.mqtt_port = mqtt_port
        self.mqtt_client_name = mqtt_client_name
        self.server_socket = None
        self.mqtt_client = None
        self.response_queue = Queue()
        self.running = False
        
    def start_server(self):
        """Start the socket server and MQTT connection"""
        self.running = True
        
        # Initialize MQTT client
        self.mqtt_client = MqttClientConnection(
            broker_ip=self.mqtt_broker_ip,
            port=self.mqtt_port,
            client_name=self.mqtt_client_name
        )
        
        # Start MQTT connection
        self.mqtt_client.start_connection()
        time.sleep(1)  # Allow time for connection
        
        # Subscribe to response topic
        self.mqtt_client._MqttClientConnection__mqtt_client.subscribe("response/topic")
        self.mqtt_client._MqttClientConnection__mqtt_client.on_message = self._on_mqtt_message
        
        # Start socket server
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        
        print(f"Socket server started on {self.host}:{self.port}")
        print(f"MQTT bridge connected to {self.mqtt_broker_ip}:{self.mqtt_port}")
        
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"Connection from {address}")
                
                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    print(f"Error accepting connection: {e}")
                    
    def _handle_client(self, client_socket, address):
        """Handle individual client connection"""
        try:
            # Receive JSON data from client
            data = client_socket.recv(1024).decode('utf-8')
            
            if not data:
                return
                
            print(f"Received data from {address}: {data}")
            
            # Parse JSON
            try:
                json_data = json.loads(data)
            except json.JSONDecodeError as e:
                error_response = {"error": "Invalid JSON format", "details": str(e)}
                client_socket.send(json.dumps(error_response).encode('utf-8'))
                return
                
            # Add additional information to JSON
            enhanced_data = {
                "original_data": json_data,
                "timestamp": time.time(),
                "client_address": f"{address[0]}:{address[1]}",
                "request_id": f"req_{int(time.time() * 1000)}"
            }
            
            # Publish to MQTT broker
            mqtt_message = json.dumps(enhanced_data)
            self.mqtt_client._MqttClientConnection__mqtt_client.publish("request/topic", mqtt_message)
            print(f"Published to MQTT: {mqtt_message}")
            
            # Wait for response from MQTT subscriber
            response = self._wait_for_response(enhanced_data["request_id"])
            
            # Send response back to client
            client_socket.send(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error handling client {address}: {e}")
            error_response = {"error": "Server error", "details": str(e)}
            try:
                client_socket.send(json.dumps(error_response).encode('utf-8'))
            except:
                pass
        finally:
            client_socket.close()
            
    def _on_mqtt_message(self, client, userdata, message):
        """Handle MQTT messages from subscriber"""
        try:
            payload = message.payload.decode('utf-8')
            topic = message.topic
            
            print(f"Received MQTT message on topic {topic}: {payload}")
            
            # Put response in queue for waiting clients
            self.response_queue.put({
                "topic": topic,
                "payload": payload,
                "timestamp": time.time()
            })
            
        except Exception as e:
            print(f"Error processing MQTT message: {e}")
            
    def _wait_for_response(self, request_id, timeout=30):
        """Wait for response from MQTT subscriber"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if not self.response_queue.empty():
                    response = self.response_queue.get(timeout=1)
                    
                    # Try to parse response and match request_id
                    try:
                        response_data = json.loads(response["payload"])
                        if response_data.get("request_id") == request_id:
                            return response["payload"]
                    except json.JSONDecodeError:
                        # If not JSON, return raw payload
                        return response["payload"]
                        
            except:
                pass
                
            time.sleep(0.1)
            
        # Timeout response
        timeout_response = {
            "error": "Response timeout",
            "request_id": request_id,
            "timeout": timeout
        }
        return json.dumps(timeout_response)
        
    def stop_server(self):
        """Stop the socket server and MQTT connection"""
        self.running = False
        
        if self.server_socket:
            self.server_socket.close()
            
        if self.mqtt_client:
            self.mqtt_client.end_connection()
            
        print("Socket MQTT bridge stopped")

if __name__ == "__main__":
    # Example usage
    bridge = SocketMqttBridge(
        host='localhost',
        port=8080,
        mqtt_broker_ip='localhost',
        mqtt_port=1883,
        mqtt_client_name='socket_bridge_client'
    )
    
    try:
        bridge.start_server()
    except KeyboardInterrupt:
        print("\nShutting down...")
        bridge.stop_server()