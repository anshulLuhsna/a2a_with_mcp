import subprocess
import os
import sys
import time
import threading

print("🔍 Running MCP server script manually...\n")

# Set up the proper environment variables
env = os.environ.copy()
src_dir = os.path.abspath("sentiment_analysis_agent/mcp-server-reddit/src")

# Add the src directory to PYTHONPATH
if 'PYTHONPATH' in env:
    env['PYTHONPATH'] = f"{src_dir}{os.pathsep}{env['PYTHONPATH']}"
else:
    env['PYTHONPATH'] = src_dir

print(f"📂 Setting PYTHONPATH to: {env.get('PYTHONPATH', 'Not set')}")
print(f"🌐 Current directory: {os.getcwd()}")
print(f"🚀 Running command: python -m mcp_server_reddit\n")

# Change directory to src so the module can be found
os.chdir(src_dir)
print(f"📁 Changed to directory: {os.getcwd()}\n")

# Set up a process with real-time output
proc = subprocess.Popen(
    ["python", "-m", "mcp_server_reddit", "--debug"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
    env=env,
)

# Function to read output in real-time
def read_output(pipe, prefix):
    for line in iter(pipe.readline, ''):
        print(f"{prefix} {line.strip()}")

# Start threads to read output
stdout_thread = threading.Thread(target=read_output, args=(proc.stdout, "📤"))
stderr_thread = threading.Thread(target=read_output, args=(proc.stderr, "⚠️"))
stdout_thread.daemon = True
stderr_thread.daemon = True
stdout_thread.start()
stderr_thread.start()

try:
    print("⏳ Waiting for server to start... (30s)")
    start_time = time.time()
    
    # Wait for server to start (max 30 seconds)
    while time.time() - start_time < 30:
        # Check if process has exited
        if proc.poll() is not None:
            print(f"⛔ Process exited with code {proc.returncode}")
            break
            
        # Try to connect to the server
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(('localhost', 10101))
            sock.close()
            
            if result == 0:
                print("✅ Server is running! Port 10101 is open.")
                break
        except Exception as e:
            pass
            
        time.sleep(0.5)
        
    # If we didn't break out of the loop, the server didn't start
    else:
        print("❌ Server did not start within 30 seconds")
    
    # Let server run for 5 more seconds to see more output
    time.sleep(5)
    
except KeyboardInterrupt:
    print("🛑 User interrupted")
finally:
    print("🧹 Cleaning up...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    
    # Change back to original directory
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(src_dir))))
