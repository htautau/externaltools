import os
import sys
import re


PACKAGE_PATTERN = re.compile('(?P<name>\w+)(?P<tag>(?:-\d{2}){3})?')


BASE_FLAG = 'TOOLMAN_BASE'
if BASE_FLAG in os.environ:
    BASE_PREFIX = os.environ[BASE_FLAG]
else:
    # use parent directory
    BASE_PREFIX = os.path.abspath(
            os.path.join(
                os.path.dirname(
                    os.path.abspath(__file__)), os.path.pardir))

PACKAGE_DIR = 'packages'
BASE = os.path.join(BASE_PREFIX, PACKAGE_DIR)
REPOS = os.path.join(BASE_PREFIX, 'repo.txt')
PACKAGES = os.path.join(BASE_PREFIX, 'packages.txt')
SVNBASE = 'svn+ssh://{USER}@svn.cern.ch/reps/'

if not os.path.exists(BASE):
    os.mkdir(BASE)


def read_file(name):

    for i, line in enumerate(open(name).readlines()):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        try:
            yield line
        except:
            print "line %i not understood: %s" % (i + 1, line)

REPO = {}
for line in read_file(REPOS):
    REPO[os.path.basename(line)] = line


class Package(object):

    def __init__(self, name, path):

        self.name = name
        self.path = path


def read_packages(filename=PACKAGES):

    for package in read_file(filename):
        match = re.match(PACKAGE_PATTERN, package)
        if not match:
            print "Not a valid package name: %s" % name
            continue
        name = match.group('name')
        if name not in REPO:
            print "Package %s not in repo.txt: %s" % name
            continue
        base_path = REPO[name]
        if match.group('tag'):
            path = os.path.join(base_path, 'tags', package)
        else: # assume trunk
            path = os.path.join(base_path, 'trunk')
        yield Package(name=name, path=path)


def list_packages():

    paths = os.listdir(BASE)
    return paths
