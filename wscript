#!/usr/bin/env python

from glob import glob
import os
import sys
import shutil

from waflib import Build, Utils, TaskGen, Logs

import toolman
from toolman import rootcore


join = os.path.join

top = '.'
out = 'build'

init_template = """\
class ResourceNotFound(Exception):
    pass


LOADED_PACKAGES = {}
HERE = os.path.dirname(os.path.abspath(__file__))
NAME = 'common'


def register_loaded(bundle, package):

    if bundle not in LOADED_PACKAGES:
        LOADED_PACKAGES[bundle] = []
    
    # check if this library was already loaded in another non-common bundle
    for other_bundle, libs in LOADED_PACKAGES.items():
        if other_bundle in (bundle, NAME):
            continue
        if library in libs:
            raise RuntimeError(
                'Attempted to load the same package (%s) from two bundles' %
                package)
    if library not in LOADED_PACKAGES[bundle]:
        LOADED_PACKAGES[bundle].append(package)
        return False
    return True


def load_library(bundle, package, deps=None):
    
    # read the deps if not supplied
    if deps is None:
        deps = []
        if bundle == NAME:
            deps_file = open(os.path.join(HERE, package, 'deps'), 'r')
        else:
            deps_file = open(os.path.join(HERE, bundle, package, 'deps'), 'r')
        for dep in deps_file.readlines():
            deps.append(dep.strip().split())
        deps_file.close()

    # first recurse on dependencies
    for bundle, dep in deps:
        load_library(bundle, dep)
    if bundle == NAME:
        lib_path = os.path.join(HERE, 'lib', 'lib%s.so' % package)
    else:
        lib_path = os.path.join(HERE, bundle, 'lib', 'lib%s.so' % package)
    
    # ignore packages that didn't produce a library (headers only)
    if os.path.isfile(lib_path):
        if not register_loaded(bundle, package):
            ROOT.gSystem.Load(lib_path)
"""

bundle_init_template = """\
NAME = {bundle}
"""

package_init_template = """\
# this is generated code
import ROOT
import os
from {depth} import ResourceNotFound
from {depth} import load_library


HERE = os.path.dirname(os.path.abspath(__file__))
NAME = {package.name}
BUNDLE = {bundle}

# read dependencies
DEPS = []
deps_file = open(os.path.join(HERE, 'deps'), 'r')
for dep in deps_file.readlines():
    DEPS.append(dep.strip().split())
deps_file.close()

load_library(BUNDLE, NAME, DEPS)

RESOURCE_PATH = os.path.join(
    HERE, 'share') + os.path.sep


def get_resource(name=''):
    
    path = os.path.join(RESOURCE_PATH, name)
    if os.path.exists(path):
        return path
    raise ResourceNotFound('resource %s not found in package %s' %
        (name, __name__))
"""

setup_template = """\
# This generated script will work in either bash or zsh.

# deterine path to this script
# http://stackoverflow.com/questions/59895/can-a-bash-script-tell-what-directory-its-stored-in
EXTERNALTOOLS_SETUP="${BASH_SOURCE[0]:-$0}"

EXTERNALTOOLS_DIR="$( dirname "$EXTERNALTOOLS_SETUP" )"
while [ -h "$EXTERNALTOOLS_SETUP" ]
do 
  EXTERNALTOOLS_SETUP="$(readlink "$EXTERNALTOOLS_SETUP")"
  [[ $EXTERNALTOOLS_SETUP != /* ]] && EXTERNALTOOLS_SETUP="$EXTERNALTOOLS_DIR/$EXTERNALTOOLS_SETUP"
  EXTERNALTOOLS_SETUP="$( cd -P "$( dirname "$EXTERNALTOOLS_SETUP"  )" && pwd )"
done
EXTERNALTOOLS_DIR="$( cd -P "$( dirname "$EXTERNALTOOLS_SETUP" )" && pwd )"

echo "sourcing ${EXTERNALTOOLS_SETUP}..."
export PYTHONPATH=${EXTERNALTOOLS_DIR}${PYTHONPATH:+:$PYTHONPATH}
"""

os.environ['PREFIX'] = join(os.path.abspath(os.curdir), 'externaltools')


def options(opt):

    opt.load('compiler_cxx')


