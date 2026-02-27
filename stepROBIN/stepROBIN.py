#!/usr/bin/python3

import numpy as np
import meshio as mio
import argparse as ag

# ----------------------- GEOMETRY FORMULAS ---------------------------

eps = np.spacing(1.0)

def getSectionIndex(x, isPylon = False):
    idx = np.empty(x.size).astype(int)
    for i in range(x.size):
        if isPylon:
            idx[i] = 4 if x[i] < 0.8 else 5
        else:
            if x[i] < 0.4:
                idx[i] = 0
            elif x[i] < 0.8:
                idx[i] = 1
            elif x[i] < 1.9:
                idx[i] = 2
            else:
                idx[i] = 3
    return idx

def getChebyshevNodes(a, b, n):
    k = np.arange(n+1)
    nodes = 0.5*(a+b) + 0.5*(b-a)*np.cos((2.0*(n-k))*np.pi*0.5/n)
    nodes[0], nodes[n] = a, b
    return nodes

def getsuperval(x, c):
    cval = (x+c[2])/c[3]
    negPowerTerm = c[0] +c[1]*np.sign(cval)*np.abs(cval)**c[4]
    val = c[5] + c[6]*np.power(np.maximum(0.0, negPowerTerm), 1.0/c[7])
    return val

def getRadialCoordinate(H, W, theta, N):
    numer = 0.25*H*W
    denom = np.power(0.5*H*np.abs(np.sin(theta)), N) + \
            np.power(0.5*W*np.abs(np.cos(theta)), N)
    denom[np.abs(denom) < eps] = 1.0
    return numer / np.power(denom, 1.0/N)

def getVertices(nx, nt, isPylon=False):
    hcoeff = np.array([
        [1.0, -1.0, -0.4, -0.4, 1.8, 0.0, 0.25, 1.8],
        [0.0, 0.0, 0.0, 1.0, 0.0, 0.25, 0.0, 1.0],
        [1.0, -1.0, -0.8, 1.1, 1.5, 0.05, 0.2, 0.6],
        [1.0, -1.0, -1.9, 0.1, 2.0, 0.0, 0.05, 2.0],
        [1.0, -1.0, -0.8, -0.4, 3.0, 0.0, 0.145, 3.0],
        [1.0, -1.0, -0.8, 0.218, 2.0, 0.0, 0.145, 2.0]
    ])

    wcoeff = np.array([
        [1.0, -1.0, -0.4, -0.4, 2.0, 0.0, 0.25, 2.0],
        [0.0, 0.0, 0.0, 1.0, 0.0, 0.25, 0.0, 1.0],
        [1.0, -1.0, -0.8, 1.1, 1.5, 0.05, 0.2, 0.6],
        [1.0, -1.0, -1.9, 0.1, 2.0, 0.0, 0.05, 2.0],
        [1.0, -1.0, -0.8, -0.4, 3.0, 0.0, 0.166, 3.0],
        [1.0, -1.0, -0.8, 0.218, 2.0, 0.0, 0.166, 2.0]
    ])

    zcoeff = np.array([
        [1.0, -1.0, -0.4, -0.4, 1.8, -0.08, 0.08, 1.8],
        [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
        [1.0, -1.0, -0.8, 1.1, 1.5, 0.04, -0.04, 0.6],
        [0.0, 0.0, 0.0, 1.0, 0.0, 0.04, 0.0, 1.0],
        [0.0, 0.0, 0.0, 1.0, 0.0, 0.125, 0.0, 1.0],
        [1.0, -1.0, -0.8, 1.1, 1.5, 0.065, 0.06, 0.6]
    ])

    ncoeff = np.array([
        [2.0, 3.0, 0.0, 0.4, 1.0, 0.0, 1.0, 1.0],
        [0.0, 0.0, 0.0, 1.0, 0.0, 5.0, 0.0, 1.0],
        [5.0, -3.0, -0.8, 1.1, 1.0, 0.0, 1.0, 1.0],
        [0.0, 0.0, 0.0, 1.0, 0.0, 2.0, 0.0, 1.0],
        [0.0, 0.0, 0.0, 1.0, 0.0, 5.0, 0.0, 1.0],
        [0.0, 0.0, 0.0, 1.0, 0.0, 5.0, 0.0, 1.0]
    ])

    if isPylon:
        xBegin, xEnd = 0.4, 1.018
    else:
        xBegin, xEnd = 0.0, 2.0

    xval = getChebyshevNodes(xBegin, xEnd, nx)
    xol = np.tile(xval, (nt, 1)).T

    secIdx = getSectionIndex(xval, isPylon)
    theta = 2*np.pi*np.arange(nt)/float(nt)

    yol = np.empty_like(xol)
    zol = np.empty_like(xol)

    for ix in range(nx+1):
        H = getsuperval(xval, hcoeff[secIdx[ix], :])
        W = getsuperval(xval, wcoeff[secIdx[ix], :])
        Z0 = getsuperval(xval, zcoeff[secIdx[ix], :])
        N = getsuperval(xval, ncoeff[secIdx[ix], :])

        r = getRadialCoordinate(H[ix], W[ix], theta, N[ix])
        yol[ix, :] = r*np.sin(theta)
        zol[ix, :] = r*np.cos(theta) + Z0[ix]

    yol[:, -1] = yol[:, 0]
    zol[:, -1] = zol[:, 0]

    return xol, yol, zol

# ---------------------- OCC / STEP EXPORT ---------------------------

from OCC.Core.TColgp import TColgp_Array2OfPnt
from OCC.Core.gp import gp_Pnt
from OCC.Core.GeomAPI import GeomAPI_PointsToBSplineSurface
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCC.Core.IFSelect import IFSelect_RetDone

def surface_from_points(x, y, z):
    nx1, nt = x.shape
    pts = TColgp_Array2OfPnt(1, nx1, 1, nt)

    for i in range(nx1):
        for j in range(nt):
            pts.SetValue(i+1, j+1,
                gp_Pnt(float(x[i,j]), float(y[i,j]), float(z[i,j])))

    return GeomAPI_PointsToBSplineSurface(pts).Surface()

def write_step_surface(surface, filename):
    face = BRepBuilderAPI_MakeFace(surface, 1e-6).Face()
    writer = STEPControl_Writer()
    writer.Transfer(face, STEPControl_AsIs)
    stat = writer.Write(filename)
    if stat != IFSelect_RetDone:
        raise RuntimeError("STEP write failed")
    print(f"STEP written: {filename}")

# --------------------------- MAIN -----------------------------------

def getArguments():
    parser = ag.ArgumentParser()
    parser.add_argument("nxFuselage", type=int)
    parser.add_argument("ntFuselage", type=int)
    parser.add_argument("nxPylon", type=int)
    parser.add_argument("ntPylon", type=int)
#    parser.add_argument("-f", default='step',
#                        choices=['csv','dat','obj','ply','stl','vtu','vtk','step'],
#                        help="Output format")
    return parser.parse_args()


if __name__ == "__main__":

    args = getArguments()

    print("Generating ROBIN surfaces...")

    # Generate geometry
    xF, yF, zF = getVertices(args.nxFuselage, args.ntFuselage)
    xP, yP, zP = getVertices(args.nxPylon, args.ntPylon, isPylon=True)

    # CAD export
#    if args.f == "step":
    fus_surf = surface_from_points(xF, yF, zF)
    pyl_surf = surface_from_points(xP, yP, zP)

    write_step_surface(fus_surf, "robin_fuselage.step")
    write_step_surface(pyl_surf, "robin_pylon.step")

#    else:
#        print("Mesh formats not shown here, but easy to re-enable.")

