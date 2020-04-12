# coding=utf-8

# pylint: disable=C0301,C0103,W1201,W0333,W0621,R0904,R0201,C0302

# # @file helper.py
# # @brief Small functions to make life easier

""" Small functions to make life easier

Note: Doctest would not run on funtions which made use of @dumpArgs and/or @DumpFuncName.
This has been fixed with the use of functools.wraps in those decorators
See https://stackoverflow.com/questions/22866510/doctest-and-decorators-in-python
"""

# pylint: disable=C0301

# Global imports
import os
import logging
import glob
import inspect
import io
import traceback
import configparser
# import wx

# Local imports
from .tracetool import ttrace


# -------------------------------------------------------------------------------------
# def create_logdir() -> str:
#     """Create the folder for logfiles. The path is stored as param.logdir
#
#     :returns: path to log folder
#     """
#
#     if not param.logdir:
#         current_folder = os.getcwd()
#         param.logdir = os.path.join(current_folder, "log")
#
#     if not os.path.isdir(param.logdir):
#         os.makedirs(param.logdir)
#
#     return param.logdir


# -------------------------------------------------------------------------------------
def create_logger(logfilename):
    """Create logger"""

    # Remove any existing root handlers. This is a bit crude, but it worked for me in
    # solving all kind of weird logging problems.

    debug(f'Create_logger({logfilename})')

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename, mode='w')
    fh.setLevel(logging.DEBUG)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    # add the handlers to logger
    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger


# -------------------------------------------------------------------------------------
def delete_old_logfiles(logdir) -> bool:
    """Delete old logfiles from the given folder
    
    :param logdir: folder in which the logfiles are located
    :returns: True if successfull, False in case of an error
    """

    debug(f"delete_old_logfiles from {logdir}")

    if not logdir:
        return False

    if not os.path.isdir(logdir):
        debug(f"Could not find {logdir} to remove files from")
        return False

    logfilemasks = ["%s/*gui*.log" % logdir, "%s/*cli*.log" % logdir]

    for mask in logfilemasks:
        logfiles = glob.glob(mask)
        logfiles.sort()

        if len(logfiles) > 5:
            files_to_delete = logfiles[:-5]
            for logfile in files_to_delete:
                debug(f"deleting: {logfile}")
                os.remove(logfile)

    return True


# -----------------------------------------------------------------------------
def decrease_path_depth(path, maxdepth=2):
    """Decrease the path to the last folders(s) / filename

    >>> decrease_path_depth('C:\\data\\LXE\\AndroidConfig\\src\\pyadb.py', 2)
    'src\\pyadb.py'

    >>> decrease_path_depth('C:\\data\\LXE\\AndroidConfig\\src\\pyadb.py', 1)
    'pyadb.py'

    """

    path = os.path.normpath(path)
    seperator = os.path.sep
    path_depth = path.count(seperator)
    if path_depth > 1:
        paths = path.split(seperator)
        path = seperator.join(paths[-maxdepth:])
    return path


# -----------------------------------------------------------------------------
def get_version(filename="buildinfo.txt"):
    """Get version number from buildinfo.txt"""

    if not os.path.isfile(filename):
        print(f"could not find {filename} to determine the buildnumber")
        return "xx.xx", "somewhere in March 2019 or later"

    config = configparser.ConfigParser()
    config.read(filename)

    try:
        version = config['DEFAULT']['version']
        builddate = config['DEFAULT']['date']
    except KeyError:
        version = "00.00"
        builddate = "20000101"

    return version, builddate


# ------------------------------------------------------------------------------
def get_builddate(filename="buildinfo.txt"):
    """Get build date from buildinfo.txt"""

    config = configparser.ConfigParser()
    config.read(filename)
    date_str = config['DEFAULT']['date']
    return date_str


# ------------------------------------------------------------------------------
def print_traceback():
    """Print traceback in case of an failure.
    """

    fp = io.StringIO()
    traceback.print_exc(file=fp)
    s = fp.getvalue()

    # param.logger.error(s)

    # Show the traceback  in stdout (or info window)
    print("")
    print("%s" % s)
    print("")

    return


