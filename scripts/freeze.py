import argparse

from p19.acceptance import manifest, write_once

parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
args = parser.parse_args()
write_once(args.output, manifest())
print("Frozen acceptance manifest saved.")
