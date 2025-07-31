from flask import Flask, render_template, jsonify
import socket
import threading
import json
import time

app = Flask(_name_)

# Global state
client_status = {f"client_{i+1}": {'active': False, 'last_update': 0, 'client_id': ''} for i in range(5)}
client_id_to_slot = {}  # maps client_id to a fixed slot (client_1, client_2, ...)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    current_time = time.time()
    # Clean up old statuses (if no update in 5 seconds, consider inactive)
    for client in client_status:
        if current_time - client_status[client]['last_update'] > 5:
            client_status[client]['active'] = False
    
    return jsonify(client_status)

def start_monitoring_server():
    def server_thread():
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('0.0.0.0', 6000))
            server_socket.listen(10)
            print("🚀 Monitor server started on port 6000")
            
            while True:
                try:
                    conn, addr = server_socket.accept()
                    print(f"📱 New connection from {addr}")
                    client_thread = threading.Thread(target=handle_client, args=(conn, addr))
                    client_thread.daemon = True
                    client_thread.start()
                except Exception as e:
                    print(f"❌ Accept error: {e}")
                
        except Exception as e:
            print(f"❌ Server error: {e}")
    
    def handle_client(conn, addr):
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    client_id = message.get('client_id', '')
                    status = message.get('status', '')

                    # Assign a fixed slot to this client_id if it's not already mapped
                    if client_id not in client_id_to_slot:
                        for i in range(5):
                            key = f"client_{i+1}"
                            if client_status[key]['client_id'] in ('', str(client_id)):
                                client_id_to_slot[client_id] = key
                                break

                    if client_id in client_id_to_slot:
                        rect_key = client_id_to_slot[client_id]
                        client_status[rect_key]['active'] = (status == 'ENTERING_CRITICAL')
                        client_status[rect_key]['last_update'] = time.time()
                        client_status[rect_key]['client_id'] = str(client_id)
                        print(f"📊 Updated {rect_key} (PID: {client_id}): {status}")
                    else:
                        print(f"⚠️ No slot available for {client_id}")

                except json.JSONDecodeError:
                    print(f"⚠️ Invalid JSON from {addr}")
                except Exception as e:
                    print(f"⚠️ Process error: {e}")
                
        except Exception as e:
            print(f"❌ Client {addr} error: {e}")
        finally:
            conn.close()
    
    server_thread = threading.Thread(target=server_thread)
    server_thread.daemon = True
    server_thread.start()

def start_critical_conflict_logger():
    def logger_thread():
        while True:
            time.sleep(0.1)
            active_clients = [key for key in client_status if client_status[key]['active']]
            if len(active_clients) > 1:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                with open("critical_conflict.log", "a") as log_file:
                    log_file.write(f"[{timestamp}] Conflict! Active clients: {active_clients}\n")
    
    thread = threading.Thread(target=logger_thread)
    thread.daemon = True
    thread.start()

if _name_ == '_main_':
    print("🎯 Starting Mobile Monitor Server...")
    start_monitoring_server()
    start_critical_conflict_logger()
    
    # Get local IP for display
    import subprocess
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        local_ip = result.stdout.strip().split()[0]
        print(f"🌐 Access from mobile: http://{local_ip}:4999")
    except:
        print("🌐 Access from mobile: http://YOUR_IP:4999")
    
    print("💻 Local access: http://localhost:4999")
    app.run(host='0.0.0.0', port=4999, debug=False)
