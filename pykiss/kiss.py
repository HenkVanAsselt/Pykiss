#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""HAM KISS protocol, implemented in Python"""

# Local imports
from lib.helper import debug
from lib.decorators import dumpArgs

# ---- Constants -------------


SERIAL_TIMEOUT = 0.01
BUFSIZE = 1000

# KISS Special Characters
# http://en.wikipedia.org/wiki/KISS_(TNC)#Special_Characters
# http://k4kpk.com/content/notes-aprs-kiss-and-setting-tnc-x-igate-and-digipeater
# Frames begin and end with a FEND/Frame End/0xC0 byte
FEND = b"\xC0"      # Marks START and END of a Frame
FESC = b"\xDB"      # Escapes FEND and FESC bytes within a frame
TFEND = b"\xDC"     # Transposed Frame End
TFESC = b"\xDD"     # Transposed Frame Escape
FESC_TFEND = b"".join([FESC, TFEND])        # "FEND is sent as FESC, TFEND" # 0xC0 is sent as 0xDB 0xDC
FESC_TFESC = b"".join([FESC, TFESC])        # "FESC is sent as FESC, TFESC"  # 0xDB is sent as 0xDB 0xDD

# KISS Command Codes
DATA_FRAME = b"\x00"
TX_DELAY = b"\x01"
PERSISTENCE = b"\x02"
SLOT_TIME = b"\x03"
TX_TAIL = b"\x04"
FULL_DUPLEX = b"\x05"
SET_HARDWARE = b"\x06"
RETURN = b"\xFF"

# Alternate command code spellings
DATAFRAME = DATA_FRAME
TXDELAY = TX_DELAY
P = PERSISTENCE
SLOTTIME = SLOT_TIME
TXTAIL = TX_TAIL
FULLDUPLEX = FULL_DUPLEX
SETHARDWARE = SET_HARDWARE

DEFAULT_KISS_CONFIG_VALUES = {
    "TX_DELAY": 40,
    "PERSISTENCE": 63,
    "SLOT_TIME": 20,
    "TX_TAIL": 30,
    "FULL_DUPLEX": 0,
}

KISS_ON = "KISS $0B"
KISS_OFF = b"".join([FEND, RETURN, FEND, FEND])

NMEA_HEADER = b"".join([FEND, b"\xF0", b"$"])

UI_PROTOCOL_ID = b"\xF0"

"""Python KISS Module Utility Functions Definitions."""


kiss_cmds = {
    0x00: "DATAFRAME",
    0x01: "TXDELAY",
    0x02: "PERSISTENCE",
    0x03: "SLOTTIME",
    0x04: "TXTAIL",
    0x05: "FULLDUPLEX",
    0x06: "SETHARDWARE",
    0xFF: "RETURN",
}


# --------------------------------------------------------------------------------------------------------------------
def decode_cmdbyte(cmdbyte) -> tuple:
    r"""Decode the given command byte.

    :param cmdbyte: The command byte to decode
    :returns: tuple of the command name string, and the port index.

    >>> decode_cmdbyte(0x00)
    ('DATAFRAME', 0)

    >>> decode_cmdbyte(0xFF)
    ('RETURN', 0)

    >>> decode_cmdbyte(0x34)
    ('TXTAIL', 4)
    """

    if cmdbyte == 0xFF:
        return "RETURN", 0

    cmd = cmdbyte & 0x0F
    # debug(f"{cmd=}")
    portindex = cmdbyte & 0xF0 >> 4
    # debug(f"{portindex=}")

    cmd_str = kiss_cmds.get(cmd, "--UNKNOWN--")
    # debug(f"{cmd_str=}")

    return cmd_str, portindex


