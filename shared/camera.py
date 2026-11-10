import cv2
import time
from pygrabber.dshow_graph import FilterGraph

class Camera:
    def __init__(self, index):
        self.error = None
        for _ in range(3):
            self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.error = "not_found"
                return
            time.sleep(1)   # wait for the camera to warm up
            if all(self._has_image() for _ in range(3)):
                return
            self.cap.release()
        self.error = "busy"

    def _has_image(self):
        ok, frame = self.cap.read()
        return ok and (frame == 0).mean() < 0.5

    def read(self):
        ok, frame = self.cap.read()
        return frame if ok else None

    def release(self):
        self.cap.release()


def list_cameras():
    return FilterGraph().get_input_devices()

if __name__ == "__main__":
    camera = Camera(0)
    print("error:", camera.error)
    while True:
        frame = camera.read()
        if frame is None:
            break
        cv2.imshow("test", frame)
        if cv2.waitKey(1) == ord("q") or cv2.getWindowProperty("test", cv2.WND_PROP_VISIBLE) < 1:
            break
    camera.release()
    cv2.destroyAllWindows()