def configure(conf):
    
    conf.load('compiler_cxx')
    conf.env['CXXFLAGS'] = rootcore.root_cflags()[:]
    conf.env.append_value('CXXFLAGS', ['-DROOTCORE'])
    conf.env['LINKFLAGS'] = rootcore.root_linkerflags()[:]
    conf.env.append_value('LINKFLAGS', conf.env.CXXFLAGS)
    #conf.env['INCLUDES'] = rootcore.root_inc()[:]
    conf.find_program('root-config')
    conf.find_program('rootcint')


LIBRARY_DEPENDENCIES = {}


def build(bld):
            
    if bld.cmd == 'install':
        if os.path.exists(bld.options.prefix):
            print "%s already exists." % bld.options.prefix
            if (raw_input(
                "Its contents could be overwritten! Continue? Y/[n]: ")
                != 'Y'):
                return
        bld.add_post_fun(build_python_package)

    install_lib_path = join(bld.options.prefix, 'lib')
    #bld.post_mode = Build.POST_AT_ONCE
    bld.post_mode = Build.POST_LAZY
    #bld.post_mode = Build.POST_BOTH

    rootcint_cmd = (
        'rootcint -f ${TGT} -c -p ${CXXFLAGS} ${ROOTCINT_INCLUDES} ${SRC}; '
        'grep include ${SRC} > ${TGT}-tmp || true; '
        'cat ${TGT} >> ${TGT}-tmp; '
        'mv ${TGT}-tmp ${TGT}')
    partitioning = toolman.packages.get_partitioning()
    for bundle, packages in partitioning.items():
        
        if bundle not in LIBRARY_DEPENDENCIES:
            LIBRARY_DEPENDENCIES[bundle] = {}

        bld.env['PACKAGES_%s' % bundle] = packages
        
        bld.add_group('dicts_%s' % bundle)
        bld.add_group('libs_%s' % bundle)

        BUNDLE_PATH = join(toolman.packages.PACKAGE_DIR, bundle)

        for package in packages:
            name = package.name
            
            if name not in LIBRARY_DEPENDENCIES[bundle]:
                LIBRARY_DEPENDENCIES[bundle][name] = []
            
            PATH = join(BUNDLE_PATH, name)

            LIB_DEPENDS = []
            INCLUDES = []
            LINKFLAGS = []
            make = None
            if rootcore.is_rootcore(bundle, name):
                # parse Makefile.RootCore
                make = rootcore.read_makefile(
                        join(PATH, 'cmt', rootcore.MAKEFILE))
                SOURCES = bld.path.ant_glob(join(PATH, 'Root', '*.cxx'))
                HEADERS = bld.path.ant_glob(join(PATH, name, '*.h'))
                # check for dependencies on other packages
                if 'PACKAGE_DEP' in make:
                    DEPS = make['PACKAGE_DEP'].split()
                    for DEP in DEPS:
                        # search for DEP in this bundle
                        # and if not found look in common
                        found = False
                        dep_bundle = None
                        for other_package in packages:
                            if DEP == other_package.name:
                                found = True
                                dep_bundle = bundle
                        if not found and bundle != 'common':
                            # check in common
                            for other_package in partitioning['common']:
                                if DEP == other_package.name:
                                    found = True
                                    dep_bundle = 'common'
                        if not found:
                            sys.exit('Package %s depends on %s '
                                     'but it is not present' % (name, DEP))
                        INCLUDES.append(
                            join(toolman.packages.PACKAGE_DIR,
                                 dep_bundle, DEP))
                        LIB_DEPENDS.append((dep_bundle, DEP))
                        LIBRARY_DEPENDENCIES[bundle][name].append(
                                (dep_bundle, DEP))
            else:
                SOURCES = bld.path.ant_glob(join(PATH, 'src', '*.cxx'))
                if not SOURCES:
                    SOURCES = bld.path.ant_glob(join(PATH, '*.cxx'))
                HEADERS = bld.path.ant_glob(join(PATH, name, '*.h'))
                if not HEADERS:
                    HEADERS = bld.path.ant_glob(join(PATH, '*.h'))

            INCLUDES.append(PATH) 
            # possible improper includes in source files
            INCLUDES.append(join(PATH, name))
            
            DICT_SRC = None
            linkdef = rootcore.find_linkdef(PATH)
            if linkdef is not None:
                DICT = join(PATH, '%s_DICT' % name.upper())
                DICT_SRC = '%s.cxx' % DICT
                DICT_H = '%s.h' % DICT
                try:
                    HEADERS.remove(linkdef)
                except ValueError:
                    pass
                try:
                    HEADERS.remove(DICT_H)
                except ValueError:
                    pass
                try:
                    SOURCES.remove(DICT_SRC)
                except ValueError:
                    pass
                bld.set_group('dicts_%s' % bundle)
                rbld = bld(
                        rule=rootcint_cmd,
                        source=linkdef,
                        target=DICT_SRC)
                rbld.env.append_value('ROOTCINT_INCLUDES',
                        ' '.join(['-I../%s' % inc for inc in INCLUDES]))
                if make is not None:
                    rootcore.define_env(rbld.env, make)
            
            bld.set_group('libs_%s' % bundle)
            if bundle == 'common':
                install_path = '${PREFIX}/lib'
            else:
                install_path = '${PREFIX}/%s/lib' % bundle

            shlib = bld.shlib(
                    source=SOURCES,
                    dynamic_source=DICT_SRC,
                    target=name,
                    #use=LIB_DEPENDS,
                    install_path=install_path)
            
            if make is not None:
                rootcore.define_env(shlib.env, make)
            
            shlib.env.append_value('INCLUDES', INCLUDES)
            shlib.env.append_value('LINKFLAGS', LINKFLAGS)
            shlib.env.append_value('LINKFLAGS', shlib.env.CXXFLAGS)


