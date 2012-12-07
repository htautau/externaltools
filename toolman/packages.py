import os
import sys
import re
import shutil
import subprocess
import operator


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
    package = os.path.basename(line)
    if package in REPO:
        # package with the same name from different repositories
        curr_package = REPO[package]
        del REPO[package]
        REPO[curr_package] = curr_package
        REPO[line] = line
    else:
        REPO[package] = line


class Package(object):

    @classmethod
    def from_string(cls, package, path=None):

        match = re.match(PACKAGE_PATTERN, package)
        if not match:
            raise ValueError("Not a valid package name: %s" % package)
        name = match.group('name')
        if path is not None:
            base_path = os.path.join(path, name)
        else:
            if name not in REPO:
                raise ValueError('package %s not found in any listed repositories' %
                        name)
            base_path = REPO[name]
        tag = None
        if match.group('tag'):
            path = os.path.normpath(os.path.join(base_path, 'tags', package))
            tag = match.group('tag')
        else: # assume trunk
            path = os.path.join(base_path, 'trunk')
        return Package(name=name, path=path, tag=tag)

    def __init__(self, name, path, tag=None):

        self.name = name
        self.path = path
        self.tag = tag
        if tag is not None:
            match = re.match(TAG_PATTERN, tag)
            if not match:
                raise ValueError("Tag %s not understood" % tag)
            self.version = map(int, match.groups(-1))
            if self.version[-1] == -1:
                self.version_str = '.'.join(map(str, self.version[:-1]))
            else:
                self.version_str = '.'.join(map(str, self.version))
            self.dot_versioned_name = '%s.%s' % (self.name, self.version_str)
        else:
            self.version = None
            self.version_str = None
            self.dot_versioned_name = self.name

    def __str__(self):

        return self.__repr__()

    def __repr__(self):

        return self.path

    def __hash__(self):

        return hash((self.name, self.tag, self.path))

    def __eq__(self, other):

        return (self.name == other.name and
                self.tag == other.tag and
                self.path == other.path)

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




def read_packages(bundle):

    print "Reading packages in bundle %s ..." % bundle
    for line in read_file(os.path.join(BUNDLES_DIR, '%s.lst' % bundle)):
        yield Package.from_string(*line.split())


def list_bundles():

    return [os.path.splitext(name)[0] for name in os.listdir(BUNDLES_DIR)
            if not name.startswith('.')]


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
    tags = [Package.from_string(tag) for tag in tags]
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


def get_partitioning():

    # determine packages in common between bundles
    # and for each package in the common packages that depends on a package that
    # isn't in common between the bundles (different tags), count that package
    # as being unique to each bundle. Repeat until no packages in the common
    # packages depends on a package in the bundle-specific package collections.
    # Return a dict mapping bundle names and 'common' (no bundle can be named
    # 'common') to packages.
    partitioning = {}
    for bundle in list_bundles():
        if bundle == 'common':
            raise NameError('A bundle has an illegal name: common')
        bundle_packages = set()
        for package in read_packages(bundle):
            for other_package in bundle_packages:
                # error if multiple packages with same name and possibly
                # different tags, so Package.__eq__ doesn't work here.
                if other_package.name == package.name:
                    raise NameError("Duplicate packages in bundle %s: %s %s" % (
                        bundle, package, other_package))
            bundle_packages.add(package)
        partitioning[bundle_to_name(bundle)] = bundle_packages
    # determine largest common subset of packages between bundles
    # this is the intersection of all sets
    common_packages = reduce(operator.__and__, partitioning.values())
    # remove packages from each bundle that are common
    for bundle, bundle_packages in partitioning.items():
        bundle_packages.difference_update(common_packages)
    partitioning['common'] = common_packages
    return partitioning


def fetch(user):

    svnbase = SVNBASE.format(**locals())
    partitioning = get_partitioning()
    for bundle, packages in partitioning.items():
        for package in packages:
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
