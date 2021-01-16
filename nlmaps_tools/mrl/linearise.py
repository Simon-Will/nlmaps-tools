#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Runs the functionaliser on the supplied file"""
import argparse

from . import local_io, mrl


def parse_arguments():
    """Parses the command line arguments.

    :return parsed_arguments: a dictionary containing the command line arguments
    """
    parser = argparse.ArgumentParser(description='A neural network based semantic parser for NLmaps')
    parser.add_argument('--input', '-i', required=True, help='Location of input file')
    parser.add_argument('--output', '-o', required=True, help='Location of output file')
    parsed_arguments = parser.parse_args()
    return parsed_arguments


def main():
    parsed_arguments = parse_arguments()
    mrl_world = mrl.MRLS['nlmaps']()
    input = local_io.read_lines_in_list(parsed_arguments.input)
    output = []
    for line in input:
        output.append(mrl_world.preprocess_mrl(line))
    local_io.write_list_to_file(output, parsed_arguments.output)


if __name__ == '__main__':
    main()
