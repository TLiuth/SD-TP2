import json
from sync.application.controllers.controller import Controller
TOPIC = "BCC362"


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"Cliente conectado com sucesso: {client}")
        client.subscribe(TOPIC)
    else:
        print(f'Erro ao me conectar! codigo={rc}')
        
        
        
def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    print(f'Cliente Subscribed at {TOPIC}')
    print(f'QOS:{granted_qos}')
    
    
def on_message(client, userdata, message, properties=None):
    print('Mensagem recebida!')
    topic = message.topic
    payload = message.payload.decode()
    
    if topic == "BCC362":
        try:
            if(str(payload) == "DONE"):
                print("Processo concluído. Atualizando fila...")
            elif(str(payload) == "REQUEST"):
                print("Processo novo requisitado. Atualizando fila...")
        except ValueError:
            print(f'Payload inválido: {payload}')
            
            
        
        

            
            
            