from .context import kiss

import os


def test_kiss_file():
    # print(f"\nCurrent folder = {os.getcwd()}")
    frames = kiss.util.read_kissframes_from_file('tests/kissframes_testfile.txt')
    for frame in frames:
        print(f"{frame=}")
        data = kiss.decode_dataframe(frame)
        print(f"{data=}")




