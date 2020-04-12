"""Python KISS Module Utility Functions Definitions."""

# Local imports
import kiss
from lib.helper import debug
from lib.decorators import dumpArgs

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
def decode_cmd(cmdbyte) -> tuple:
    r"""Decode the given command byte.
    
    :param cmdbyte: The command byte to decode
    :returns: tuple of the command name string, and the port index.

    >>> decode_cmd(0x00)
    ('DATAFRAME', 0)

    >>> decode_cmd(0xFF)
    ('RETURN', 0)

    >>> decode_cmd(0x34)
    ('TXTAIL', 4)
    """

    if cmdbyte == 0xFF:
        return "RETURN", 0

    cmd = cmdbyte & 0x0F
    debug(f"{cmd=}")
    portindex = cmdbyte & 0xF0 >> 4
    debug(f"{portindex=}")

    cmd_str = kiss_cmds.get(cmd, "--UNKNOWN--")
    debug(f"{cmd_str=}")

    return cmd_str, portindex


# --------------------------------------------------------------------------------------------------------------------
def encode_command_and_port_to_byte(cmd=0, port=0) -> bytes:
    """Given the command and port index, create a single byte.

    :param cmd: The command, which can be an interger or a byte
    :param port: The port index, which can be an integer or a byte
    :returns: A single byte
    
    See https://en.wikipedia.org/wiki/KISS_(TNC) for mor details
    """

    INVALID = b""

    if isinstance(cmd, int):
        c = cmd
    elif isinstance(cmd, bytes):
        c = cmd[0]
    else:
        print('Invalid type for "cmd"')
        return INVALID
    if c > 16:
        debug(f"Invalid value {cmd=}")
        return INVALID

    if isinstance(port, int):
        p = port
    elif isinstance(port, bytes):
        p = port[0]
    else:
        debug('Invalid type for "port"')
        return INVALID
    if p > 16:
        debug(f"Invalid value {port=}")
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

    debug(f"{data=}")
    debug(f"{port=}")

    # Check if a valid portnumber is given
    if port > 14 or port < 0:
        print(f"ERROR, invalid port index {port}")
        return b""

    # Intialialize the frame, which will start with an FEND byte
    frame = b""
    frame += kiss.FEND  # Start of a KISS frame
    frame += bytes(
        [port << 4]
    )  # Portnumber is represented by the high nibble of the 2nd byte (The low nibble is the command code.)

    for i in data:  # b will be an integer when doing an iteration like this,
        b = bytes([i])  # So b has to be converted to a byte again
        debug(f"{i=}, {b=}")
        if b == kiss.FEND:  # Escape this special character
            frame += kiss.FESC
            frame += kiss.TFEND
        elif b == kiss.FESC:
            frame += kiss.FESC
            frame += kiss.TFESC
        else:
            frame += b

    frame += kiss.FEND  # End of a KISS frame

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
        debug("ERROR: KISS frame length < 2")
        valid = False

    # Check if this kiss frame end with an FEND. If not, there is an error
    if not f[-1:] == kiss.FEND:
        debug(f"ERROR: KISS frame should end with FEND. {f=}")
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

    frame = frame.strip(kiss.FEND)
    debug(f"stripped frame: {frame=}")
    return frame

# --------------------------------------------------------------------------------------------------------------------
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

    debug("----")
    orig_frame = frame      # Just save the original for later reference

    if not is_valid_kiss_frame(frame):
        return[]

    frame = strip_fends_from_kissframe(frame)

    # Check if there is another FEND inside this frame.
    # If so, then this 'frame' actually consists of multiple frames.
    # Split the original data in multiple frames.
    # For example
    #       'b'\xc0\x06TNC:FLDIGI 4.0.1\xc0\xc0\x06TRXS:RX\xc0'
    # will become
    #       [b'\x06TNC:FLDIGI 4.0.1', b'\x06TRXS:RX']
    if kiss.FEND in frame:
        frames = [t for t in frame.split(b'\xc0') if t]
    else:
        frames = [frame]

    framelist_to_return = []

    debug(f"{frames=}")
    for frame in frames:
        data = b""
        transpose = False
        debug(f"{frame=}")
        for i in frame:
            b = bytes([i])
            # debug(f"{b=}")
            if b == kiss.FEND:
                debug(f"ERROR: KISS frame should not have FEND ({kiss.FEND=} in the middle. {orig_frame=}")
            if transpose:
                if b == kiss.TFESC:
                    data += kiss.FESC
                elif b == kiss.TFEND:
                    data += kiss.FEND
                else:
                    debug(f"ERROR: KISS protocol error.  Found 0x{b} after FESC. {frame=}")
                transpose = False
            elif b == kiss.FESC:
                transpose = True
            else:
                data += b
        debug(f"{data=}")
        framelist_to_return.extend([data])
        debug(f"{framelist_to_return=}")

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
    # Original: return s.replace(kiss.FESC, kiss.FESC_TFESC).replace(kiss.FEND, kiss.FESC_TFEND)

    s = s.replace(kiss.FESC, kiss.FESC_TFESC)
    s = s.replace(kiss.FEND, kiss.FESC_TFEND)
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

    # Original: return s.replace(kiss.FESC_TFESC, kiss.FESC).replace(kiss.FESC_TFEND, kiss.FEND)
    s = s.replace(kiss.FESC_TFESC, kiss.FESC)
    s = s.replace(kiss.FESC_TFEND, kiss.FEND)
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
#     start_ui = frame.split(b"".join([kiss.FEND, kiss.DATA_FRAME]))
#     end_ui = start_ui[0].split(b"".join([kiss.SLOT_TIME, kiss.UI_PROTOCOL_ID]))
#     return "".join([chr(x >> 1) for x in end_ui[0]])


# --------------------------------------------------------------------------------------------------------------------
def strip_df_start(frame) -> bytes:
    """Strip KISS DATA_FRAME start (0x00) and newline from frame.

    :param frame: APRS/AX.25 frame.
    :type frame: str
    :returns: APRS/AX.25 frame sans DATA_FRAME start (0x00).
    :rtype: str
    """

    frame = frame.lstrip(kiss.DATA_FRAME)
    frame = frame.strip()
    return frame


# --------------------------------------------------------------------------------------------------------------------
def strip_nmea(frame) -> bytes:
    """Extract NMEA header from T3-Micro or NMEA encoded KISS frames.

    :param frame: The frame to process
    :returns: processed frame
    """
    if len(frame) > 0:
        if frame[0] == 240:
            return frame[1:].rstrip()
    return frame


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
