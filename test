#!/usr/bin/env python
import sys
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
import os
from glob import glob

HERE = os.path.dirname(os.path.abspath(__file__))

if len(sys.argv) == 1:
    libs = glob(os.path.join(HERE, 'externaltools', 'lib', '*.so'))
else:
    libs = sys.argv[1:]

for lib in libs:
    print "Loading %s..." % lib
    try:
        ROOT.gSystem.Load(lib)
    except Exception, e:
        print e
