from astropy import wcs
from astropy.io import fits
import numpy as np
from astropy.convolution import Gaussian2DKernel
from astropy.convolution import convolve
import matplotlib.pyplot as plt


_fits_header = """
NAXIS   =                    2
NAXIS1  =                   %i
NAXIS2  =                   %i
CTYPE1  = 'RA---AIT'
CRPIX1  =                   %i
CRVAL1  =                   %s
CDELT1  =                  -%f
CUNIT1  = 'deg     '
CTYPE2  = 'DEC--AIT'
CRPIX2  =                   %i
CRVAL2  =                   %s
CDELT2  =                   %f
CUNIT2  = 'deg     '
COORDSYS= '%s'
"""


def plot_counts_map(ra, dec, side, pixel_size, smoothing_kernel=0.0):
    """
    Plot a counts map

    :param ra: array of Right Ascension
    :param dec: array of Declinations
    :param side: side of the image in deg. The produced image will not be exactly this big because the number of pixels
    must be even.
    :param pixel_size: size of the pixel (in deg)
    :param smoothing_kernel: width of the smoothing kernel (in deg)
    :return: a matplotlib Figure
    """
    # Look for center of data
    ra_center = np.average(ra)
    dec_center = np.average(dec)

    # Make a even number of pixels
    npix = int(np.ceil(side / pixel_size / 2.0)) * 2

    header = _fits_header % (npix, npix,
                             npix // 2, ra_center, pixel_size,
                             npix // 2, dec_center, pixel_size,
                             'icrs'
                             )

    w = wcs.WCS(fits.Header.fromstring(header, sep='\n'))

    i, j = w.all_world2pix(ra, dec, 0, ra_dec_order=True)

    img = np.zeros((npix, npix))

    idx = (i > 0) & (i < npix) & (j > 0) & (j < npix)

    img[j[idx].astype(int), i[idx].astype(int)] += 1

    if smoothing_kernel > 0.0:

        kernel = Gaussian2DKernel(smoothing_kernel)

        img_conv = convolve(img, kernel)  # type: np.ndarray

    else:

        # No smoothing

        img_conv = img

    fig = plt.figure()
    sub = fig.add_subplot(111, projection=w)

    _ = sub.imshow(img_conv, origin='lower', cmap='hot')

    return fig