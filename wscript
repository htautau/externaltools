#!/usr/bin/env python

from glob import glob
import os
import sys
import shutil

from toolman import packages
from toolman import rootcore

from waflib import Build, Utils, TaskGen, Logs

join = os.path.join

top = '.'
out = 'build'

init_template = """
# this is generated code
import os
import ROOT
ROOT.gSystem.Load('{LIBRARY}')
HERE = os.path.dirname(os.path.abspath(__file__))

def get_resource(name=''):
    
    path = os.path.join(HERE, 'share', name)
    if os.path.exists(path):
        return path
    return None
"""

setup_template = """
#!/bin/bash
# this is a generated script

# deterine path to this script here so that this
# package is relocatable
# http://stackoverflow.com/questions/59895/can-a-bash-script-tell-what-directory-its-stored-in
EXTERNALTOOLS_SOURCE="${BASH_SOURCE[0]}"
while [ -h "$EXTERNALTOOLS_SOURCE" ] ; do EXTERNALTOOLS_SOURCE="$(readlink "$EXTERNALTOOLS_SOURCE")"; done
EXTERNALTOOLS="$( cd -P "$( dirname "$EXTERNALTOOLS_SOURCE" )" && pwd )"
EXTERNALTOOLS_DIR="$(dirname "$EXTERNALTOOLS")"
echo "sourcing ${EXTERNALTOOLS_SOURCE}..."

export PYTHONPATH=${EXTERNALTOOLS_DIR}${PYTHONPATH:+:$PYTHONPATH}
export LD_LIBRARY_PATH=${EXTERNALTOOLS}/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
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


def build(bld):
            
    if bld.cmd == 'install':
        if os.path.exists(bld.options.prefix):
            print "%s already exists." % bld.options.prefix
            if raw_input("Its contents could be overwritten! Continue? Y/[n]: ") != 'Y':
                return
        bld.add_post_fun(build_python_package)

    install_lib_path = join(bld.options.prefix, 'lib')
    bld.post_mode = Build.POST_AT_ONCE
    #bld.post_mode = Build.POST_LAZY
    #bld.post_mode = Build.POST_BOTH

    bld.add_group('dicts')
    bld.add_group('libs')
    
    rootcint_cmd = (
        'rootcint -f ${TGT} -c -p ${CXXFLAGS} ${ROOTCINT_INCLUDES} ${SRC}; '
        'grep include ${SRC} > ${TGT}-tmp || true; '
        'cat ${TGT} >> ${TGT}-tmp; '
        'mv ${TGT}-tmp ${TGT}')

    package_names = packages.list_packages()
    bld.env['PACKAGES'] = package_names

    for name in package_names:
        
        PATH = join(packages.PACKAGE_DIR, name)

        LIB_DEPENDS = []
        INCLUDES = []
        LINKFLAGS = []
        make = None
        if rootcore.is_rootcore(name):
            # parse Makefile.RootCore
            make = rootcore.read_makefile(
                    join(PATH, 'cmt', rootcore.MAKEFILE))
            SOURCES = bld.path.ant_glob(join(PATH, 'Root', '*.cxx'))
            HEADERS = bld.path.ant_glob(join(PATH, name, '*.h'))

            # check for dependencies on other packages
            if 'PACKAGE_DEP' in make:
                DEPS = make['PACKAGE_DEP'].split()
                #LINKFLAGS.append('-Lexternaltools/lib')
                for DEP in DEPS:
                    if DEP not in package_names:
                        sys.exit('Package %s depends on %s but it is not present' %
                                 (name, DEP))
                    INCLUDES.append(join(packages.PACKAGE_DIR, DEP))
                    LIB_DEPENDS.append(DEP)
                    #LINKFLAGS.append('-l%s' % DEP)
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
            bld.set_group('dicts')
            rbld = bld(
                rule=rootcint_cmd,
                source=linkdef,
                target=DICT_SRC
            )
            rbld.env.append_value('ROOTCINT_INCLUDES',
                                  ' '.join(['-I../%s' % inc for inc in INCLUDES]))
            if make is not None:
                rootcore.define_env(rbld.env, make)
        
        bld.set_group('libs')
        shlib = bld.shlib(source=SOURCES,
                          dynamic_source=DICT_SRC,
                          target=name,
                          use=LIB_DEPENDS,
                          install_path='${PREFIX}/lib')#install_lib_path)
        
        if make is not None:
            rootcore.define_env(shlib.env, make)
        
        shlib.env.append_value('INCLUDES', INCLUDES)
        shlib.env.append_value('LINKFLAGS', LINKFLAGS)
        shlib.env.append_value('LINKFLAGS', shlib.env.CXXFLAGS)


def ignore_paths(dir, contents):
    
    # ignore hidden files/dirs
    return filter(lambda c: c.startswith('.'), contents)


def build_python_package(bld):

    # create __init__.py
    open(join(bld.options.prefix, '__init__.py'), 'w').close()
    # create setup.sh
    setup_file = open(join(bld.options.prefix, 'setup.sh'), 'w')
    setup_file.write(setup_template)
    setup_file.close()
    for package in bld.env.PACKAGES:
        LIBRARY = 'lib%s.so' % package
        base = join(bld.options.prefix, package)
        if not os.path.exists(base):
            os.mkdir(base)
        # create __init__.py
        init_file = open(join(base, '__init__.py'), 'w')
        init_file.write(init_template.format(**locals()))
        init_file.close()
        # copy data
        share_data = join(top, package, 'share')
        if os.path.exists(share_data):
            Logs.info("Copying share data for package %s..." % package)
            dest = join(base, 'share')
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(share_data, dest, ignore=ignore_paths)


# support for the "dynamic_source" attribute follows
@TaskGen.feature('cxx')
@TaskGen.before('process_source')
def dynamic_post(self):
    """
    bld(dynamic_source='*.cxx', ..) will search for source files to add to the attribute 'source'
    we could also call "eval" or whatever expression
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
