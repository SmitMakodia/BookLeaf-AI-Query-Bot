import subprocess
import sys
import time
import os

def main():
    print("Cleaning up older instances...")
    subprocess.run(["stop.bat"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    python_exe = os.path.join("venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"])
    
    print("Installing dependencies...")
    subprocess.run([python_exe, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"])

    print("Resetting database...")
    if os.path.exists("bookleaf.db"):
        try:
            os.remove("bookleaf.db")
        except Exception:
            pass
            
    subprocess.run([python_exe, "-m", "app.db.seed"])

    print("Starting Qdrant...")
    qdrant_process = subprocess.Popen([r"qdrant_bin\qdrant.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("Starting FastAPI Backend...")
    uvicorn_process = subprocess.Popen([python_exe, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"])
    
    print("Starting Streamlit UI...")
    streamlit_env = os.environ.copy()
    streamlit_env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    streamlit_process = subprocess.Popen([python_exe, "-m", "streamlit", "run", "ui/streamlit_app.py"], env=streamlit_env)

    try:
        print("\n" + "="*50)
        print("All services running! Frontend will open automatically in your browser.")
        print("Press Ctrl+C to cleanly stop all services.")
        print("="*50 + "\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nReceived Ctrl+C. Stopping all services gracefully...")
        streamlit_process.terminate()
        uvicorn_process.terminate()
        qdrant_process.terminate()
        
        streamlit_process.wait()
        uvicorn_process.wait()
        qdrant_process.wait()
        
        subprocess.run(["stop.bat"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("All services stopped.")

if __name__ == "__main__":
    main()
