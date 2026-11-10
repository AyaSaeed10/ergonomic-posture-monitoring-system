from PyQt5.QtCore import QThread, pyqtSignal

from shared.camera import Camera, list_cameras


class CameraService(QThread):
    frame_ready = pyqtSignal(object)   # sends each new frame to the screen
    error = pyqtSignal(str)            # "not_found", "busy" or "disconnected"
    opened = pyqtSignal()              # the camera opened and works
    
    def __init__(self, index):
        super().__init__()
        self.index = index
        self.running = True

    def run(self):
        camera = Camera(self.index)
        if camera.error:
            self.error.emit(camera.error)
            return
        self.opened.emit()
        while self.running:
            frame = camera.read()
            if frame is None:
                self.error.emit("disconnected")
                break
            self.frame_ready.emit(frame)
        camera.release()

    def stop(self):
        self.running = False
        self.wait()


if __name__ == "__main__":
    import sys
    from PyQt5.QtCore import QCoreApplication, QTimer

    app = QCoreApplication(sys.argv)
    service = CameraService(0)
    service.frame_ready.connect(lambda frame: print(frame.shape))
    service.error.connect(print)
    service.start()
    QTimer.singleShot(3000, lambda: (service.stop(), app.quit()))
    app.exec_()