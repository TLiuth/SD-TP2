import paho.mqtt.client as mqtt

mqtt_client = mqtt.Client() # Nome pode ser passado como argumento opcional
mqtt_client.connect(host="localhost", port=1883)
mqtt_client.publish(topic="BCC362", payload='{ "minha":"mensagem" }')