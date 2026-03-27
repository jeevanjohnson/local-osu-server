"""
Purpose/Domain/Concept:
- Runs all the necessary services for the application.
"""

from install_dependencies import install_dependencies

install_dependencies()

import multiprocessing
import sys

# from adapters import log
from processes import (
    interface_process,
    los_process,
    proxy_process,
    songs_folder_process,
    # TODO: mirror_process,
)


def main():

    processes: list[multiprocessing.Process] = [
        multiprocessing.Process(target=process, daemon=True, name=process.__name__)
        for process in [
            songs_folder_process,
            proxy_process,
            los_process,
            interface_process,
        ]
    ]

    for process in processes:
        print(f"Starting {process.name}...")
        process.start()
        print(f"Succesfully started {process.name}")

    try:
        while any(p.is_alive() for p in processes):
            for process in processes:
                process.join(timeout=1)
                # if not process.is_alive() and process.exitcode != 0:
                #     # log.error(f"{process.name} exited with code {process.exitcode}")

    except KeyboardInterrupt:
        pass

    finally:
        for process in processes:
            if process.is_alive():
                print(f"Terminating {process.name}...")
                process.terminate()
                process.join(timeout=5)

                if process.is_alive():
                    print(f"{process.name} did not stop, killing...")
                    process.kill()
                    process.join()

                print(f"Succesfully terminated {process.name}!")
            # else:
            #     # log.warning(f"{process.name} was already dead")

    sys.exit(130)


if __name__ == "__main__":
    install_dependencies()
    main()
