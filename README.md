# Stealth Play-it Service
This project provides a resilient, silent background service that combines a local SOCKS4 proxy with a persistent playit.gg tunnel. It is designed to run completely invisibly, manage itself, and clean up after termination, making it ideal for providing reliable, long-term access to a local network service without manual intervention.

Features
SOCKS4 Proxy Server: Starts a stable SOCKS4 proxy server on 127.0.0.1:8088.

Automated playit.gg Agent:

Automatically detects the host OS (Windows x64 or Linux x64) and downloads the correct playit.gg executable.

Fetches the required playit.gg secret key from a remote URL.

Runs the playit.gg agent silently in the background.

Self-Healing: A monitoring loop runs every 60-120 seconds to ensure both the SOCKS4 proxy and the playit.gg agent are active. If either service crashes, it is automatically restarted.

Stealth Operation:

Runs completely in the background with no visible console window or UI.

Does not create any log files.

Auto-Cleanup: Upon termination (via Ctrl+C, system shutdown, or kill command), the script automatically terminates the playit.gg process and deletes the downloaded executable from the temporary directory.

Requirements
Python 3.6+

requests library

You can install the requests library using pip:

bash
pip install requests
Configuration
Before running the script, you must configure two variables at the top of the file:

PLAYIT_GITHUB_AUTH_TOKEN_RAW_URL: This must be set to the raw URL of a text file containing your playit.gg secret key.

python
# --- CONFIGURATION & CONSTANTS ---
PLAYIT_GITHUB_AUTH_TOKEN_RAW_URL = 'https://raw.githubusercontent.com/your-user/your-repo/main/your-key.txt'
The key file can be in one of two formats:

A raw string: 424d27ca39db4b37fbd43842f2e94abd23261954006932925408a8cc3eb919d4

A variable assignment: secret_key = "424d27ca39db4b37fbd43842f2e94abd23261954006932925408a8cc3eb919d4"

PROXY_PORT (Optional): By default, the SOCKS4 proxy runs on port 8088. You can change this if needed.

python
PROXY_PORT = 8088
Usage
The script is designed to be run as a background service. The method for execution differs between Windows and Linux.

On Windows
To ensure the script runs silently without a console window, save the file with a .pyw extension (e.g., service.pyw).

To run: Simply double-click the service.pyw file.

To stop and clean up: Open Task Manager, find the pythonw.exe process that is running the script, and terminate it. The cleanup routine will automatically run.

On Linux
Save the file with a standard .py extension (e.g., service.py).

Make the script executable:

bash
chmod +x service.py
Run in the background using nohup:

bash
nohup ./service.py &
This ensures the script continues running even after you close your terminal.

To stop and clean up: Find the Process ID (PID) of the script and use the kill command.

bash
# Find the PID
ps aux | grep service.py

# Terminate the process (replace <PID> with the actual ID)
kill <PID>
The cleanup routine will automatically run upon termination.

How It Works
Initial Delay: The script waits 10 seconds after starting to allow network services to initialize.

Setup: It downloads the playit.gg agent and fetches the secret key. If either step fails, the script will exit.

Execution: It starts two threads:

One for the SOCKS4 proxy server.

One for the main monitoring loop.

Monitoring: The main loop sleeps for a random interval between 60 and 120 seconds. After waking, it checks if the proxy and playit.gg process are still running. If not, it restarts them.

Termination: The atexit and signal modules are used to register a cleanup() function that is called whenever the script exits, ensuring the playit.gg process is killed and the executable is deleted.

# Disclaimer
This tool is designed for legitimate purposes, such as maintaining persistent access to your own development environments or game servers. Ensure you have authorization to run this software on any system you deploy it to. Unauthorized use is strictly discouraged.
