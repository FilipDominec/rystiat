#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os
for root, dirs, files in os.walk(".", topdown=False):
    for name in files:
        fullname = os.path.join(root, name)
        try:
            if fullname[-4:] == '.dat':
                with open(fullname[:-4]+'.plt') as f: 
                    lines = f.readlines()
                    lines[0:3] = []
                    lines[0] = lines[0].replace(' ', '')
                    lines[2:6] = []
                    if len(lines) > 2:  ## the file is probably multicolumn -> use line labels instead of y-unit
                        lines[1:2] = []
                    header = '#' + '\t'.join([l.strip() for l in lines])
                with open(fullname, 'r') as original: data = original.read()
                with open(fullname, 'w') as modified: modified.write(header + '\n' + data)
        except:
            print('could not find', fullname)