# --------------------------------------------------------------------------------------------------------------------
def encode_command_and_port_to_byte(cmd=0, port=0) -> bytes:
    """Given the command and port index, create a single byte.

    :param cmd: The command, which can be an interger or a byte
    :param port: The port index, which can be an integer or a byte
    :returns: A single byte

    See https://en.wikipedia.org/wiki/KISS_(TNC) for mor details

    >>> encode_command_and_port_to_byte(cmd=0, port=5)
    b'\x56'
    """

    INVALID = b""

    if isinstance(cmd, int):
        c = cmd
    elif isinstance(cmd, bytes):
        c = cmd[0]
    else:
        # print('Invalid type for "cmd"')
        return INVALID
    if c > 16:
        # debug(f"Invalid value {cmd=}")
        return INVALID

    if isinstance(port, int):
        p = port
    elif isinstance(port, bytes):
        p = port[0]
    else:
        # debug('Invalid type for "port"')
        return INVALID
    if p > 16:
        # debug(f"Invalid value {port=}")
        return INVALID

    ret = p << 4  # port number in the high nibble
    ret = ret | c  # command in the low nibble

    return bytes([ret])


# --------------------------------------------------------------------------------------------------------------------
@dumpArgs
def encode_dataframe(data: bytes, port=0) -> bytes:
    r"""Encode the given data to a KISS frame.

    :param data: The date to encode to KISS
    :param port: Optional port to use to transmit on. Default is 0.
    :returns: The encoded KISS data, or empty b'' in case of an error

    >>> encode_dataframe(b'TEST')
    b'\xc0\x00TEST\xc0'

    """

    # Check if a valid portnumber is given
    if port > 14 or port < 0:
        print(f"ERROR, invalid port index {port}")
        return b""

    # Intialialize the frame, which will start with an FEND byte
    frame = b""
    frame += FEND  # Start of a KISS frame
    frame += bytes(
        [port << 4]
    )  # Portnumber is represented by the high nibble of the 2nd byte (The low nibble is the command code.)

    for i in data:  # b will be an integer when doing an iteration like this,
        b = bytes([i])  # So b has to be converted to a byte again
        # debug(f"{i=}, {b=}")
        if b == FEND:  # Escape this special character
            frame += FESC
            frame += TFEND
        elif b == FESC:
            frame += FESC
            frame += TFESC
        else:
            frame += b

    frame += FEND  # End of a KISS frame

    # debug(f"{frame=}")
    return frame


# --------------------------------------------------------------------------------------------------------------------
def is_valid_kiss_frame(f) -> bool:
    f"""Check if this frame is valid.
    :param f: the frame to inspect
    :returns: True if valid, False if not

    >>> is_valid_kiss_frame(b'\xC0\x00\x54\x45\x53\x54\xC0')
    True

    >>> is_valid_kiss_frame(b'\xC0')
    False

    >>> is_valid_kiss_frame(b'\xC0\x00\x54\x45\x53\x54')
    False
    """

    valid = True  # Assume it is valid

    # Check for a minimum length
    if len(f) < 2:
        debug(f"ERROR: is_valid_kiss_frame({f=}) KISS frame length < 2.")
        valid = False

    # Check if this kiss frame end with an FEND. If not, there is an error
    if not f[-1:] == FEND:
        debug(f"ERROR: is_valid_kiss_frame({f=}). KISS frame should end with FEND.")
        valid = False

    return valid


# --------------------------------------------------------------------------------------------------------------------
def strip_fends_from_kissframe(frame) -> bytes:
    r"""Strip leading and trailing FENDS from the given kiss frame
    :param frame: The kiss frame to process
    :returns: The stripped frame

    >>> strip_fends_from_kissframe(b'\xC0\x00\x54\x45\x53\x54\xC0')
    b'\x00\x54\x45\x53\x54'
    """

    frame = frame.strip(FEND)
    return frame


