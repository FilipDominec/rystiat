# RYSTIAT - Run Your Simulations To Investigate A Trend

*"The purpose of computing is insight, not numbers" -- Richard Hamming (1915-1998)*

This program does not compute anything. It only runs a batch of simulations, defined by the path of the interpreter and the control script. 

## Installation

Requires working Python 3. Tested with nextnano3 on Linux, but *should* work with other simulations and *might* be adapted for other systems.

Complement this script with rystiat.rc, a text file containing 
* (optional) the path to the setup script before simulations (e.g. env variables setting)
* the path to the simulation interpreter, 
* the path to the actual simulation script,
* possibly the separating string between these. 
* (optional) the path to the pospro script before simulations (e.g. env variables setting)

## Usage 

Then you may run, e.g.,:

    ./rystiat.py height=234.56 width=-5e5 depth=10..25..5

And (if the given parameters are defined in your simulation script), the 
simulation directories will be generated:

    yourscript__height=234.56__width=-5e5__depth=10
    yourscript__height=234.56__width=-5e5__depth=15
    yourscript__height=234.56__width=-5e5__depth=20
    yourscript__height=234.56__width=-5e5__depth=25

Any processing of the simulation data is up to you; you can do this in the postprocessing script.
