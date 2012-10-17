import os
import sys
import re
import shutil
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

PACKAGE_DIR = 'src'
BUNDLES_DIR = 'bundles'
PACKAGE_PATH = os.path.join(BASE_PREFIX, PACKAGE_DIR)
BUNDLES_PATH = os.path.join(BASE_PREFIX, BUNDLES_DIR)
REPOS_FILE = os.path.join(BASE_PREFIX, 'repo.lst')

SVNBASE = 'svn+ssh://{user}@svn.cern.ch/reps/'

if not os.path.exists(PACKAGE_PATH):
    os.mkdir(PACKAGE_PATH)


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
for line in read_file(REPOS_FILE):
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


def read_packages(bundle):

    print "Reading packages in bundle %s ..." % bundle
    for token in read_file(os.path.join(BUNDLES_DIR, '%s.lst' % bundle)):
        package = make_package(token)
        if package:
            yield package


def list_bundles():

    return [os.path.splitext(name)[0] for name in os.listdir(BUNDLES_DIR)]


def bundle_fetched(bundle):

    return os.path.isdir(os.path.join(PACKAGE_PATH, bundle))


def list_packages(bundle):

    return os.listdir(os.path.join(PACKAGE_PATH, bundle))


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


def show_repo():

    for name, path in REPO.items():
        print "%s => %s" % (name, path)


def show_used(bundle):

    for package in read_packages(bundle):
        print "%s => %s" % (package.name, package.path)


def show_tags(user, package):

    for tag in list_tags(user, package):
        print tag


def show_updates(user, bundle):

    for package in read_packages(bundle):
        if package.tag is not None:
            # only look for updates if we are not using the trunk
            tags = list_tags(user, package.name)
            tags.sort()
            if package not in tags:
                print "Package %s is not an available tag" % package
                continue
            newer_packages = tags[tags.index(package) + 1:]
            if newer_packages:
                if len(newer_packages) == 1:
                    print "A newer tag of package %s is available:" % (
                        package.name)
                else:
                    print "Newer tags of package %s are available:" % (
                        package.name)
                for p in newer_packages:
                    print p
                print "You are using %s" % package
                print


def fetch(bundle, user):

    svnbase = SVNBASE.format(**locals())

    for package in read_packages(bundle):
        url = os.path.join(svnbase, package.path)
        outpath = os.path.join(PACKAGE_PATH, bundle, package.name)
        print
        # update
        if os.path.exists(outpath):
            print "Updating %s..." % package.name
            print "This will remove and recreate %s" % outpath
            if raw_input("Continue? (Y/[n]) ") == 'Y':
                shutil.rmtree(outpath)
                print
            else:
                continue
        # checkout
        print "Checking out %s (%s) ..." % (package.name, package.path)
        if subprocess.call(['svn', 'co', url, outpath]):
            print "Failed to checkout %s!" % package.name


def bundle_to_name(bundle):

    # Replace invalid characters with '_' and convert to lower case
    return 'bundle_%s' % re.sub('[^0-9a-zA-Z_]', '_', bundle).lower()
