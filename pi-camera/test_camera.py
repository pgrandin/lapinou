"""Run: python3 pi-camera/test_camera.py. No camera or third-party packages needed."""
import os
import tempfile
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from camera import Handler, ThreadingHTTPServer, next_snapshot, save_snapshot

scratch = Path(__file__).resolve().parents[1] / 'scratch/pi-camera-tests'
scratch.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(dir=scratch) as folder:
    folder = Path(folder)
    assert next_snapshot(folder, 21600) < time.time()
    now = time.time()
    frame = b'\xff\xd8test\xff\xd9'
    saved = save_snapshot(folder, frame, now)
    os.utime(saved, (now, now))
    assert saved.read_bytes() == frame and not list(folder.glob('*.part'))
    assert next_snapshot(folder, 21600) == now + 21600
    with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
        server.frame = (frame, time.monotonic())
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(base + '/snapshot.jpg?fresh=1') as response:
                assert response.read() == frame
                assert response.headers['Content-Type'] == 'image/jpeg'
                assert response.headers['Cache-Control'] == 'no-store'
            for path, cached, status in [('/missing', server.frame, 404),
                                         ('/snapshot.jpg', (frame, time.monotonic()-16), 503),
                                         ('/snapshot.jpg', (b'', 0), 503)]:
                server.frame = cached
                try:
                    urlopen(base + path)
                    raise AssertionError('Expected HTTP error')
                except HTTPError as error:
                    assert error.code == status
        finally:
            server.shutdown()
print('PASS: JPEG endpoint, cache headers, stale/startup errors, atomic snapshots, restart cadence')
