# Troubleshooting by observed symptom

| Symptom | Check |
|---|---|
| `START_ALL.bat` reports missing model, folder, build, or Python | Restore that local file/folder or rebuild; read the exact path in its error. Do not start an old launcher as a substitute. |
| Port 5000 occupied | Open <http://localhost:5000/>. If it is the current gallery, rerun `START_ALL.bat` to reuse it. If another app owns the port, stop that app before starting. |
| Gallery HTTP unreachable in `CHECK_SYSTEM.bat` | Inspect backend window, config paths, and port 5000. The check never triggers a camera upload. |
| Wi-Fi IPv4 differs from camera's stored laptop target | Put laptop and camera on the same reachable network; update the camera upload target in its verified firmware if the laptop IP changed. `localhost` is only for laptop processes. |
| Main ESP32 prints `EVENT` but no new gallery photo | `EVENT` confirms a GPIO19 pulse only. Check camera 5 V **under capture/upload load**, common GND, GPIO19-to-GPIO13 trigger, camera boot, hotspot connectivity, and camera upload logs. |
| Some but fewer than five frames appear | Inspect burst missing slots, camera power dips, Wi-Fi drops, HTTP error codes, and whether another trigger was sent while the camera was busy. |
| Five photos arrive but ML stays pending | Inspect worker window and heartbeat. Queued jobs survive worker restarts; `START_ALL.bat` restarts an absent worker. A held worker lock with stale heartbeat needs investigation. |
| `No person detected` despite visible person | Open the original full image. Improve framing and light, keep the person fully visible for the burst, and compare annotated result. This label is a model result, not proof the scene is empty. |
| React page looks old | In `frontend/`, run `npm run build`, then refresh <http://localhost:5000/>. Normal use does not require `START_DEV.bat`. |
| Camera or main ESP32 repeatedly resets | Check physical power and wiring, not only the software status. Measure camera 5 V/GND under load; try a stable regulated 5 V supply and sound USB cable. |

For a snapshot of the current state, double-click `CHECK_SYSTEM.bat`: it reads the gallery root and the SQLite database without changing records. Then run `BACKUP_DATA.bat` after the system becomes quiet. Do not retire legacy data paths until the complete post-reboot hardware gate passes.
