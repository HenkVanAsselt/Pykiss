from .context import kiss

print(dir(kiss))
print()

def test_is_valid_kiss_frame():
    assert kiss.is_valid_kiss_frame(b'\xC0\x00\x54\x45\x53\x54\xC0') == True
    assert kiss.is_valid_kiss_frame(b'\xC0') == False
    assert kiss.is_valid_kiss_frame(b'\xC0\x00\x54\x45\x53\x54') == False

def test_kiss_decode():
    assert kiss.decode_dataframe(b'\xC0\x00TEST\xC0') == [b'\x00TEST']
    assert kiss.decode_dataframe(b'\xc0\x06TNC:FLDIGI 4.0.1\xc0\xc0\x06TRXS:RX\xc0') == [b'\x06TNC:FLDIGI 4.0.1', b'\x06TRXS:RX']
    assert kiss.decode_dataframe(b'\xc0\x06MODEM:BPSK31\xc0\xc0\x06MODEMBW:31\xc0\xc0\x06KISSCRCM:NONE,CCITT\xc0') == [b'\x06MODEM:BPSK31', b'\x06MODEMBW:31', b'\x06KISSCRCM:NONE,CCITT']

def test_kiss_encode():
    assert kiss.encode_dataframe(b'TEST') == b'\xc0\x00TEST\xc0'
    assert kiss.encode_dataframe(b"Hello", port=5) == b'\xc0\x50\x48\x65\x6C\x6C\x6F\xC0'   # Send the characters "Hello" out of TNC port 5
    assert kiss.encode_dataframe(b'\xC0\xDB') == b'\xC0\x00\xDB\xDC\xDB\xDD\xC0'

def test_decode_commands():
    assert kiss.decode_cmdbyte(0x00) == ('DATAFRAME', 0)
    assert kiss.decode_cmdbyte(0xFF) == ('RETURN', 0)
    assert kiss.decode_cmdbyte(0x34) == ('TXTAIL', 4)

def test_encode_command_and_port_to_byte():
    assert kiss.encode_command_and_port_to_byte(0, 0) == b'\x00'
    assert kiss.encode_command_and_port_to_byte(0, 6) == b'\x60'
    assert kiss.encode_command_and_port_to_byte(6, 0) == b'\x06'
    assert kiss.encode_command_and_port_to_byte(cmd=b'\x06', port=5) == b'\x56'
    assert kiss.encode_command_and_port_to_byte(20, 0) == b''
    assert kiss.encode_command_and_port_to_byte(1, 30) == b''
