#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
RYSTIAT - Run Your Simulations To Investigate A Trend

"The purpose of computing is insight, not numbers" -- Richard Hamming (1915-1998)

Complement this script with rystiat.rc, a text file containing 
* (optional) the path to the setup script before simulations (e.g. env variables setting)
* the path to the simulation interpreter, 
* the path to the actual simulation script,
* possibly the separating string between these. 

Then you may run, e.g.,:

    ./rystiat.py height=234.56 width=-5e5 depth=10..25..5

And (if the given parameters are defined in your simulation script), the 
simulation directories will be generated:

    yourscript__height=234.56__width=-5e5__depth=10
    yourscript__height=234.56__width=-5e5__depth=15
    yourscript__height=234.56__width=-5e5__depth=20
    yourscript__height=234.56__width=-5e5__depth=25

"""

## Import common moduli
import os, sys, shutil, datetime, subprocess, time
import numpy as np

from scipy.constants import c, hbar, pi


CB = '\033[94m'
CG = '\033[92m'
CR = '\033[91m'
CP = '\033[95m'
CW = '\033[97m'
C0 = '\033[0m'

def highlight(s, keyws):
    for keyw in keyws:
        s = s.replace(keyw, CR+keyw+C0)
        s = s.replace(keyw.lower(), CR+keyw.lower()+C0)
        s = s.replace(keyw.upper(), CR+keyw.upper()+C0)
    return s
def Popen_nice_print(command_list, enc, color, **params):
    process = subprocess.Popen(command_list, **params, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) # , shell=True
    linenumber = 0
    t0 = time.time()
    while True:
        output = process.stdout.readline()
        if output == b'' and process.poll() is not None:
            break
        if output:
            print('{:06.3f} {:}{:04}:{:} {:}'.format(time.time()-t0, color, linenumber, C0, 
                highlight(output.decode(enc).strip(), ('Error', 'Warning', 'Failed'))))
        linenumber += 1
    if process.returncode:          # or process.poll()?
        print(CR+'rystiat warning:'+C0+' External command ended with return code {:}, check the printout or the log file'.format(process.returncode))
    return process.returncode


## Load the settings
def search_file_in_updirs(filename):
    cwd = os.getcwd()
    parsedlines = {}
    while cwd != '/':
        try:
            checkfile = os.path.join(cwd, filename)
            with open(checkfile) as openfile:
                print(CW+'rystiat: run control file found: ', C0, checkfile)
                for rl in openfile.readlines():
                    if rl.strip() and rl[0] != '#':
                        if rl[0] not in (' ', '\t'):   ## whitespace on line beginning = extend multiline 
                            key, val = [s.strip() for s in rl.split('=', 1)]
                            parsedlines[key] = val
                        else:  ## will turn the output to a list, and append to the existing value
                            val = rl.strip()
                            try:
                                parsedlines[key].append(val)
                            except:
                                parsedlines[key] = [parsedlines[key], val]
                return parsedlines
        except FileNotFoundError:
            cwd = os.path.split(cwd)[0]
    print('rystiat error: could not find the file `{:}` in the directory `{:}` nor its up-dirs'.format(filename, os.getcwd()))
rystiatrc = search_file_in_updirs('rystiat.rc')

## Automatic numbering of simulation runs
def read_and_increment_counter(counterfile='./rystiat-counter'):
    try:    
        with open(counterfile) as openfile: counter = int(openfile.read())
    except: 
        counter = 0
    with open(counterfile, 'w') as openfile: openfile.write(str(counter + 1))
    return counter
counter = read_and_increment_counter()

## Parse the command-line parameters
def parse_param(paramstr):
    totalrange = []
    for rangestr in paramstr.split(','):
        splitted = rangestr.split('..')                     # if it is a (multi)range in format from..to..step,from..to..step, etc.
        if len(splitted) > 2:
            pfrom, pto, pstep = [float(s) for s in splitted]
            totalrange += list(np.arange(pfrom, pto+pstep/2, pstep))
        elif len(splitted) == 1:
            try:
                totalrange.append(float(splitted[0]))       # if it is a number
            except ValueError:
                totalrange.append(splitted[0].strip())      # if it is a string
    return totalrange

staticparam = {}
scannedparam_name, scannedparam_vals = None, None
for arg in sys.argv[1:]:
    argname, argvalraw = arg.split('=')
    argval = parse_param(argvalraw)
    if len(argval) > 1:
        if not scannedparam_name:
            scannedparam_name, scannedparam_vals = argname, argval
        else:
            print(CW+'rystiat warning: Already set up a 1-D scan over the `{:}{:}` parameter, cannot run a 2-D scan also over `{:}`'.format(
                rystiatrc['varprefix'], scannedparam_name, argname)+C0)
            print(CW+'               I will thus set {:}{:}={:.6} as a static parameter.'.format(rystiatrc['varprefix'], argname, argval[0])+C0)
            staticparam[argname] = argval[0]
    else:
        staticparam[argname] = argval[0]

## Generate new directory and backup the original script there
simulationid = '{:03d}__{:.40}'.format(counter, os.path.split(rystiatrc['scriptname'])[1])
for k,v in staticparam.items(): 
    try:
        simulationid += '__{:}={:.6g}'.format(k,v)
    except ValueError:
        simulationid += '__{:}={:}'.format(k,v)
if scannedparam_name: 
    simulationid += '__{:}Scan'.format(scannedparam_name)
batchdir = os.path.join(os.getcwd(), simulationid)

## Backup the original script and also the calling command in the root directory of the whole batch
os.makedirs(batchdir, exist_ok=True)
with open('rystiat_last_batch_dir.txt', 'w') as outputfile: outputfile.write(batchdir+'\n')
with open(os.path.join(batchdir, 'rystiat_command_line.txt'), 'w') as outputfile: outputfile.write(' '.join(sys.argv)+'\n')
shutil.copy(rystiatrc['scriptname'], os.path.join(batchdir, os.path.split(rystiatrc['scriptname'])[1]+'__original_bkup'))

## Enable running a single simulation (without parametric scan)
if not scannedparam_vals: scannedparam_vals = [None]


## Preprocessing command
my_env = os.environ.copy()

def flatten(x): # in risk of passing a non-list, enclose it in brackets!
    """ Flattens a nested list, or a tuple. 
    Makes a list containing a string from a nonempty string, c.f. what list() normally does! 
    The some for other (non-compound) data types. Skips empty strings.
    """
    result = []
    for el in x:
        if type(el) in (list,tuple):
            result.extend(flatten(el))
        elif el!='':
            result.append(el)
    return result

for cmd in flatten([rystiatrc['preprocess']]): 
    print(CG+'rystiat info: calling the preprocessing command now...'+cmd+C0)
    Popen_nice_print(cmd.split(), 'utf-8', CG, cwd=batchdir, env=my_env)

## Main loop - for each scanned parameter generate a new script with updated parameters 
try:
    enc = 'utf-8'
    with open(rystiatrc['scriptname'], 'r', encoding=enc) as inputfile: 
        inputlines = inputfile.readlines()
except UnicodeDecodeError:      # one can never 100% determine encoding, but this often helps 
    enc = 'cp1252'
    with open(rystiatrc['scriptname'], 'r', encoding=enc) as inputfile: 
        inputlines = inputfile.readlines()


for scannedparam_currentval in scannedparam_vals:
    unused_staticparam = list(staticparam.keys())
    unused_scannedparam = True

    ## Generate a descriptive name for the script to be written
    if scannedparam_currentval is not None:
        barename, ext = rystiatrc['scriptname'].rsplit('.')
        try:        ## FIXMe
            newscriptname = os.path.join(batchdir, '{:}__{:}={:.6g}.{:}'.format(barename, scannedparam_name, scannedparam_currentval, ext))
        except ValueError:
            newscriptname = os.path.join(batchdir, '{:}__{:}={:}.{:}'.format(barename, scannedparam_name, scannedparam_currentval, ext))
    else: newscriptname = os.path.join(batchdir, rystiatrc['scriptname'])

    ## Parse and write the new updated script 
    with open(newscriptname, 'w') as outputfile:
        for l in inputlines:
            if scannedparam_name and rystiatrc['varprefix']+scannedparam_name+'=' in l.replace(' ', ''):  # (todo) should better search for whole word
                unused_scannedparam = False
                try: 
                    l = '{:}{:}={:.6g}\n'.format(rystiatrc['varprefix'], scannedparam_name, scannedparam_currentval)
                except:
                    print(CW+'rystiat warning: could not parse the scanned parameter `{:}{:}` value as a number, assuming it is a text parameter'.format(
                            rystiatrc['varprefix'], scannedparam_name)+C0)
                    print(CW+'warning: could not format parameter value as a number'+C0)
                    l = '{:}{:}={:}\n'.format(rystiatrc['varprefix'], scannedparam_name, scannedparam_currentval)
            for k,v in staticparam.items():
                if rystiatrc['varprefix']+k+'=' in l.replace(' ', ''):  # (todo) should better search for whole word
                    unused_staticparam.remove(k)
                    l = '{:}{:}={:}\n'.format(rystiatrc['varprefix'], k, v)
                    break
            outputfile.write(l)

    ## Check if all user-given parameters were used
    if unused_staticparam:
        if len(unused_staticparam)>1:
            print(CR+'rystiat error:'+CW+' The static parameters {:}{:} were not found to be defined anywhere in the source file {:}'.format(
                rystiatrc['varprefix'], unused_staticparam, rystiatrc['scriptname'])+C0)
        else:
            print(CR+'rystiat error:'+CW+' The static parameter {:}{:} was not found to be defined anywhere in the source file {:}'.format(
                rystiatrc['varprefix'], unused_staticparam, rystiatrc['scriptname'])+C0)
        break
    if unused_scannedparam and scannedparam_currentval is not None:
        print(CR+'rystiat error:'+CW+' The parameter to be scanned {:}{:} was not found to be defined anywhere in the source file {:}'.format(
            rystiatrc['varprefix'], scannedparam_name, rystiatrc['scriptname'])+C0)
        break

    ## Run the simulation!

    #from datetime import datetime;  ''.format(datetime.datetime())
    #my_env['NEXTNANO'] = '/home/dominecf/bin/nextnano/2017_01_19/'
    print(CB+'rystiat info: it is {:}, running the next simulation: {:}'.format(datetime.datetime.now(), CP+os.path.split(newscriptname)[1])+C0)
    #callresult = subprocess.check_output([rystiatrc['interpreter'], rystiatrc['separator'], newscriptname, rystiatrc['staticparams']],
            #cwd=os.path.split(newscriptname)[0], env=my_env)
    Popen_nice_print(flatten([rystiatrc['interpreter'], newscriptname, rystiatrc['staticparams']]), enc, CB,
            cwd=os.path.split(newscriptname)[0], env=my_env)

newdirparam = ''
newdirscan = ''

for cmd in flatten([rystiatrc['postprocess']]): 
    print(CG+'rystiat info: calling the postprocessing command now...'+cmd+C0)
    Popen_nice_print(cmd.split(), 'utf-8', CG, cwd=batchdir, env=my_env)

"""
programmer's notes 

"""