# --------------------------------------------------------------------------------------------------------------------
@dumpArgs
def decode_dataframe(frame) -> list:
    r"""Decode the given KISS frame(s) to 'normal' data.

    :param frame: The KISS frame(s) to decode
    :returns: The decoded data frames as a list of byte strings, or an empty list in case of an error.

    >>> decode_dataframe(b'\xC0\x00\x54\x45\x53\x54\xC0')
    b'\x00TEST'

    Notes: The frame sequence is: The sequence is:
        FEND		- Magic frame separator, optional.
        data		- with certain byte values replaced so FEND will never occur here.
        FEND		- Magic frame separator.

    """

    orig_frame = frame  # Just save the original for later reference

    if not is_valid_kiss_frame(frame):
        return []

    frame = strip_fends_from_kissframe(frame)

    # Check if there is another FEND inside this frame.
    # If so, then this 'frame' actually consists of multiple frames.
    # Split the original data in multiple frames.
    # For example
    #       'b'\xc0\x06TNC:FLDIGI 4.0.1\xc0\xc0\x06TRXS:RX\xc0'
    # will become
    #       [b'\x06TNC:FLDIGI 4.0.1', b'\x06TRXS:RX']
    if FEND in frame:
        frames = [t for t in frame.split(b'\xc0') if t]
    else:
        frames = [frame]

    framelist_to_return = []

    for frame in frames:
        data = b""
        transpose = False
        for i in frame:
            b = bytes([i])
            if b == FEND:
                debug(f"ERROR: KISS frame should not have FEND ({FEND=} in the middle. {orig_frame=}")
            if transpose:
                if b == TFESC:
                    data += FESC
                elif b == TFEND:
                    data += FEND
                else:
                    debug(f"ERROR: KISS protocol error.  Found 0x{b} after FESC. {frame=}")
                transpose = False
            elif b == FESC:
                transpose = True
            else:
                data += b
        framelist_to_return.extend([data])

    return framelist_to_return


# --------------------------------------------------------------------------------------------------------------------
def escape_special_codes(s) -> bytes:
    """Escape special codes, per KISS spec.

    :param s: The data to inspect
    :returns: Escaped data

    "If the FEND or FESC codes appear in the data to be transferred, they
    need to be escaped. The FEND code is then sent as FESC, TFEND and the
    FESC is then sent as FESC, TFESC."
    """
    # Original: return s.replace(FESC, FESC_TFESC).replace(FEND, FESC_TFEND)

    s = s.replace(FESC, FESC_TFESC)
    s = s.replace(FEND, FESC_TFEND)
    return s


# --------------------------------------------------------------------------------------------------------------------
def recover_special_codes(s) -> bytes:
    """Recover special codes, per KISS spec.

    :param s: The data to recover
    :returns: The recovered data

    "If the FESC_TFESC or FESC_TFEND escaped codes appear in the data received,
    they need to be recovered to the original codes. The FESC_TFESC code is
    replaced by FESC code and FESC_TFEND is replaced by FEND code."
    - http://en.wikipedia.org/wiki/KISS_(TNC)#Description
    """

    # Original: return s.replace(FESC_TFESC, FESC).replace(FESC_TFEND, FEND)
    s = s.replace(FESC_TFESC, FESC)
    s = s.replace(FESC_TFEND, FEND)
    return s


# --------------------------------------------------------------------------------------------------------------------
# def extract_ui(frame):
#     """
#     Extracts the UI component of an individual frame.
#
#     :param frame: APRS/AX.25 frame.
#     :type frame: str
#     :returns: UI component of frame.
#     :rtype: str
#     """
#     start_ui = frame.split(b"".join([FEND, DATA_FRAME]))
#     end_ui = start_ui[0].split(b"".join([SLOT_TIME, UI_PROTOCOL_ID]))
#     return "".join([chr(x >> 1) for x in end_ui[0]])


