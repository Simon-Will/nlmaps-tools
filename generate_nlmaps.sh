#!/usr/bin/env bash

set -e

SUFFIX="$1"
V2_DIR="$2"
AREAS="$3"
POIS="$4"

if [ "$#" != 4 ]; then
    echo 'Usage Example:'
    echo 'generate_nlmaps.sh beta nlmaps_v2/split_1_train_dev_test areas.txt pois.txt'
    exit 1
fi

V3_DIR="nlmaps_v3$SUFFIX"
if [ -d "$V3_DIR" ]; then
    echo "Directory $V3_DIR already exists."
    exit 2
fi

generate() {
    local out_prefix="$1"
    local count="$2"
    local noise="$3"
    echo "Generating $out_prefix ($count instances)"
    if [ "$noise" = noise ]; then
        python -m nlmaps_tools.generate_nl --noise --count "$count" \
               -o "$out_prefix" "$AREAS" "$POIS"
    else
        python -m nlmaps_tools.generate_nl --count "$count" \
               -o "$out_prefix" "$AREAS" "$POIS"
    fi
}

declare -A LENGTHS
for split in train dev test; do
    LENGTHS["$split"]=$(wc -l <"$V2_DIR/nlmaps.v2.$split.mrl")
done

mkdir -p "$V3_DIR/v3$SUFFIX.normal"
generate "$V3_DIR/v3$SUFFIX.normal/nlmaps.v3$SUFFIX.train" "$((2 * "${LENGTHS[train]}"))"
generate "$V3_DIR/v3$SUFFIX.normal/nlmaps.v3$SUFFIX.dev" "$((2 * "${LENGTHS[dev]}"))"
generate "$V3_DIR/v3$SUFFIX.normal/nlmaps.v3$SUFFIX.test" "$((2 * "${LENGTHS[test]}"))"

mkdir -p "$V3_DIR/v3$SUFFIX.noise"
generate "$V3_DIR/v3$SUFFIX.noise/nlmaps.v3$SUFFIX.train" "$((2 * "${LENGTHS[train]}"))" noise
generate "$V3_DIR/v3$SUFFIX.noise/nlmaps.v3$SUFFIX.dev" "$((2 * "${LENGTHS[dev]}"))" noise
generate "$V3_DIR/v3$SUFFIX.noise/nlmaps.v3$SUFFIX.test" "$((2 * "${LENGTHS[test]}"))" noise

for type in normal noise; do
    mkdir -p "$V3_DIR/v3$SUFFIX.$type.plusv2"
    for split in train dev test; do
        for ext in en mrl; do
            merged="$V3_DIR/v3$SUFFIX.$type.plusv2/nlmaps.v3$SUFFIX.$split.$ext"
            echo "Merging new and old $split into $merged"
            cat "$V2_DIR/nlmaps.v2.$split.$ext" \
                <(head -n "${LENGTHS["$split"]}" "$V3_DIR/v3$SUFFIX.$type/nlmaps.v3$SUFFIX.$split.$ext") \
                >"$merged"
        done
    done
done
