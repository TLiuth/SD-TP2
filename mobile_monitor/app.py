from flask import Flask, render_template, jsonify
import socket
import threading
import json
import time

app = Flask(__name__)

# Global state
client_status = {f"client_{i+1}": {'active': False, 'last_update': 0, 'client_id': ''} for i in range(5)}

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
                    
                    # Map client ID to one of our 5 rectangles
                    rect_index = (hash(str(client_id)) % 5)
                    rect_key = f"client_{rect_index + 1}"
                    
                    client_status[rect_key]['active'] = (status == 'ENTERING_CRITICAL')
                    client_status[rect_key]['last_update'] = time.time()
                    client_status[rect_key]['client_id'] = str(client_id)
                    
                    print(f"📊 Updated {rect_key} (PID: {client_id}): {status}")
                    
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

if __name__ == '__main__':
    print("🎯 Starting Mobile Monitor Server...")
    start_monitoring_server()
    
    # Get local IP
    import subprocess
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        local_ip = result.stdout.strip().split()[0]
        print(f"🌐 Access from mobile: http://{local_ip}:4999")
    except:
        print("🌐 Access from mobile: http://YOUR_IP:4999")
    
    print("💻 Local access: http://localhost:4999")
    app.run(host='0.0.0.0', port=4999, debug=False)