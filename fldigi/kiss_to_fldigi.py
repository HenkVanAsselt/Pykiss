#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Python KISS Module Class Definitions."""

import kiss
import tcp_kiss
import fldigi

from lib.helper import debug
from lib.decorators import dumpArgs


# --------------------------------------------------------------------------------------------------------------------
# Simple callback function. Just print all  data...
# @dumpArgs
def p(frames):
    for frame in frames:
        print(frame)  # prints whatever is passed in.


# --------------------------------------------------------------------------------------------------------------------
# Simple callback function. Print the data in the frame
# @dumpArgs
def print_frame_data(frames):
    for frame in frames:
        # print(frame[1:])  # prints whatever is passed in.
        s = frame[1:]
        s1 = "".join(map(chr, s))
        # debug(f"{s1=}")
        if 'HOST:' in s1:   # THis is a fldigi to host command. @todo: intercept this earlier.
            continue
        if '\n' in s1 or '\r' in s1:
            print()
        else:
            print(s1, end='')


# --------------------------------------------------------------------------------------------------------------------
def start_fldigi():
    """If fldigi is not already running, start it now.
    """

    if fldigi.find_proces("fldigi.exe"):
        print('fldigi is already running')
        exe = None
    else:
        exe = fldigi.Fligi()
        exe.start()

        # Wait till the fldigi is running...
        for i in range(0, 5):
            running = exe.is_running()
            if running:
                break
            time.sleep(1)

    return exe


# --------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    """The main of this module will perform some tests"""

    import time

    import lib.helper
    lib.helper.clear_debug_window()

    # debug('Starting fldigi')
    # app = start_fldigi()
    # debug('Fldigi is started')

    try:
        # with kiss.TcpKiss("127.0.0.1", 7342) as tcp:
        with kiss.TcpKiss("192.168.0.31", 7342) as tcp:

            tcp.write_command(b"TNC:")  # Ask for the FLDigi version number
            tcp.read(callback=p)
            tcp.write_command(b"MODEML:")   # Ask for list of supported modems (modes)
            tcp.read(callback=p)
            tcp.write_command(b"MODEM: MODEMBW: KISSCRCM:")   # Ask for current modem information
            tcp.read(callback=p)
            tcp.write_command(b"RSIDBCAST:ON TRXSBCAST:ON TXBEBCAST:ON")    # Set parameters
            tcp.read(callback=p)
            tcp.write_command(b"KISSRAW:ON")
            tcp.read(callback=p)

            while True:
                tcp.read(callback=print_frame_data)

    except Exception as e:
        debug(e)
        print(e)
        pass

    debug('End of kiss loop')

    # if app:
    #     debug('Stopping app')
    #     errorCode = app.stop(force=False)
    #     print(f"app returned {errorCode}")
