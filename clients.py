# # precisa falar com seu sync (um subscriber/publisher) que quer se conectar
# # O sync recebe seu pedido de acesso, juntamente ao id do client, e o envia ao broker juntamente ao timestamp e ao seu próprio id. 
# # Tods os subscribers/publishers recebem a requisição de acesso e enfileiram o pedido.
# # Se o recurso estiver livre, o cliente com o id do início da fila é liberado para processar.
# # quando seu processamento concluir, ele notifica o sync, que então atualiza o broker. Todos os syncs são notificados, e a fila atualiza

# # se um novo pedido chega ao broker, todos os syncs são notificados ao mesmo tempo


# O exemplo abaixo não mantém a conexão com o sync. Manter a conexão é importante, para aguardar a resposta



import socket
import time
import json # If you want to send JSON messages
import os

# --- Configuration for the Client ---
SERVER_HOST = "192.168.15.7" # IP address of the machine running main_app.py
SERVER_PORT = 5000         # Port your main_app.py's network listener is using

def send_message_to_server(message):
    """Sends a message to the server and prints any response."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        try:
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            print(f"Client: Connected to server at {SERVER_HOST}:{SERVER_PORT}")

            # Send the message (ensure it's bytes)
            client_socket.sendall(message.encode('utf-8'))
            print(f"Client: Sent message: '{message}'")

            # --- Optional: Receive a response from the server ---
            # Your main_app.py currently just processes the network message and publishes to MQTT.
            # It doesn't send a direct TCP response back to the client.
            # If you wanted it to, you would need to add `conn.sendall()` in `handle_network_client_connection`
            # in `main_app.py`.
            # For now, this part will likely block or receive nothing unless the server sends something.
            # It's here for completeness if you decide to add server-side responses later.
            # try:
            #     response_data = client_socket.recv(1024) # Read up to 1024 bytes
            #     if response_data:
            #         print(f"Client: Received response: '{response_data.decode('utf-8')}'")
            # except socket.timeout:
            #     print("Client: No response received within timeout.")
            # except Exception as e:
            #     print(f"Client: Error receiving response: {e}")

        except ConnectionRefusedError:
            print(f"Client: Connection refused. Is the server running on {SERVER_HOST}:{SERVER_PORT}?")
            print("Client: Also check firewalls on the server machine.")
        except socket.timeout:
            print("Client: Connection timed out.")
        except Exception as e:
            print(f"Client: An error occurred: {e}")
        finally:
            print("Client: Connection closed.")

if __name__ == "__main__":
    print("--- Starting Client Application ---")


    # Example 2: Send a JSON formatted message (if your protocol expects it)
    json_message = {"command": "REQUEST_ACCESS", "client_id":f"{os.getpid()}"}
    send_message_to_server(json.dumps(json_message)) # Convert dict to JSON string
    time.sleep(1)

    json_message = {"command": "DONE", "client_id":f"{os.getpid()}"}
    send_message_to_server(json.dumps(json_message)) # Convert dict to JSON string
    time.sleep(1)

    print("--- Client application finished sending messages. ---")
