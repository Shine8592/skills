#!/usr/bin/env python3
import subprocess
import sys

def convert(input_file, output_format):
    cmd = f"ffmpeg -i {input_file} output.{output_format}"
    subprocess.run(cmd, shell=True)

if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
