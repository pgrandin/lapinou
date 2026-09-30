# Pi camera daemon

One Python standard-library daemon plus the already installed `rpicam-still`. It keeps the camera open, captures a 1640 × 1232 JPEG about every two seconds, and serves the latest complete image at:

http://192.168.1.150:8080/snapshot.jpg

The first fresh frame is archived immediately, then one every six hours, in `/home/pi/lapinou/snapshots/` on the Pi. Names contain UTC timestamps. Restarting retains the six-hour schedule using the last archived file's modification time. Archives are kept until manually removed; there is no automatic deletion. Frequent preview images rotate through three files in `/run/lapinou-camera/` (RAM), so they do not continually write to the SD card. A stalled or exited camera causes a service restart; the HTTP endpoint returns 503 for missing or stale frames.

## Frigate

Merge `pi-camera/frigate.yaml` into the existing Frigate configuration. It polls the JPEG at 1 fps using `preset-http-jpeg-generic`, with object detection and video recording disabled. The image itself updates about every two seconds. The six-hour archive is independent of Frigate and continues if Frigate is offline. No Frigate server configuration has been changed automatically.

Frigate documents changing JPEG inputs here: https://docs.frigate.video/configuration/camera_specific/#jpeg-stream-cameras

To enable continuous Frigate video recording later, JPEG input requires encoding; see the same documentation. This setup stores stills locally and does not provide RTSP or audio.

The address `192.168.1.150` is the example deployment; substitute your Pi's address in these commands and `frigate.yaml`.

## Install / manage

The files are deployed to `/home/pi/lapinou/camera.py` and `/etc/systemd/system/lapinou-camera.service` on `pi@192.168.1.150`.

```sh
ssh pi@192.168.1.150 'mkdir -p /home/pi/lapinou'
scp pi-camera/camera.py pi-camera/lapinou-camera.service pi@192.168.1.150:/home/pi/lapinou/
ssh pi@192.168.1.150 'sudo install -m 644 /home/pi/lapinou/lapinou-camera.service /etc/systemd/system/lapinou-camera.service && sudo systemctl daemon-reload && sudo systemctl enable --now lapinou-camera'
ssh pi@192.168.1.150 'systemctl status lapinou-camera --no-pager'
ssh pi@192.168.1.150 'journalctl -u lapinou-camera -n 30 --no-pager'
```

Use `sudo systemctl restart lapinou-camera` after changes, or `sudo systemctl disable --now lapinou-camera` to stop it and disable boot startup. The systemd unit exposes `WIDTH`, `HEIGHT`, `PORT`, `SNAPSHOT_DIR`, and `SNAPSHOT_SECONDS` as environment settings. Exposure and white balance currently remain automatic.

## Checks

```sh
python3 pi-camera/test_camera.py
curl --fail http://192.168.1.150:8080/snapshot.jpg -o camera-live.jpg
```

The local test covers JPEG responses, missing/stale frames, cache headers, atomic archive writes, and preserving archive cadence across restarts. Deployment is additionally checked with actual camera frames, FFmpeg's JPEG input options, an accelerated four-second archive schedule in a separate test directory, and systemd restart behavior.
