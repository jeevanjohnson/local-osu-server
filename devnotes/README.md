# Purpose

This directory contains personal notes I have taken while working on this project.

# 3.16.2026
- Fix GUI now since we know when the client is opened or not
- Begin tackling leaderboards and score_submission
- - Support lazer scores being seen on lbs but nots its replys
- - Have personal tags `[rxonly] cover` and then server tags `cover (1.2x Rate)`, server tags can allow us for when we rate change on a map we can see the og leaderboard map and everyone's rate but now we can see our rate in terms of speed and do score multiplying accordingly
- GUI profile specific settings
- rank button click for gui
- recently loaded score on gui
- when storing scores, store the osu file in case if stuff gets lost, we can still figure out a way to load replay

## 3.15.2026

`field(init=False)` excludes the field from being included in the generated `__init__` method of a dataclass.

`IntFlag` allows multiple members to be combined using the OR bitwise operation `|`. This is useful for representing a combination of options or flags. 

`|=` regarding binary operations is the bitwise OR operator. It compares each bit position and keeps a 1 if either of the bits is 1. For example, if you have the binary numbers 1101 and 1011, the bitwise OR would be 1111 because at least one of the bits in each position is 1. In context of uleb128, when we set the most significant bit to 1, so we use this operator to set that bit to 1 while keeping the other bits unchanged.

`&` regarding binary operations is the bitwise AND operator. It compares each bit position and only keeps a 1 where both bits are 1. For example, if you have the binary numbers 1101 and 1011, the bitwise AND would be 1001 because only the first and last bits are both 1. In context of uleb

For writing uleb128:
- You are given a number that you want to encode as uleb128.
```
While number > 0:
    Take the 7 least significant bits of the number.
        Ex. 12345678, the 7 least significant bits of this are 8,7,6,5,4,3,2,1.
    Check if the most significant bit (the first bit) is = 1.

    If equals 1:
        This means there are more bytes to read, so we set the most significant bit to 1 and write this byte to the output.
    If equals 0:
        This means this is the last byte and we are done encoding.
```

`int 32` is just an int that is 4 bytes long. It can represent values from -2,147,483,648 to 2,147,483,647. 

`int 64` is an int that is 8 bytes long. It can represent values from -9,223,372,036,854,775,808 to 9,223,372,036,854,775,807.

`unsigned int` can't hold negative values. While a `signed int` can.

`bytes(size: int)` creates a byte object of the specified size filled with null bytes (0x00).

`enum.unique` checks if there are any members sharing the same value. If so, an error is raised.

osu! Packet writing Protocol (little endian):
- Packet ID (unsigned short, 2 bytes)
- Packet Length (padding, 1 byte)
- Packet Data Length (unsigned int, 4 bytes)
- Packet Data (variable length)

Endian refers to the order of bytes in a data type (like ints or floats). For little-endian, the least significant byte is stored first. The "least significant byte" is the byte that represents the smallest part of the number. For example, 1234, the least significant number is 4. So in terms of bytes, the least significant byte would be the one that represents the 4. In little-endian, this byte would be stored first in memory in little-endian format. Then 3, Then 2, and then 1. So the bytes would be stored in the order of 4, 3, 2, 1.

## 3.14.2026

`multiprocess.Process(..., daemon=bool)` If this is set to `True`, the process will be killed the moment the main process (the script running the processes) exits. If this is set to `False`, the main process will wait for them to finish before exiting.
  
`finally` block act as a cleanup mechanism. You can think about as you try to do something, if an error occurs, you can catch it and handle it, but regardless of whether an error occurs or not, the code in the `finally` block will always execute.

`pip freeze > requirements.txt` to update the dependencies in the `requirements.txt` file.
- Ensure you are in the correct virtual environment before running this command to capture all the necessary dependencies for your project.

`mitmdump -s mitm_script.py` to start the mitmproxy with the specified script.
- This command will run mitmproxy and execute the `mitm_script.py` script,
- `-q` flag is used to suppress the output of mitmproxy, making it "quieter" while running.

`#!/usr/bin/env python` at the top of a Python script is called a shebang line. It tells the operating system how to execute the script.
- `#!/usr/bin/env python` uses the `env` command to find the Python interpreter