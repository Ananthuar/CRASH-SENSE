import time
import threading
import sys
import psutil
from backend.core.resolution import system_resolver

def test_throttle():
    print("--- Testing Throttle (renice) ---")
    pid = psutil.Process().pid
    name = "test_script"
    
    # We will throttle ourselves
    system_resolver.throttle_process(pid, name)
    
    # Give it a second to run async
    time.sleep(1)
    
    nice = psutil.Process(pid).nice()
    print(f"Current nice value: {nice}")
    print("If nice=19, throttle succeeded.\n")


def test_cache_drop():
    print("--- Testing System Cache Drop ---")
    system_resolver.clear_sys_cache()
    time.sleep(2)
    print("Check logs above. If it says 'Successfully cleared' or 'requires passwordless sudo', it functioned as expected.\n")


def test_terminate():
    print("--- Testing Graceful Termination (SIGTERM) ---")
    print("Spawning a dummy child process to terminate...")
    import subprocess
    # Run a sleep process that we will terminate
    child = subprocess.Popen(["sleep", "60"])
    
    print(f"Child PID: {child.pid}")
    system_resolver.terminate_process(child.pid, "sleep_dummy")
    
    time.sleep(1)
    
    if child.poll() is None:
        print("Child is STILL running! Terminate failed.")
        child.kill()
    else:
        print(f"Child terminated successfully with code {child.returncode}")


if __name__ == "__main__":
    test_throttle()
    test_cache_drop()
    test_terminate()

