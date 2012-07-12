import os
import sys
import re
import subprocess


PACKAGE_PATTERN = re.compile('(?P<name>\w+)(?P<tag>(?:-\d{2}){3}(?:-\d{2})?)?')
TAG_PATTERN = re.compile('-(?P<major>\d{2})'
                         '-(?P<minor>\d{2})'
                         '-(?P<micro>\d{2})'
                         '(?:-(?P<branch>\d{2}))?')

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

    def __init__(self, name, path, tag=None):

        self.name = name
        self.path = path
        self.tag = tag
        if tag is not None:
            match = re.match(TAG_PATTERN, tag)
            if not match:
                raise ValueError("Tag %s not understood" % tag)
            self.version = map(int, match.groups(-1))
        else:
            self.version = None

    def __str__(self):

        return self.__repr__()

    def __repr__(self):

        if self.tag is not None:
            return self.name + self.tag
        else:
            return self.name

    def __cmp__(self, other):

        if self.name != other.name:
            raise ValueError("Cannot compare different packages %s and %s" %
                    (self.name, other.name))
        if self.tag is None and other.tag is None:
            # both are trunk
            return 0
        elif self.tag is None and other.tag is not None:
            # trunk wins
            return 1
        elif self.tag is not None and other.tag is None:
            # trunk wins
            return -1
        # compare tags
        return cmp(self.version, other.version)


def make_package(token):

    token = token.strip('/ ')
    match = re.match(PACKAGE_PATTERN, token)
    if not match:
        print "Not a valid package name: %s" % token
        return None
    name = match.group('name')
    if name not in REPO:
        print "Package %s not in repo.txt: %s" % name
        return None
    base_path = REPO[name]
    tag = None
    if match.group('tag'):
        path = os.path.join(base_path, 'tags', token)
        tag = match.group('tag')
    else: # assume trunk
        path = os.path.join(base_path, 'trunk')
    return Package(name=name, path=path, tag=tag)


def read_packages(filename=PACKAGES):

    for token in read_file(filename):
        package = make_package(token)
        if package:
            yield package


def list_packages():

    paths = os.listdir(BASE)
    return paths


def list_tags(user, package):

    if package not in REPO:
        sys.exit('Repository does not contain the package %s' % package)
    USER=user
    url = os.path.join(SVNBASE.format(**locals()),
                       REPO[package], 'tags')
    tags = subprocess.Popen(['svn', 'list', url],
            stdout=subprocess.PIPE).communicate()[0].strip().split()
    tags = [make_package(tag) for tag in tags]
    return tags
