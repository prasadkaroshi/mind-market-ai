# run_app.py (Complete and Final Version)

import socket
import subprocess
import sys
import asyncio

# CRITICAL FIX: Set the policy for Windows at the top of the launcher script.
# This ensures the correct event loop policy is active before Streamlit starts.
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def find_open_port(start_port=8501, end_port=9000):
    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise IOError("Could not find any open port in the specified range.")

def run_streamlit():
    print("--- Starting AI Stock Analyzer ---")
    try:
        port = find_open_port()
        print(f"Found an open port: {port}. Launching app...")
        print("Your app will be available at:")
        print(f"  > http://localhost:{port}")
        
        # Command to run streamlit
        command = [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", str(port)]
        
        # The process will run in this terminal window
        process = subprocess.Popen(command)
        process.wait()

    except IOError as e:
        print(f"ERROR: {e}")
    except KeyboardInterrupt:
        print("\n--- Shutting down AI Stock Analyzer ---")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    run_streamlit()