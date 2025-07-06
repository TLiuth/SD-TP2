# precisa falar com seu sync (um subscriber/publisher) que quer se conectar

# O sync recebe seu pedido de acesso, juntamente ao id do client, e o envia ao broker juntamente ao timestamp e ao seu próprio id. 
# Tods os subscribers/publishers recebem a requisição de acesso e enfileiram o pedido.
# Se o recurso estiver livre, o cliente com o id do início da fila é liberado para processar.
# quando seu processamento concluir, ele notifica o sync, que então atualiza o broker. Todos os syncs são notificados, e a fila atualiza

# se um novo pedido chega ao broker, todos os syncs são notificados ao mesmo tempo


import socket
import json
from typing import Dict, Any

class Client:
    def __init__(self):
        self.socket = None
        
    def connect(self, host: str, port: int) -> bool:
        """Connect to a subscriber server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            return True
        except Exception as e:
            print(f"Failed to connect to {host}:{port} - {e}")
            return False
            
    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON request and return the response"""
        if not self.socket:
            raise ConnectionError("Not connected to server")
            
        try:
            # Send JSON request
            json_data = json.dumps(request)
            self.socket.send(json_data.encode('utf-8'))
            
            # Receive response
            response_data = self.socket.recv(1024)
            response = json.loads(response_data.decode('utf-8'))
            
            return response
            
        except Exception as e:
            print(f"Error sending request: {e}")
            return {"error": str(e)}
            
    def disconnect(self):
        """Close the connection"""
        if self.socket:
            self.socket.close()
            self.socket = None

# Example usage
if __name__ == "__main__":
    client = Client()
    
    # Connect to subscriber
    if client.connect('localhost', 8080):  # Replace with actual subscriber port
        # Send a request
        request = {
            "action": "subscribe",
            "topic": "events",
            "data": {"user_id": 123}
        }
        
        response = client.send_request(request)
        print(f"Response: {response}")
        
        client.disconnect()