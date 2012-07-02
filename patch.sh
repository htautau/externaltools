#!/bin/bash

if [ -d packages/JetUncertainties/ ]
then
    echo "patching JetUncertainties..."
    mv packages/JetUncertainties/analysisPlots packages/JetUncertainties/share/
    cp patches/JetUncertainties/*.config packages/JetUncertainties/share/
fi
echo "done"
