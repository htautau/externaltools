#!/usr/bin/env python
from toolman import packages


for bundle in packages.list_bundles():

    if not packages.bundle_fetched(bundle):
        continue

    print "Testing bundle %s ..." % bundle

    for package in packages.list_packages(bundle):

        print "Testing package %s ..." % package
        exec('from externaltools.%s import %s' % (
            packages.bundle_to_name(bundle), package))