# ------------------------------------------------------------------------------
def get_caller(i=2):
    """ Get the calling function filename and linenumber

    :param i: The index to retreive from the frame info listctrl. Default is 2
    :returns: tuple of filename and linenumber
    """

    frame_info_list = inspect.stack()
    caller = frame_info_list[i]  # This is the frameinfo for the calling module
    frame, filename, lineno, function_name, code_context, index = caller
    return filename, lineno


# -----------------------------------------------------------------------------
def debug(s):
    """ Send message s to logging.debug and print it (if not commented out)

    :param s: message to print
    :return: Nothing

    """

    filename, lineno = get_caller()

    filename = decrease_path_depth(filename, 2)

    ttrace.debug.send(f"{filename} line:{lineno}", s)
    # if param.logger:
    #     param.logger.debug(f"{filename} line:{lineno} : {s}")
    # else:
    #     logging.debug(f"{filename} line:{lineno} : {s}")

    return


# ===============================================================================
# clear_debug_window
# ===============================================================================
def clear_debug_window():
    """Make the ttrace debug window empty
    """

    ttrace.clearAll()
    return


# ===============================================================================
# normalize_text
# ===============================================================================
def normalize_text(s):
    """ Normalize given text

        @param s Text to convert
        @returns New text, or None if there was no text to process.
    """

    if not s:
        return None

    s = s.replace("\x00", "")

    # remove superflouse carriage returns
    s = s.replace("\r\r\n", "\r\n")

    return s


# ===============================================================================
# start_application
# ===============================================================================
def start_application(filename) -> bool:
    """ Check if the given file exists, and if so, start the application
    :param filename: Full path to the given file
    :return: True on success, False in case of an error
    """

    if not os.path.isfile(filename):
        print(f"Error: Could not start {filename} as it was not found")
        return False

    try:
        os.startfile(filename)
        return True
    except OSError:
        print(f"Problem in starting {filename}")
        return False


# ===============================================================================
def send_image_to_clipboard(filename, scalefactor=None) -> bool:
    """ Open the given image file and copy the contents to the Windows clipboard
    :param filename: The full path to the file to open
    :param scalefactor: float (like 0.5) with scalefactor, if required. The default is None
    :returns: False in case of an error

    @todo: Scale the image to a smaller one, by taking a scaling factor in account
    """

    import io
    import win32clipboard
    from PIL import Image

    if not os.path.isfile(filename):
        debug(f"Could not find {filename}")
        return False

    image = Image.open(filename)

    if scalefactor:
        new_width = int(scalefactor * image.size[0])
        new_height = int(scalefactor * image.size[1])
        image = image.resize((new_width, new_height), Image.ANTIALIAS)

    output = io.BytesIO()
    image.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]
    output.close()

    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()

    return True


# ===============================================================================
def ask_userddata_if_first_run():
    """This function will ask for some data after it was discovered that this
    program is run for the very first time"""

    tagfile = "first_run.tag"
    if not os.path.isfile("first_run.tag"):
        debug(f"tagfile {tagfile} is not found. Not the first run of this application")
        return False

    dlg = wx.TextEntryDialog(
        None, 'What is your favorite programming language?',
        'Eh??', 'Python')

    dlg.SetValue("Python is the best!")

    if dlg.ShowModal() == wx.ID_OK:
        print('You entered: %s\n' % dlg.GetValue())

    dlg.Destroy()

    os.remove(tagfile)
    return True


# ===============================================================================
def is_exe(path) -> str:
    """Determine if the give path can be found and is a file

    :param path: The path to examine
    :returns: string to full path of exe if found, empty string if not.
    """

    exe = os.path.abspath(path)
    if os.path.isfile(exe):
        debug(f"Found {exe}")
        return exe
    else:
        return ""


# ===============================================================================
if __name__ == "__main__":

    delete_old_logfiles("c:\\data\\LXE\\AndroidConfig\\src\\log")

    # app = wx.App()
    # print('simualate 1st run')
    # ask_userddata_if_first_run()
    # print('simulate 2nd run')
    # ask_userddata_if_first_run()