# --------------------------------------------------------------------------------------------------------------------
def read_kissframes_from_file(filename) -> list:
    """Open a file with kissframes to read and process later.

    :param filename: The file to read
    :returns: list of kissframes

    A line in the file should be like "c00082a09a92606660889862988a9e608884608c8e84e103f054233134362c3138372c3030342c3030312c3039302c3030302c3030303030303030c0"
    A line returned will be like b'\xc0\x00\x82\xa0\x9a\x92`f`\x88\x98b\x98\x8a\x9e`\x88\x84`\x8c\x8e\x84\xe1\x03\xf0T#146,187,004,001,090,000,00000000\xc0'
    """

    with open(filename) as f:
        lines = f.readlines()

    lines = [bytes.fromhex(line) for line in lines]
    return lines


# --------------------------------------------------------------------------------------------------------------------
class Kiss(object):
    """KISS Object Class."""

    def __init__(self,) -> None:
        self.sock = None

    def __enter__(self):
        return self

    def __exit__(self, exit_type, value, traceback):
        self.close()

    def __del__(self):
        self.close()

    def _read_handler(self, bufsize=None):
        """Helper method to call when reading from KISS interface.
        :param bufsize: The maximum amount of data to be received at once.
        """
        # noinspection PyUnusedLocal
        bufsize = bufsize or BUFSIZE

    # noinspection PyUnusedLocal,PyMethodMayBeStatic
    def _write_handler(self, frame=None):  # pylint: disable=R0201
        """Helper method to call when writing to KISS interface.
        """
        debug("default Kiss _write_handler()")
        del frame

    def close(self):
        """Helper method: stop the Kiss interface
        """
        pass

    def open(self, **kwargs):
        """Helper method: start the Kiss interface
        """
        pass

    # # ------------------------------------------------------------
    # def write_setting(self, name, value):
    #     """Write KISS Command Codes to attached device.
    #     :param name: KISS Command Code Name as a string.
    #     :param value: KISS Command Code Value to write.
    #     """
    #
    #     pass

        # # If the value is an integer, convert it.
        # if isinstance(value, int):
        #     value = chr(value)
        #
        # data = bytes(getattr(kiss, name.upper()))
        # data += value
        # frame = encode_dataframe(data)
        #
        # return self.sock.write(frame)

    # ------------------------------------------------------------
    # noinspection PyTypeChecker
    def read(self, bufsize=None, callback=None, readmode=True) -> list:
        """Read data from KISS device.

        :param bufsize: The maximum amount of data to be received at once.
        :param callback: Call this function with decoded data.
        :param readmode: If True, do not use the callback function, but return the data
        :return: The data (un-kissed), or it calls the callback function
        """

        kiss_data = self._read_handler(bufsize)
        if not kiss_data:
            return []

        # debug(f"read_data() len={len(kiss_data)}), {kiss_data=}")
        data = decode_dataframe(kiss_data)
        # debug(f'Unkissed: {data=} ')

        if readmode and callback:
            callback(data)
            return None
        else:
            return data

    # ------------------------------------------------------------
    def write(self, data, command=0, port=0) -> bool:
        """Writes the given data to the kiss interface.

        :param data: Data to write.
        :param command: The command (as bytes). Default is 0 (DATAFRAME)
        :param port: Optional port number to use. Default is 0
        :returns: True if successfull, False if not
        """

        if not self._write_handler:
            print('No write_handler defined')
            return False

        cmd_byte = encode_command_and_port_to_byte(command, port)

        frame_escaped = escape_special_codes(data)
        frame_kiss = b"".join([FEND, cmd_byte, frame_escaped, FEND])

        self._write_handler(frame_kiss)
        return True

    # ------------------------------------------------------------
    def write_command(self, data, port=0):
        """Writes the given data to the kiss interface
        :param data: Data to write.
        :param port: Optional port number to use. Default is 0

        This function will implicetely use the kiss SETHARDWARE command
        """

        self.write(data, command=SETHARDWARE, port=port)


# --------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    """The main of this module will perform some tests"""

    import lib.helper
    lib.helper.clear_debug_window()

    test_obj = Kiss()
    print(repr(test_obj))

