#!/usr/bin/env python

# Distribute a set of points randomly across a sphere, allow them
# to mutually repel and find equilibrium.

import sys, os
import string
import random
from math import pi, asin, atan2, cos, sin, sqrt

import matplotlib.pyplot as plt
plt.interactive(False)

import numpy as np

def cartToSph(xyz):
    ptsnew = np.zeros([xyz.shape[0],2])
    xy = xyz[:,0]**2 + xyz[:,1]**2
    #ptsnew[:,0] = np.sqrt(xy + xyz[:,2]**2)
    ptsnew[:,0] = np.rad2deg(np.arctan2(xyz[:,1], xyz[:,0]))+180
    ptsnew[:,1] = np.rad2deg(np.arccos(xyz[:,2]))-90 # for elevation angle defined from Z-axis down
    #ptsnew[:,4] = np.arctan2(xyz[:,2], np.sqrt(xy)) # for elevation angle defined from XY-plane up
    
    return ptsnew

from GtBurst.angularDistance import getAngularDistance

def computeSpread(points,plot=False):
    minD = []
    for r,d in points:
        distances = getAngularDistance(r,d,points[:,0],points[:,1])
        minD.append(distances[distances > 0].min())
    if(plot):
      plt.hist(minD)
    return max(minD)-min(minD),np.median(minD)


args = sys.argv[1:]

if len(args) > 0:
    n = string.atoi(sys.argv[1])
    args = args[1:]
else:
    n = 7

if len(args) > 0:
    if(os.path.exists(args[0])):
      raise RuntimeError("File exists")
    outfile = open(args[0], "w+")
    args = args[1:]
else:
    outfile = sys.stdout

points = []

def realprint(a):
    for i in range(len(a)):
        outfile.write(str(a[i]))
        if i < len(a)-1:
            outfile.write(" ")
        else:
            outfile.write("\n")

def pprint(*a):
    realprint(a)

#for i in range(n):
    # Invent a randomly distributed point.
    #
    # To distribute points uniformly over a spherical surface, the
    # easiest thing is to invent its location in polar coordinates.
    # Obviously theta (longitude) must be chosen uniformly from
    # [0,2*pi]; phi (latitude) must be chosen in such a way that
    # the probability of falling within any given band of latitudes
    # must be proportional to the total surface area within that
    # band. In other words, the probability _density_ function at
    # any value of phi must be proportional to the circumference of
    # the circle around the sphere at that latitude. This in turn
    # is proportional to the radius out from the sphere at that
    # latitude, i.e. cos(phi). Hence the cumulative probability
    # should be proportional to the integral of that, i.e. sin(phi)
    # - and since we know the cumulative probability needs to be
    # zero at -pi/2 and 1 at +pi/2, this tells us it has to be
    # (1+sin(phi))/2.
    #
    # Given an arbitrary cumulative probability function, we can
    # select a number from the represented probability distribution
    # by taking a uniform number in [0,1] and applying the inverse
    # of the function. In this case, this means we take a number X
    # in [0,1], scale and translate it to obtain 2X-1, and take the
    # inverse sine. Conveniently, asin() does the Right Thing in
    # that it maps [-1,+1] into [-pi/2,pi/2].

#    theta = random.random() * 2*pi
#    phi = asin(random.random() * 2 - 1)
#    points.append((cos(theta)*cos(phi), sin(theta)*cos(phi), sin(phi)))


import numpy as np

import math

def uniform_spherical_distribution(N): 
    pts = []   
    inc = math.pi * (3 - math.sqrt(5)) 
    off = 2 / float(N) 
    for k in range(0, int(N)): 
        y = k * off - 1 + (off / 2) 
        r = math.sqrt(1 - y*y) 
        phi = k * inc 
        pts.append([math.cos(phi)*r, y, math.sin(phi)*r])   
    return pts

points = uniform_spherical_distribution(n)
#points = map(lambda x:[float(x[0]),float(x[1]),float(x[2])],np.recfromtxt("out3.txt"))
sph = cartToSph(np.array(points))
spread,median = computeSpread(sph,False)
#plt.show()
#sys.exit()
sys.stderr.write("Spread before computation: %s (med. dist. %s)\n" %(spread,median))


# For the moment, my repulsion function will be simple
# inverse-square, followed by a normalisation step in which we pull
# each point back to the surface of the sphere.

Nmax = 200
res = {}

for hh in range(Nmax):
    # Determine the total force acting on each point.
    forces = []
    for i in range(len(points)):
        p = points[i]
        f = (0,0,0)
        ftotal = 0
        for j in range(len(points)):
            if j == i: continue
            q = points[j]

            # Find the distance vector, and its length.
            dv = (p[0]-q[0], p[1]-q[1], p[2]-q[2])
            dl = sqrt(dv[0]**2 + dv[1]**2 + dv[2]**2)

            # The force vector is dv divided by dl^3. (We divide by
            # dl once to make dv a unit vector, then by dl^2 to
            # make its length correspond to the force.)
            dl3 = dl ** 3
            fv = (dv[0]/dl3, dv[1]/dl3, dv[2]/dl3)

            # Add to the total force on the point p.
            f = (f[0]+fv[0], f[1]+fv[1], f[2]+fv[2])

        # Stick this in the forces array.
        forces.append(f)

        # Add to the running sum of the total forces/distances.
        ftotal = ftotal + sqrt(f[0]**2 + f[1]**2 + f[2]**2)
    
        
    # Scale the forces to ensure the points do not move too far in
    # one go. Otherwise there will be chaotic jumping around and
    # never any convergence.
    thr = 0.1
    if ftotal > thr:
        fscale = thr / ftotal
    else:
        fscale = 1
        
    
    # Move each point, and normalise. While we do this, also track
    # the distance each point ends up moving.
    dist = 0
    dists = []
    for i in range(len(points)):
        p = points[i]
        f = forces[i]
        p2 = (p[0] + min(f[0]*fscale,10), p[1] + f[1]*fscale, p[2] + f[2]*fscale)
        pl = sqrt(p2[0]**2 + p2[1]**2 + p2[2]**2)
        p2 = (p2[0] / pl, p2[1] / pl, p2[2] / pl)
        dv = (p[0]-p2[0], p[1]-p2[1], p[2]-p2[2])
        dl = sqrt(dv[0]**2 + dv[1]**2 + dv[2]**2)
        dist = dist + dl
        dists.append(dist)
        points[i] = p2
    
    sph = cartToSph(np.array(points))
    
    spread,median = computeSpread(sph,False)
    #plt.show()
    
    res[spread] = list(points)
    
    # Done. Check for convergence and finish.
    sys.stderr.write("%s (%s)\n" %(spread,median))
    if spread <= (0.290645811472):
        break

mm = min(res.keys())
print("Min is %s" %(mm))
for k,v in res.iteritems():
  if(k==mm):
    points = v

# Output the points.
for x, y, z in points:
    pprint(x, y, z)
