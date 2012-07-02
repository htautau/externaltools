import os
import sys

base_flag = 'TOOLMAN_BASE'
if base_flag in os.environ:
    base_prefix = os.environ[base_flag]
else:
    # use parent directory
    base_prefix = os.path.abspath(
            os.path.join(
                os.path.dirname(
                    os.path.abspath(__file__)), os.path.pardir))

PACKAGE_DIR = 'packages'
BASE = os.path.join(base_prefix, PACKAGE_DIR)
PACKAGES = os.path.join(base_prefix, 'packages.txt')
SVNBASE = 'svn+ssh://{USER}@svn.cern.ch/reps/'

if not os.path.exists(BASE):
    os.mkdir(BASE)


class Package(object):

    def __init__(self, name, path):

        self.name = name
        self.path = path


def read_packages():

    for i, line in enumerate(open(PACKAGES).readlines()):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        try:
            yield Package(*line.split())
        except TypeError:
            print "line %i not understood: %s" % (i + 1, line)


def list_packages():

    paths = os.listdir(BASE)
    return paths
