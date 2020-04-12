"""TBD
"""

import os
import sys
import time
import subprocess
import xmlrpc.client

import psutil
import signal

from lib.helper import debug


# ================================================================================================
def find_proces(name="fldigi.exe"):
    """Return a list of processes matching 'name'.

    :param name: The name of the process, by default 'fldigi.exe'
    :returns: list of processes found. Is an empty list when nothing is found
    """

    ls = []
    for p in psutil.process_iter(["name", "exe", "cmdline"]):
        if name == p.info['name'] or \
                p.info['exe'] and os.path.basename(p.info['exe']) == name or \
                p.info['cmdline'] and p.info['cmdline'][0] == name:
            ls.append(p)
    return ls


# ================================================================================================
def kill_proc_tree(pid, sig=signal.SIGTERM, include_parent=True,
                   timeout=None, on_terminate=None):
    """Kill a process tree (including grandchildren) with signal.

    "sig" and return a (gone, still_alive) tuple.
    "on_terminate", if specified, is a callabck function which is
    called as soon as a child terminates.
    """

    assert pid != os.getpid(), "won't kill myself"
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    if include_parent:
        children.append(parent)
    for p in children:
        print(p)
        p.send_signal(sig)
    gone, alive = psutil.wait_procs(children, timeout=timeout,
                                    callback=on_terminate)
    return gone, alive


