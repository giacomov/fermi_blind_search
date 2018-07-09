import os
import collections
from fermi_blind_search.fits_handling.fits_interface import pyfits
from astropy.io.fits import HDUList, PrimaryHDU, BinTableHDU

import fitsio
import numpy as np
from fermi_blind_search.angular_distance import angular_distance_fast


def make_GTI_from_FT2(ft2filename, filter_expression, gti_filename, overwrite=True,
                      force_start=None, force_stop=None):

    if force_start is not None:

        assert force_stop is not None

        filter_expression += " && (STOP >= %s) && (START <= %s)" % (force_start, force_stop)

    with fitsio.FITS(ft2filename, 'r') as fits:

        indexes_to_keep = fits['SC_DATA'].where(filter_expression)
        indexes_to_keep.sort()

        data = fits['SC_DATA'].read(rows=indexes_to_keep, columns=['START', 'STOP'])

    # Make sure it is sorted
    idx = np.argsort(data['START'])
    data = data[idx]

    start = data['START']
    stop = data['STOP']

    gti_starts = np.sort(list(set(start) - set(stop)))
    gti_stops = np.sort(list(set(stop) - set(start)))

    assert len(gti_starts) == len(gti_stops)

    # Fix the global start and stop if required
    if force_start is not None:

        gti_starts[0] = max(gti_starts[0], force_start)
        gti_stops[-1] = min(gti_stops[-1], force_stop)

    if os.path.exists(gti_filename):

        if overwrite:

            os.remove(gti_filename)

        else:

            raise IOError("%s already exists and overwrite is False" % gti_filename)

    # Make GTI file
    with fitsio.FITS(gti_filename, 'rw') as fits:

        array_list = [gti_starts, gti_stops]
        names = ['START', 'STOP']
        fits.write(array_list, names=names, extname='GTI')

    return gti_starts, gti_stops


def update_GTIs(fits_file, gti_starts, gti_stops):

    with fitsio.FITS(fits_file, 'rw') as fits:

        fits['GTI'].resize(len(gti_starts))

        array_list = [gti_starts, gti_stops]
        names = ['START', 'STOP']
        fits['GTI'].write(array_list, names=names, extname='GTI')


class FitsFile(object):

    def __init__(self, filename, extension=None, filter_expr=None, cone=None):

        # If there is a filter to be applied, get the indexes of the elements to keep
        if extension is not None:

            assert filter_expr is not None, "If you provide an extension, you also need to provide a filter for it"

        # Make sure the file exists
        assert os.path.exists(filename), "%s does not exist" % filename
        
        # Read all extensions
        self._extensions = collections.OrderedDict()

        with pyfits.open(filename) as f:

            # Get also the primary extension with its header

            self._primary = PrimaryHDU(f[0].data, header=f[0].header)

            for ext_id in range(1, len(f)):

                # Read name of the extension and use it as key, if it exists, otherwise use
                # just the ordinal number

                name = f[ext_id].header.get('EXTNAME')

                if name is not None:

                    key = name

                else:

                    key = ext_id

                # Apply filtering if provided.
                # This can follow the CFITSIO advanced filtering, where you can filter for regions,
                # gtis and so on

                if extension is not None:

                    if key == extension:

                        # This is the extension to be filtered

                        with fitsio.FITS(filename, 'r') as fits:

                            indexes_to_keep = fits[extension].where(filter_expr)
                            indexes_to_keep.sort()

                            # Apply cone filter if any
                            if cone is not None:

                                ra_c, dec_c, radius = cone

                                data = fits['EVENTS'].read(rows=indexes_to_keep, columns=['RA', 'DEC'])

                                distances = angular_distance_fast(ra_c, dec_c, data['RA'], data['DEC'])

                                idx = (distances <= radius)

                                indexes_to_keep = indexes_to_keep[idx]

                        self._extensions[key] = BinTableHDU(f[ext_id].data[indexes_to_keep], f[ext_id].header)

                    else:

                        # This is an extension for which no filter has been provided

                        self._extensions[key] = BinTableHDU(f[ext_id].data, f[ext_id].header)

                else:

                    # No filter provided at all

                    self._extensions[key] = BinTableHDU(f[ext_id].data, f[ext_id].header)

    def write_to(self, filename, overwrite=False):

        hdu_list = HDUList([self._primary])

        for ext_name in self._extensions:

            this_hdu = self._extensions[ext_name]

            #this_hdu.verify('silentfix')

            hdu_list.append(this_hdu)

        hdu_list.writeto(filename, overwrite=overwrite)

    def __getitem__(self, item):

        return self._extensions[item]


