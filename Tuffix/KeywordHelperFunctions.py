##########################################################################
# changing the system during keyword add/remove
# AUTHOR: Kevin Wortman, Jared Dyreson
##########################################################################

import apt
import pickle
import pathlib
from functools import partial
import psutil
import re
import requests

class LinkChecker:
    def __init__(self):
        self._re = re.compile("(?P<content>.*)\.git")


    # def link_up(self, link: str) -> tuple[bool, int]:
    def link_up(self, link: str):
        request = requests.get(link)
        status = ((request.status_code >= 200)
                  and (request.status_code <= 299))
        return (status, request.status_code)

    def check_links(self, manifest: dict) -> None:
        for name, container in manifest.items():
            link, is_git = container
            if(is_git):
                link = self._re.match(link).group("content")

            status, code = self.link_up(link)
            if not(status):
                raise UsageError(
                    f'[INTERNAL ERROR] Could not reach link {link}, received code: {code}')

class ProcessHandler():
    """
    Get a list of PIDs running on the system
    If we run into a EnvironmentError while installing a package, we need to remove the process holding `apt`
    And then re-run the command
    https://stackoverflow.com/a/64906644

    NOTE: THIS IS UNTESTED
    """

    def __init__(self):
        self.processes = self.gather_processes()

    def gather_processes(self) -> dict:

        container = {}

        for proc in psutil.process_iter():
            if(proc.name() not in container):
                container[proc.name()] = [proc.pid]
            else:
                container[proc.name()].append(proc.pid)

        return container

    def remove_process(self, name: str) -> None:
        if(not isinstance(name, str)):
            raise ValueError(
                f'expecting `str`, received {type(name).__name__}')
        proc_id_container = self.container[name]  # list of PIDs
        # ^ Above will raise KeyError if the dictionary does not contain the proper name of the process you are interested in
        for __id in proc_id_container:
            psutil.Process(__id).terminate()  # kill the process


def edit_deb_packages(package_names, is_installing):
    if not (isinstance(package_names, list) and
            all(isinstance(name, str) for name in package_names) and
            isinstance(is_installing, bool)):
        raise ValueError
    print(
        f'[INFO] Adding all packages to the APT queue ({len(package_names)})')
    cache = apt.cache.Cache()
    cache.update()
    cache.open()

    for name in package_names:
        print(
            f'[INFO] {"Installing" if is_installing else "Removing"} package: {name}')
        try:
            cache[name].mark_install() if(
                is_installing) else cache[name].mark_delete()
        except KeyError:
            raise EnvironmentError(
                f'[ERROR] Debian package "{name}" not found, is this Ubuntu?')
    try:
        cache.commit()
    except OSError:
        DEFAULT_PROCESS_HANDLER.remove_process("apt")
        raise EnvironmentError('[FATAL] Could not continue, apt was holding resources. Processes were killed, please try again.')
    except Exception as e:
        cache.close()
        raise EnvironmentError(f'[ERROR] Could not install {name}: {e}.')
    finally:
        # unittest complains there is an open file but I have tried closing it in every avenue
        # NOTE : possible memory leak
        cache.close()

class PickleFactory():
    """
    Pickle a custom class to disk so it can be ressurected for debugging
    purposes.
    """

    def __init__(self):
        pass

    def pickle(self, obj, path: pathlib.Path):
        if(not isinstance(path, pathlib.Path)):
            raise ValueError

        with open(path.resolve(), 'wb') as fp:
            pickle.dump(obj, fp)

    def depickle(self, path: str):
        with open(path, 'rb') as fp:
            __class = pickle.load(fp)
        return __class

DEFAULT_PICKLER = PickleFactory()
DEFAULT_PROCESS_HANDLER = ProcessHandler()
DEFAULT_LINK_CHECKER = LinkChecker()
