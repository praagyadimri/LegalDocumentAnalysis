import subprocess
import time
import webbrowser
import sys
import os


PROJECT_DIR = r"D:\PROJECTS\DMBS_Latest_RAG"
FRONTEND = os.path.join(
    PROJECT_DIR,
    "index_latest.html"
)


def main():

    print("Starting DMBS Legal AI...")

    backend = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000"
        ],
        cwd=PROJECT_DIR
    )

    print("Starting backend...")

    time.sleep(5)

    print("Opening application...")

    webbrowser.open(
        "file:///" + FRONTEND.replace("\\", "/")
    )

    print("DMBS Legal AI is running.")

    try:

        backend.wait()

    except KeyboardInterrupt:

        print("Stopping application...")

        backend.terminate()


if __name__ == "__main__":
    main()