# ================================================================================================
class Fligi(object):
    """Responsible for launching, monitoring, and terminating the FLDIGI application process, using subprocess.Popen().

    :param hostname: The FLDIGI XML-RPC server's IP address or hostname (usually localhost / 127.0.0.1)
    :param port: The port in which FLDIGI's XML-RPC server is listening on.

    .. note:: Commandline arguments can be found on the following links:

        * `Official Documentation page <http://www.w1hkj.com/FldigiHelp-3.21/html/command_line_switches_page.html/>`_
        * `Man page for FLDIGI <https://www.dragonflybsd.org/cgi/web-man?command=fldigi&section=1/>`_
    """

    # ------------------------------------------------------------------------
    def __init__(self, hostname="127.0.0.1", port=7362):
        """Initialize this class.

        :param hostname: The FLDIGI XML-RPC server's IP address or hostname (usually localhost / 127.0.0.1)
        :param port: The port in which FLDIGI's XML-RPC server is listening on.
        """

        # Intialize variables
        self.platform = sys.platform
        self.hostname = hostname
        self.port = int(port)
        self.process = None
        self.returncode = None

        if self.platform not in ["linux", "win32"]:
            raise Exception(
                "You're probably using an OS that is unsupported.  Sorry about that.  I take pull requests."
            )
        self.client = xmlrpc.client.ServerProxy(
            "http://{}:{}/".format(self.hostname, self.port)
        )

    # ------------------------------------------------------------------------
    def start(self, headless=False, wfall_only=False):
        """Start fldigi (preferably in the background).

        :param headless: if True, starts the FLDIGI application in headless mode (POSIX only!  Doesn't work in Windows)
        :param wfall_only: If True, start FLDIGI in 'waterfall-only' mode.  (POSIX only!  Doesn't work in Windows)

        :Example:

        # >>> import fldigikiss
        # >>> c = fldigi.Client()
        # >>> app = fldigi.ApplicationMonitor(headless=True)
        # >>> app.start()
        # >>> # At this point, fldigi should be running in headless mode.
        # >>> c.modem.name  # Ask FLDIGI which modem it's currently using
        # 'CW'
        """

        args = [self._get_path()]           # Determine the path of the fldigi executable
        debug(f"{args=}")

        if self.platform == "win32":
            # Currently, the app crashes if I pass in any params from the windows commandline.
            # For now just ignore all of the params if running this under windows.
            # pass
            args.extend(["--enable-io-port", "2"])    # KISS
            args.extend(["--home-dir", "C:\\Users\\HenkA"])
            args.extend(["--config-dir", "C:\\Users\\HenkA\\fldigi.files"])
        else:
            args.extend(["--arq-server-address", self.hostname])
            args.extend(["--arq-server-port", str(self.port)])
            if headless is True:
                if self.platform == "win32":
                    raise Exception(
                        "cannot run headless with win32.  Headless mode is only supported on Linux."
                    )
                else:  # Assumes cygwin, linux, and darwin can utilize xvfb to create a fake x server
                    args.insert(
                        0, "xvfb-run"
                    )  # http://manpages.ubuntu.com/manpages/zesty/man1/xvfb-run.1.html
                    args.append("-display")
                    args.append(":99")
            else:
                if wfall_only is True:  # consider this modal with 'headless'
                    args.append("--wfall-only")
            # args.extend(['-title', 'fldigi'])  # Set the title to something predictable.

        debug(f"Process arguments {args=}")
        self.process = subprocess.Popen(args)
        debug(f"starting {self.process}")
        start = time.time()
        while True:
            try:
                if self.client.fldigi.name() == "fldigi":
                    debug('found name "fldigi"')
                    break
            except ConnectionRefusedError:
                debug('ConnectionRefused. Trying again')
                pass
            else:
                debug('Connection possible')
            if time.time() - start >= 10:
                debug('Max time exceeded.')
                break
            debug('sleeping for 1/2 second')
            time.sleep(0.5)

    # ------------------------------------------------------------------------
    def stop(self, save_options=True, save_log=True, save_macros=True, force=True) -> int:
        """Attempts to gracefully shut down fldigi.

        :param save_options: If True,
        :param save_log: If True,
        :param save_macros: If Ture,
        :param force: If True...
        :returns:  the error code.

        :Example:

        # >>> import pyfldigi
        # >>> app = pyfldigi.ApplicationMonitor()
        # >>> app.start()
        # >>> time.sleep(10)  # wait a bit
        # >>> app.stop()
        """
        bitmask = int(
            "0b{}{}{}".format(int(save_macros), int(save_log), int(save_options)), 0
        )
        self.client.fldigi.terminate(bitmask)

        if not self.process:
            print("Fligi does not seem to be running")
            return 0

        try:
            debug("Trying to gracefully terminate fldigi...")
            error_code = self.process.wait(timeout=5)
            self.process = None
            debug(f"app returned {error_code=}")
            return error_code
        except subprocess.TimeoutExpired:
            debug("Could not gracefully stop fldigi, now trying with force.")

        if force is True:
            debug("Terminate process with force")
            p = find_proces("fldigi.exe")
            if p:
                pid = p[0].pid
                kill_proc_tree(pid)
                self.process = None
                return 0

    # ------------------------------------------------------------------------
    def kill(self):
        """Kills fldigi.

        .. warning::
            Please try and use stop() before doing this to shut down fldigi gracefully.
            Consider kill() the last resort.

        :Example:

        # >>> import pyfldigi
        # >>> app = pyfldigi.ApplicationMonitor()
        # >>> app.start()
        # >>> time.sleep(10)  # wait a bit
        # >>> app.kill()  # kill the process
        """
        if self.process is not None:
            self.process.kill()
            self.process = None
        # TODO: Interpret error codes and raise custom exceptions

    # ------------------------------------------------------------------------
    def _get_path(self):
        """Get the path to the fldigi executable.
        """
        if self.platform == "win32":
            #  Below is a clever way to return a list of fldigi versions.  This would fail if the user
            #     did not install fldigi into Program Files.
            fldigi_versions = [
                d
                for d in os.listdir(os.environ["ProgramFiles(x86)"])
                if "fldigi" in d.lower()
            ]
            if len(fldigi_versions) == 0:
                raise FileNotFoundError(
                    "Cannot find the path to fldigi.  Is it installed?"
                )
            elif len(fldigi_versions) == 1:
                path = os.path.join(os.environ["ProgramFiles(x86)"], fldigi_versions[0])
                # Check to see if fldigi.exe is in the folder
                if "fldigi.exe" in os.listdir(path):
                    return os.path.join(path, "fldigi.exe")
            else:
                raise Exception(
                    "Found more than one version of fldigi.  Uninstall one."
                )
        else:  # Assume all other OS's are smart enough to place fldigi in PATH
            return "fldigi"

    # # ------------------------------------------------------------------------
    def is_running(self):
        """Determine if FLDIGI is still running.

        .. warning::
            If the AppMonitor did not start FLDIGI, then this function will not return True.
            Ths method only works if FLDIGI was launched using start().

        :return: Returns whether or not the FLDIGI application is running
        """

        if self.process is None:
            return False    # Process is flagged to be NOT running

        processes = find_proces('fldigi.exe')
        if processes:
            return True
        else:
            return False


# ================================================================================================
if __name__ == "__main__":

    app = Fligi()
    app.start()

    for i in range(0, 5):
        running = find_proces('fldigi.exe')
        print(f"{running=}")
        time.sleep(1)

    errorCode = app.stop()
    print(f"app returned {errorCode}")
