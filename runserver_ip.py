import socket
import os

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't need to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

ip = get_local_ip()
port = "8000"

print(f"🚀 Starting Django on http://{ip}:{port}/")
os.system(f"python manage.py runserver {ip}:{port}")
