from pathlib import Path
from threading import Thread
from queue import Queue
from time import sleep
import socket
from tenacity import *

class FolderListener:
    # create the listener and create list of files present already
    def __init__(self, folder_path,  file_pattern):
        self.files = []
        self.new_files = Queue()
        for i in self.get_all_objects(folder_path, file_pattern):
            self.files.append(i)
        self._watcher = Thread(target=self._watch_forever, args=(folder_path,file_pattern))
        self._watcher.start()


    def get_all_objects(self, folder_path: str,  file_pattern: str) -> iter:
        y = Path(folder_path).glob(file_pattern)
        return y

    def _append_new_objects(self, y: iter) -> None:
        for i in y:
            if i not in self.files:
                self.files.append(i)
                self.new_files.put(i)

    def _watch_forever(self, folder_path: str, file_pattern: str) -> None:
        while True: #This could be replaced by some experiment_running flag
            self._append_new_objects(self.get_all_objects(folder_path, file_pattern))
            sleep(1)


# some worker which takes from queue and sends file via socket is needed

class FileSender:
    """Sends new files from queue to a websocket"""
    def __init__(self, queue_name, host, port):
        self.host = host
        self.port = port
        self._sender = Thread(target=self.queue_worker(queue_name))
        self._sender.start()
        # call queue done when done and look for new
        pass

    def queue_worker(self, queue_name: Queue):
        while True:
            if not queue_name.empty():
                new_file_path = queue_name.get()
                self.open_socket_and_send(self.host, self.port, new_file_path)
                queue_name.task_done()
            sleep(1)

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(2), reraise=True)
    def open_socket_and_send(self, host, port, path_to_file):
        s = socket.socket()
        s.connect((host, port))
        file_size = Path(path_to_file).stat().st_size

        s.send(f"{path_to_file.name}<SEPARATOR{file_size}".encode())
        with open(path_to_file, 'rb') as f:
            while True:
                bytes_read = f.read(4096)
                if not bytes_read:
                    break
                s.sendall(bytes_read)
        s.close()

#Servercode is missing