#!/usr/bin/env bash

find . -name '*.mrl' |
    while read -r mrlfile; do
        linfile="${mrlfile%mrl}lin"
        echo "$mrlfile -> $linfile"
        python -m nlmaps_tools.mrl.linearise -i "$mrlfile" -o "$linfile"
    done
