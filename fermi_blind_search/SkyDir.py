# I do this because maybe in the future I will want to remove the dependence
# from the ST

from astropy.coordinates import SkyCoord
import astropy.units as u

class SkyDir(object):

    def __init__(self, lon, lat, system):

        if (system.lower() == 'equatorial'):

            sys = 'icrs'

        elif (system.lower() == 'galactic'):

            sys = 'galactic'

        else:

            raise RuntimeError("Unknown coordinate system %s" % (system))

        skydir_orig = SkyCoord(lon * u.degree, lat * u.degree, frame=sys)

        skydir_ircs = skydir_orig.transform_to('ircs')
        skydir_gal = skydir_orig.transform_to('galactic')

        self.ra = skydir_ircs.ra.value
        self.dec = skydir_ircs.dec.value
        self.l = skydir_gal.l.value
        self.b = skydir_gal.b.value

    pass


pass
