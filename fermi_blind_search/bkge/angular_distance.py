
from astropy.coordinates import SkyCoord
import astropy.units as u

def getAngularDistance(ra1,dec1,ra2,dec2):

    sky1 = SkyCoord(ra=ra1 * u.deg, dec=dec1 * u.deg, frame='icrs')

    sky2 = SkyCoord(ra=ra2 * u.deg, dec=dec2 * u.deg, frame='icrs')

    distance = sky1.separation(sky2)

    return distance.to(u.deg).value