# One-command CARLA workflow

The guided launcher connects, checks versions, selects or creates a vehicle,
records observations, releases owned actors, compares memory strategies, and
opens a local report. You do not need to edit source code or supply an API key.

## What you need once

- A running CARLA server and its hostname/IP and port (normally 2000).
- A Python client matching that server's version on a compatible computer.
- This project and its dependencies installed on that client computer.

The server and client can share a computer. For a remote server, the RPC and
streaming ports (normally 2000 and 2001) must be reachable through the lab network
or VPN. This launcher does not deploy servers, create cloud accounts, configure
firewalls, or set up SSH authentication.

Your current Mac environment uses Python 3.14 and has no CARLA client. For CARLA
0.9.16, the documented packaged platform is Windows/Ubuntu with Python 3.7–3.12;
this project uses Python 3.11 or newer, so use **Python 3.11 or 3.12** with that
CARLA release. Running the launcher on the CARLA lab/server machine is often the
simplest option. A server address alone cannot resolve an incompatible client.
See the [CARLA setup guide](https://carla.readthedocs.io/en/0.9.16/start_quickstart/).

On that compatible computer, from this project folder:

```sh
python -m pip install -r requirements-lock.txt
python -m pip install carla==0.9.16
```

The second command is an example **only for a 0.9.16 server**. For other versions
install the matching client; for custom server builds use the supplied client
wheel. Client/server version mismatches stop the launcher before recording.

## Guided run

```sh
python -m scripts.start_carla
```

The launcher asks for:

1. Server hostname or IP address. Enter only the address, without `http://`.
2. Port, default 2000.
3. Recording length in observed frames, default 300 for a short initial check.
4. A listed vehicle ID, or `demo` to create one autopilot vehicle. A sole hero/ego
   vehicle is the default selection. When the world has no vehicles, demo is the
   default option in an asynchronous world.

After these entries, recording and analysis run automatically. New output folders
are generated each time under `data/results/carla_TIMESTAMP_UNIQUEID/`.
On a desktop the report opens in your browser. On a headless machine the launcher
prints the report location; copy/download that folder to view it on your Mac.
Results are stored on the machine running the launcher, not automatically synced.

## Try the workflow now on your Mac

From your project folder:

```sh
venv/bin/python -m scripts.start_carla --offline
```

This uses the bundled ten-event sample and budgets 2, 5, and 10. It clearly labels
itself an offline check and never contacts CARLA. It verifies the report workflow,
not a live simulator connection.

## Connection check only

```sh
python -m scripts.start_carla --host YOUR_SERVER --port 2000 --check --non-interactive
```

This lists versions, map, clock mode, and existing vehicles. It does not spawn
actors, change world settings, record data, or create result directories.

## Unattended runs

Existing vehicle:

```sh
python -m scripts.start_carla --host YOUR_SERVER --port 2000 --vehicle-id 123 --frames 600 --non-interactive --no-browser
```

New demo vehicle:

```sh
python -m scripts.start_carla --host YOUR_SERVER --port 2000 --demo --frames 600 --non-interactive --no-browser
```

Optional: `--capacities 5 15 30`, `--output NEW_FOLDER`,
`--traffic-manager-port 8050`, `--timeout 20`, and `--debug` for troubleshooting.
Use a Traffic Manager port appropriate for your environment; default is 8050.
The launcher does not reconfigure a shared Traffic Manager's global parameters.

## Vehicle and clock behavior

The new demo vehicle is driven by CARLA's **Traffic Manager autopilot**, not by
the project's memory planner. Memory strategies are compared on its recorded
observations afterward. The demo tries unoccupied map spawn points and removes
its own vehicle on completion or failure. Existing vehicles are neither driven,
destroyed, nor reconfigured by the launcher.

Demo mode requires an asynchronous world and never switches a shared server's
clock mode. For a synchronous scenario, select an existing vehicle while that
scenario's existing controller advances the clock. Without a clock-driving client,
recording times out. The launcher never loads a map or changes the weather.

Spawn order has a fixed seed; Traffic Manager driving is **not** claimed to be
deterministic. The manifest records this distinction. This is an integration demo,
not a controlled closed-loop evaluation of a memory-based driving policy.
See [CARLA Traffic Manager](https://carla.readthedocs.io/en/0.9.16/adv_traffic_manager/)
and [synchronization](https://carla.readthedocs.io/en/0.9.16/adv_synchrony_timestep/).

## Output and failures

- `session.json`: connection details, vehicle mode, and demo cleanup status.
- `events.jsonl`: recorded observations.
- `events.metadata.json`: recorder completion, versions, and acquisition caveats.
- `analysis/comparison.html`: comparison report.
- `analysis/`: CSV/JSON results, provenance, and traces.
- `run_status.json`: complete or failed session status.

An incomplete recording is preserved but is not automatically analyzed. Existing
results cannot be overwritten. Ctrl+C triggers cleanup and preserves partial data.
When a server becomes unreachable, cleanup cannot be guaranteed; check warning
messages and `session.json` for any owned vehicle that may remain.

A single continuous recording is **one episode**, not hundreds of independent
trials. Its report therefore has no multi-episode confidence interval. Collect
independent, controlled scenarios and use the research evaluation protocol for
publication claims. Live CARLA has not been tested in this environment; the
launcher is covered by mocked integration tests and an actual offline demo.
