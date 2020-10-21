#!/usr/bin/env bash

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
    if [ "$noise" = noise ]; then
        python -m nlmaps_tools.generate_nl --noise --count "$count" \
               -o "$out_prefix" "$AREAS" "$POIS"
    else
        python -m nlmaps_tools.generate_nl --count "$count" \
               -o "$out_prefix" "$AREAS" "$POIS"
    fi
}

mkdir -p "$V3_DIR/v3$SUFFIX.normal"
generate "$V3_DIR/v3$SUFFIX.normal/nlmaps.v3$SUFFIX.train" 50000
generate "$V3_DIR/v3$SUFFIX.normal/nlmaps.v3$SUFFIX.dev" 2000
generate "$V3_DIR/v3$SUFFIX.normal/nlmaps.v3$SUFFIX.test" 20000

mkdir -p "$V3_DIR/v3$SUFFIX.noise"
generate "$V3_DIR/v3$SUFFIX.noise/nlmaps.v3$SUFFIX.train" 50000 noise
generate "$V3_DIR/v3$SUFFIX.noise/nlmaps.v3$SUFFIX.dev" 2000 noise
generate "$V3_DIR/v3$SUFFIX.noise/nlmaps.v3$SUFFIX.test" 20000 noise

mkdir -p "$V3_DIR/v3$SUFFIX.normal.plusv2"
TRAIN_LEN=$(wc -l "$V2_DIR/nlmaps.v2.train.mrl")
DEV_LEN=$(wc -l "$V2_DIR/nlmaps.v2.dev.mrl")
TEST_LEN=$(wc -l "$V2_DIR/nlmaps.v2.test.mrl")
cat "$V2_DIR/nlmaps.v2.train.mrl" \
    <(sed "$((TRAIN_LEN + 1))"',$d' "$V3_DIR/v3$SUFFIX.normal/nlmaps.v3$SUFFIX.train.mrl") \
    >"$V3_DIR/v3$SUFFIX.normal.plusv2.train.mrl"
cat "$V2_DIR/nlmaps.v2.dev.mrl" \
    <(sed "$((DEV_LEN + 1))"',$d' "$V3_DIR/v3$SUFFIX.normal/nlmaps.v3$SUFFIX.dev.mrl") \
    >"$V3_DIR/v3$SUFFIX.normal.plusv2.dev.mrl"
cat "$V2_DIR/nlmaps.v2.dev.mrl" \
    <(sed "$((DEV_LEN + 1))"',$d' "$V3_DIR/v3$SUFFIX.normal/nlmaps.v3$SUFFIX.dev.mrl") \
    >"$V3_DIR/v3$SUFFIX.normal.plusv2.dev.mrl"

mkdir -p "$V3_DIR/v3$SUFFIX.noise.plusv2"
TRAIN_LEN=$(wc -l "$V2_DIR/nlmaps.v2.train.mrl")
DEV_LEN=$(wc -l "$V2_DIR/nlmaps.v2.dev.mrl")
TEST_LEN=$(wc -l "$V2_DIR/nlmaps.v2.test.mrl")
cat "$V2_DIR/nlmaps.v2.train.mrl" \
    <(sed "$((TRAIN_LEN + 1))"',$d' "$V3_DIR/v3$SUFFIX.noise/nlmaps.v3$SUFFIX.train.mrl") \
    >"$V3_DIR/v3$SUFFIX.noise.plusv2.train.mrl"
cat "$V2_DIR/nlmaps.v2.dev.mrl" \
    <(sed "$((DEV_LEN + 1))"',$d' "$V3_DIR/v3$SUFFIX.noise/nlmaps.v3$SUFFIX.dev.mrl") \
    >"$V3_DIR/v3$SUFFIX.noise.plusv2.dev.mrl"
cat "$V2_DIR/nlmaps.v2.dev.mrl" \
    <(sed "$((DEV_LEN + 1))"',$d' "$V3_DIR/v3$SUFFIX.noise/nlmaps.v3$SUFFIX.dev.mrl") \
    >"$V3_DIR/v3$SUFFIX.noise.plusv2.dev.mrl"
