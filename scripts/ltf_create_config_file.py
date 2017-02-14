#!/usr/bin/env python

import argparse


default_config = '''

[Analysis]

# Instrument Response Function
irf = P8R2_SOURCE_V6

# Null-hyp probability
nullp = 1e-5

# Zenith cut for gtmktime
zenith_cut = 95

# Theta cut for gtmktime
theta_cut = 60

# Emin and emax in MeV
emin = 100
emax = 100000

# Maximum duration, above which any excess is excluded (in seconds)
Max_duration = 21600

# Minimum number of counts in excess
Min_counts = 3

[Post processing]
# Candidate transients within this distance from each other (in deg) will
# be checked and marked as the same transient if they overlap in time
cluster_distance = 15.0

[Hardware]
ncpus = 10
'''


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Create a configuration file for the LAT Transient factory')

    parser.add_argument('--outfile', help="name for output configuration file", required=True)

    args = parser.parse_args()

    with open(args.outfile, 'w+') as f:

        f.write(default_config)