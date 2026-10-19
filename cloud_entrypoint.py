"""Single API process; optionally run the existing alert worker after readiness."""
import os
import subprocess
import sys
import time
import urllib.request
import signal


def main():
    port=int(os.getenv('PORT','7860'))
    api=subprocess.Popen([sys.executable,'-m','uvicorn','backend:app','--host','0.0.0.0','--port',str(port),'--workers','1'])
    worker=None
    def stop(*_):
        if api.poll() is None:api.terminate()
    signal.signal(signal.SIGTERM,stop)
    try:
        if os.getenv('RUN_ALERT_WORKER','false').lower()=='true':
            for _ in range(300):
                if api.poll() is not None:return api.returncode
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health',timeout=2) as response:
                        if response.status==200:break
                except Exception:time.sleep(1)
            else:raise RuntimeError('API did not become ready; worker not started')
            worker=subprocess.Popen([sys.executable,'alert_worker.py'])
        while api.poll() is None:
            if worker is not None and worker.poll() is not None:
                raise RuntimeError('Alert worker stopped; restarting the container is required')
            time.sleep(1)
        return api.returncode
    finally:
        for process in (worker,api):
            if process and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=15)
                except subprocess.TimeoutExpired:process.kill();process.wait()


if __name__=='__main__':sys.exit(main())
