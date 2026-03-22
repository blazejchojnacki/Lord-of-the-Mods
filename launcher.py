"""
Core of the 'Lord of the Mods.exe' to launch the application composed of the modules under /source/
Alternatively, the modules can be tested via trials.py
"""

import os
import sys

from source.initiator import initiate
import source.interface

if __name__ == "__main__":
    if os.path.abspath('./') != '\\'.join(sys.argv[0].split('\\')[0:-1]):
        start_file = sys.argv[1]
        os.chdir('\\'.join(sys.argv[0].split('\\')[0:-1]))
    else:
        start_file = None
    initiate()
    main_window = source.interface.Window(start_file)
