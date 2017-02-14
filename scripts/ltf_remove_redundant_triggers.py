#!/usr/bin/env python

"""This script takes trigger data from text files with 6 columns,
    obtains dec, ra, tstarts, tstops, and counts,
    and eliminates overlapping regions based on which is more significant,
    returning a text file with the result.
    The assumption is that when overlapping regions trigger simultaneously,
    they are triggering on the same event;
    this script chooses the most significant trigger and removes duplicate detections.
    Significance is determined primarily by number of time bins in a specified area of sky,
    and secondarily by the count rate in the highest count-density bin"""

import numpy as np
# from math import *
import argparse
from astropy.coordinates import SkyCoord
import astropy.units as u


def dist(region1, region2):
    """
    Compute the angular distance (in degrees) between the center of the two input regions

    :param region1: input region 1 (an object with a 'ra' and 'dec' items, typically a np.recarray)
    :param region2: input region 2 (an object with a 'ra' and 'dec' items, typically a np.recarray)
    :return: the angular distance in degrees
    """
    region1_center = SkyCoord(ra=region1['ra'] * u.degree, dec=region1['dec'] * u.degree, frame='icrs')

    region2_center = SkyCoord(ra=region2['ra'] * u.degree, dec=region2['dec'] * u.degree, frame='icrs')

    angular_distance = region1_center.separation(region2_center).to(u.degree)

    # angular_dist = acos(sin(region1['dec'])*sin(region2['dec']) +
    # cos(region1['dec'])*cos(region2['dec'])*cos(region1['ra']-region2['ra']))

    return angular_distance.value


def bins(inp_region):
    """
    return number of time bins in input region; arg should be region in inp_list

    :param inp_region: an object with a 'tstarts' field (typically a row of the input file)
    :return: the number of intervals defined
    """

    # create list of tstarts associated with inp_region
    list_in_string = inp_region['tstarts'].split(",")

    return len(list_in_string)


def find_most_significant_bin(inp_region):
    """
    returns most significant bin and its count rate, given a region as input

    :param inp_region: an object with a 'tstarts' field (typically a row of the input file)
    :return: a list containing the highest count rate of all bins, and the position of the corresponding bin
    in the list
    """

    # converts tstarts, etc. entry for i into a readable list

    region_starts = np.array(map(float, inp_region['tstarts'].split(",")))
    region_stops = np.array(map(float, inp_region['tstops'].split(",")))
    region_counts = np.array(map(float, inp_region['counts'].split(",")))

    dt = region_stops - region_starts

    assert np.all(dt > 0), "One time interval has a length <= 0, which is impossible"

    rate = region_counts / dt

    bin_max = np.argmax(rate)

    rate_max = rate[bin_max]

    return [rate_max, bin_max]


def check_nearest(regions, min_dist):
    """
    Remove redundant regions, finding the regions containing the most significant signal among all the overlapping
    regions.

    :param regions: a list of intervals (typically a np.recarray)
    :param min_dist: the minimum distance between the centers of two regions below which they are
    considered overlapping
    :return: a trimmed version of the input, where overlapping regions are removed so that only the most significant
    one is maintained (a np.recarray)
    """

    # primary iteration counter
    i = 0

    # flag as true to increment counter
    increment_i = True

    # import pdb;pdb.set_trace()

    # for each region in inp_list:
    while i in range(len(regions)):

        # secondary iteration counter
        j = i + 1

        # look at each subsequent region j
        # start from i+1 to avoid checking twice for overlapping regions

        while j in range(i + 1, len(regions)):

            # determine if i and j overlap
            if dist(regions[i], regions[j]) <= min_dist:

                # if so, remove the less significant region from output list

                # first see if one has more bins; this means it is more significant
                if bins(regions[j]) != bins(regions[i]):

                    # if i has more bins than j, it is therefore more significant
                    # remove j from list; do not inc j so as not to skip next list element
                    if bins(regions[j]) < bins(regions[i]):

                        # This essentially "pop" out the element j

                        regions = regions[regions["name"] != regions.name[j]]

                    else:

                        # j has more bins than i
                        # remove i from list; do not inc i so as not to skip next list element, and return to i loop

                        regions = regions[regions["name"] != regions.name[i]]
                        increment_i = False

                        break

                else:

                    # regions[i] and regions[j] have the same number of time bins
                    # find the bin in each with highest count rate; make sure highest bins are at the
                    # same place in terms of bin order; unsure if this accounts for cases where time bins are
                    # completely incogruent between regions i and j

                    # get most significant bin from region i and its rate; do same with j
                    max_rate_i, id_rate_i = find_most_significant_bin(regions[i])
                    max_rate_j, id_rate_j = find_most_significant_bin(regions[j])

                    # debug

                    print "i = %s, j = %s, will now raise error if %s != %s" % (i, j, id_rate_i, id_rate_j)

                    # check if the i bin is same place in terms of bin order as j
                    if id_rate_i != id_rate_j:

                        raise RuntimeError("Bin %s and bin %s are overlapping in space, but their maximum rate is not "
                                           "overlapping in time. This should never happen." % (i, j))

                    # check if highest rate in i > than in j
                    elif max_rate_i >= max_rate_j:

                        # i is more significant than j, remove j from list
                        regions = regions[regions["name"] != regions.name[j]]

                    else:

                        # j is more significant, remove i from list and return to parent loop
                        regions = regions[regions["name"] != regions.name[i]]
                        increment_i = False
                        break

            else:

                # Regions i and j do not overlap

                # nothing was removed from list, inc j to check next region
                j += 1

        # if i wasn't removed, so increment_i was never set to false, increment_i to check next region
        if increment_i:

            i += 1

        # if i was removed, do not inc i (so as not to skip next region) and reset increment_i flag
        else:

            increment_i = True

    # return pruned list
    return regions


# execute only if run from command line
if __name__ == "__main__":

    # create parser for this script
    parser = argparse.ArgumentParser('Remove redundant triggers which overlap spatially and temporally. For each group '
                                     'of overlapping triggers, keep only the most significant one.')

    # add the arguments needed to the parser
    parser.add_argument("--in_list", help="Text file containing the output list from the BB code", required=True,
                        type=str)
    # parser.add_argument("--min_dist", help="distance above which regions are not considered to overlap",
    #                     type=float, required=True)
    parser.add_argument("--out_list", help="Name for the output file, which will contained the pruned list",
                        required=True, type=str)

    # parse the arguments
    args = parser.parse_args()

    # get input data file from parser and convert to record array
    data = np.recfromtxt(args.in_list, dtype=[('name', 'S50'),
                                              ('ra', float),
                                              ('dec', float),
                                              ('tstarts', 'S1000'),
                                              ('tstops', 'S1000'),
                                              ('counts', 'S1000'),
                                              ('probabilities', 'S1000')])

    if len(data.shape) == 0:
        # The file contains only one line. In that case, unfortunately, recfromtxt does not produce
        # an array of lines, but just one line. Fix that
        data = np.array([data])

    from fermi_blind_search.Configuration import configuration

    # check for multiple triggers by same event,
    min_dist = float(configuration.get("Post processing", "cluster_distance"))
    result = check_nearest(data, min_dist)

    # import pdb;pdb.set_trace()

    # create output file
    with open(args.out_list, 'w+') as f:

        # write column headers
        f.write("# %s\n" % (" ".join(result.dtype.names)))

        # write each row of array to file, followed by line break
        for row in result:
            out = " ".join(map(str, row))

            f.write("%s" % out)

            f.write("\n")