def ignore_paths(dir, contents):
    
    # ignore hidden files/dirs
    return filter(lambda c: c.startswith('.'), contents)


def build_python_package(bld):

    # create main __init__.py
    init_file = open(join(bld.options.prefix, '__init__.py'), 'w')
    init_file.write(init_template)
    init_file.close()
    
    # create setup.sh
    setup_file = open(join(bld.options.prefix, 'setup.sh'), 'w')
    setup_file.write(setup_template)
    setup_file.close()
    
    partitioning = toolman.packages.get_partitioning()
    for bundle, packages in partitioning.items():
        
        if bundle == 'common':
            depth = '..'
            base_bundle = bld.options.prefix
        else:
            depth = '...'
            base_bundle = join(
                    bld.options.prefix, bundle)
            if not os.path.exists(base_bundle):
                os.mkdir(base_bundle)
        
            # create bundle __init__.py
            bundle_init = open(join(base_bundle, '__init__.py'), 'w')
            bundle_init.write(bundle_init_template.format(**locals()))
            bundle_init.close()

        for package in bld.env['PACKAGES_%s' % bundle]:
            LIBRARY = 'lib%s.so' % package
            base_package = join(base_bundle, package.name)
            if not os.path.exists(base_package):
                os.mkdir(base_package)
            
            # create package-level __init__.py
            package_init_file = open(join(base_package, '__init__.py'), 'w')
            package_init_file.write(package_init_template.format(**locals()))
            package_init_file.close()
            
            # write dependencies file
            dep_file = open(join(base_package, 'deps'), 'w')
            for dep_bundle, dep in LIBRARY_DEPENDENCIES[bundle][package.name]:
                dep_file.write('%s %s\n' % (dep_bundle, dep))
            dep_file.close()

            # copy data
            # check for either data/ or share/
            share_data = join(toolman.packages.PACKAGE_PATH, bundle, package.name, 'share')
            data_data = join(toolman.packages.PACKAGE_PATH, bundle, package.name, 'data')
            data = None
            if os.path.exists(share_data) and os.path.exists(data_data):
                Logs.error("Both share/ and data/ exist for package %s!" %
                        package)
            elif os.path.exists(share_data):
                data = share_data
            elif os.path.exists(data_data):
                data = data_data
            if data is not None:
                Logs.info("Copying data for package %s ..." % package)
                dest = join(base_package, 'share')
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.copytree(data, dest, ignore=ignore_paths)


# support for the "dynamic_source" attribute follows
@TaskGen.feature('cxx')
@TaskGen.before('process_source')
def dynamic_post(self):
    """
    bld(dynamic_source='*.cxx', ..) will search for source files to add
    to the attribute 'source' we could also call "eval" or whatever expression
    """
    if not getattr(self, 'dynamic_source', None):
        return
    self.source = Utils.to_list(self.source)
    src_nodes = self.path.get_bld().ant_glob(self.dynamic_source, quiet=True)
    self.source.extend(src_nodes)

    # if headers are created dynamically, assign signatures manually:
    #for x in self.path.get_bld().ant_glob('*.h'):
    #    x.sig = Utils.h_file(x.abspath())
    self.env.append_value('INCLUDES', [s.bld_dir() for s in src_nodes])
