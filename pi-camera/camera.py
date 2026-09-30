"""LAN JPEG camera and six-hour archive. Python stdlib + installed rpicam-still."""
import logging
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def next_snapshot(directory, interval):
    return max((p.stat().st_mtime for p in directory.glob('*.jpg')), default=0) + interval


def save_snapshot(directory, frame, now):
    name = datetime.fromtimestamp(now, timezone.utc).strftime('%Y-%m-%dT%H-%M-%S.%fZ.jpg')
    destination = directory / name
    pending = destination.with_suffix('.part')
    pending.write_bytes(frame)
    pending.replace(destination)
    logging.info('Saved %s', destination)
    return destination


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.connection.settimeout(5)
        if self.path.split('?', 1)[0] not in ('/', '/snapshot.jpg'):
            self.send_error(404)
            return
        frame, captured = self.server.frame
        if not frame or time.monotonic() - captured > 15:
            self.send_error(503, 'Waiting for a fresh camera frame')
            return
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'image/jpeg')
            self.send_header('Content-Length', str(len(frame)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(frame)
        except (ConnectionError, TimeoutError):
            pass  # A disconnected viewer must not affect capture.

    def log_message(self, *_):
        pass  # Avoid writing an SD-card log for every Frigate poll.


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    runtime = Path(os.environ.get('RUNTIME_DIRECTORY', '/run/lapinou-camera'))
    archive = Path(os.environ.get('SNAPSHOT_DIR', '/home/pi/lapinou/snapshots'))
    interval = int(os.environ.get('SNAPSHOT_SECONDS', '21600'))
    assert interval > 0
    runtime.mkdir(parents=True, exist_ok=True)
    archive.mkdir(parents=True, exist_ok=True)
    latest = runtime / 'latest.jpg'
    latest.unlink(missing_ok=True)
    command = ['rpicam-still', '--nopreview', '--timeout', '0', '--timelapse', '2000',
               '--zsl', '--framerate', '5', '--width', os.environ.get('WIDTH', '1640'),
               '--height', os.environ.get('HEIGHT', '1232'), '--quality', '90', '--wrap', '3',
               '--output', str(runtime / 'frame%01d.jpg'), '--latest', str(latest), '--verbose', '0']
    with ThreadingHTTPServer(('0.0.0.0', int(os.environ.get('PORT', '8080'))), Handler) as server:
        server.frame = (b'', 0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        camera = subprocess.Popen(command)
        due = next_snapshot(archive, interval)
        stamp, last_frame = None, time.monotonic()
        try:
            while True:
                if camera.poll() is not None:
                    raise RuntimeError(f'Camera exited: {camera.returncode}')
                if time.monotonic() - last_frame > 30:
                    raise RuntimeError('Camera has not produced a frame for 30 seconds')
                try:
                    current = latest.stat().st_mtime_ns
                    if current != stamp:
                        frame = latest.read_bytes()
                        if frame.startswith(b'\xff\xd8') and frame.endswith(b'\xff\xd9'):
                            stamp, last_frame = current, time.monotonic()
                            server.frame = (frame, last_frame)
                            now = time.time()
                            if now >= due:
                                try:
                                    save_snapshot(archive, frame, now)
                                    due = now + interval
                                except OSError:
                                    logging.exception('Snapshot save failed; retrying in one minute')
                                    due = now + 60
                except FileNotFoundError:
                    pass  # rpicam briefly unlinks latest.jpg before updating it.
                time.sleep(.2)
        finally:
            camera.terminate()
            try:
                camera.wait(timeout=5)
            except subprocess.TimeoutExpired:
                camera.kill()
                camera.wait()
            server.shutdown()


if __name__ == '__main__':
    main()
