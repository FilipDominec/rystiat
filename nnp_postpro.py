#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
Nextnano stores the numeric data in *.dat file, and the corresponding descirptive 
header in a *.plt file. This script recursively adds the header to the data file, so that
it can be easily loaded by usual ascii processing programs. 

Also, it flattens the recursive directory structure if called with --flatten parameter.
"""


import os, sys, shutil
from pathlib import Path

print('nnp_postpro running recursively in directory', os.getcwd())

#pathlib.Path.glob() recursively searches for files.
#allpy = pathlib.Path('~').expanduser().glob('*.py')  
for fullpath in Path.cwd().rglob('*.dat'):
    try:
        with open(fullpath.with_suffix('.plt')) as f: 
            lines = f.readlines()
            lines[0:3] = []
            lines[0] = lines[0].replace(' ', '')
            lines[2:6] = []
            if len(lines) > 2:  ## the file is probably multicolumn -> use line labels instead of y-unit
                lines[1:2] = []
            header = '#' + '\t'.join([l.strip() for l in lines])
        Path.unlink(Path(fullpath.with_suffix('.plt')))
        with open(fullpath, 'r') as original: data = original.read()
        with open(fullpath, 'w') as modified: modified.write(header + '\n' + data)
    except IOError:
        pass

for name in Path('output').glob('*'):
    if name.is_dir():
        toname = Path(*[part for part in Path(name).parts if 'output' not in str(part)]) # filter out 'output' from dir path
        shutil.move(name, toname)

