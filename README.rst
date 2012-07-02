.. -*- mode: rst -*-

About
=====

"externaltools" is a package for easily checking out and building all of the
"external" tools we use (MissingMassCalculator, PileupReweighting,
TauTriggerCorrections, etc.)

The file "packages.txt" contains a list of the packages and the format of each
line is as follows::

   [package name] [path to package (trunk, or a specific tag or branch) in svn]

Please add any additional packages.


Getting and Building the External Tools
=======================================

To checkout all packages (you will be prompted for your CERN username)::

   ./fetch

and to build and install all packages (in ./externaltools/lib)::

   ./waf configure build install

to clean::

   ./waf clean


Testing the Built Packages
==========================

To make sure that all packages are built properly and that there are no linking
errors::

   source externaltools/setup.sh
   ./test_libs.py

You should see no errors.
