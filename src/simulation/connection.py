"""Connection validation and read-only inspection for the guided launcher."""
import ipaddress
import re


def normalize_host(host):
    if not isinstance(host, str) or not host.strip():
        raise ValueError("Enter the CARLA server hostname or IP address.")
    host = host.strip()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", host):
            raise ValueError("Enter only a hostname or IP address; enter the port separately, without http://.")
        return host


def inspect_server(client):
    """Read server metadata without spawning actors or changing world settings."""
    if client.world is None:
        client.connect()
    version = client.client.get_client_version()
    server_version = client.client.get_server_version()
    if version != server_version:
        raise RuntimeError(f"CARLA version mismatch: Python client {version}, server {server_version}. "
                           "Install the Python client supplied with that server before recording.")
    settings = client.world.get_settings()
    vehicles = [{"id": vehicle.id, "type": getattr(vehicle, "type_id", "vehicle"),
                 "role": vehicle.attributes.get("role_name", "")}
                for vehicle in client.world.get_actors().filter("vehicle.*")]
    return {"host": client.host, "port": client.port, "client_version": version,
            "server_version": server_version, "map": client.world.get_map().name,
            "synchronous_mode": settings.synchronous_mode,
            "fixed_delta_seconds": settings.fixed_delta_seconds,
            "vehicles": sorted(vehicles, key=lambda vehicle: vehicle["id"])}
