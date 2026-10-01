"""Reserve a fresh experiment directory and make interrupted runs explicit."""
from contextlib import contextmanager
from pathlib import Path
from src.utils.helpers import write_json


@contextmanager
def experiment_directory(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    if any(path.iterdir()):
        raise FileExistsError(f"Experiment directory is not empty: {path}. Choose a new --output path.")
    lock = path / ".experiment.lock"
    # Exclusive creation closes the race between two processes selecting an empty directory.
    with lock.open("x", encoding="utf-8") as stream:
        stream.write("reserved\n")
    started = False
    try:
        if any(item != lock for item in path.iterdir()):
            raise FileExistsError(f"Experiment directory is not empty: {path}.")
        started = True
        write_json(path / "run_status.json", {"status": "running"})
        yield path
    except BaseException as error:
        if started:
            write_json(path / "run_status.json", {"status": "failed", "error_type": type(error).__name__,
                                                   "error": str(error)})
        raise
    else:
        write_json(path / "run_status.json", {"status": "complete"})
    finally:
        lock.unlink(missing_ok=True)
