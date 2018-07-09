import numpy as np


def angular_distance_fast(ra1, dec1, ra2, dec2):
    """
    Compute angular distance using the Haversine formula. Use this one when you know you will never ask for points at
    their antipodes. If this is not the case, use the angular_distance function which is slower, but works also for
    antipodes.

    :param lon1:
    :param lat1:
    :param lon2:
    :param lat2:
    :return:
    """

    lon1 = np.deg2rad(ra1)
    lat1 = np.deg2rad(dec1)
    lon2 = np.deg2rad(ra2)
    lat2 = np.deg2rad(dec2)
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon /2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return np.rad2deg(c)