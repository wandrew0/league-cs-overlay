import wmi
import time
import psutil
import threading
import pythoncom

TARGET_EXE = "League of Legends.exe"


def process_start_listener():
    """Listen for creation events (i.e. process start) for TARGET_EXE."""
    pythoncom.CoInitialize()  # Initialize the COM library for the current thread.
    c = wmi.WMI()
    while True:
        try:
            # Block until a new process matching TARGET_EXE is created.
            watcher = c.watch_for(
                notification_type="Creation", wmi_class="Win32_Process", Name=TARGET_EXE
            )
            watcher()  # This call blocks until an event occurs.
            # When the process starts, call show_ui in a thread-safe manner.
            # root.after(0, show_ui)
            print("League of Legends has been started.")
        except Exception as e:
            print("Error in start listener:", e)
            time.sleep(1)


def process_stop_listener():
    """Listen for deletion events (i.e. process stop) for TARGET_EXE."""
    pythoncom.CoInitialize()  # Initialize the COM library for the current thread.
    c = wmi.WMI()
    while True:
        try:
            # Block until a process matching TARGET_EXE is terminated.
            watcher = c.watch_for(
                notification_type="Deletion", wmi_class="Win32_Process", Name=TARGET_EXE
            )
            watcher()  # This call blocks until an event occurs.
            # root.after(0, hide_ui)
            print("League of Legends has been closed.")
        except Exception as e:
            print("Error in stop listener:", e)
            time.sleep(1)


if __name__ == "__main__":
    threading.Thread(target=process_start_listener, daemon=True).start()
    threading.Thread(target=process_stop_listener, daemon=True).start()
    while True:
        time.sleep(1)
