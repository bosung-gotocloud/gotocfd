"""
Export a Salome Mesh to OpenFOAM.

It handles all types of cells. Use
salomeToOpenFOAM.exportToFoam(Mesh_1)
to export. Optionally an output dir can be given as argument.

It's also possible to select a mesh in the object browser and
run the script via file->load script (ctrl-T).

Groups of volumes will be treated as cellZones. If they are
present they will be put in the file cellZones. In order to convert
to regions use the OpenFOAM tool
splitMeshRegions - cellZones

No sorting of faces is done so you'll have to run
renumberMesh -overwrite
In order to use the mesh.
"""
#Copyright 2013
#Author Nicolas Edh,
#Nicolas.Edh@gmail.com,
#or user "nsf" at cfd-online.com
#
#License
#
#    This script is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    salomeToOpenFOAM  is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with hexBlocker.  If not, see <http://www.gnu.org/licenses/>.
#
#    The license is included in the file LICENSE.
#

# Modified to support cellZones and GUI improvements by bosung-gotocloud 2025
"""
1.Data Processing (cellZone Support)
A new logic has been implemented within the exportToFoam function 
to identify SMESH.VOLUME types.  It automatically maps the Salome volume IDs 
to OpenFOAM cell IDs and records them in a dedicated cellZones file.

User Interface (Group Differentiation)
The GUI has been upgraded to distinguish between group types. 
Instead of listing all groups in generic combo boxes, it now allows boundary 
type configuration for FACE groups while visually labeling VOLUME groups 
as "CellZones" to prevent user error.

Real-time Feedback: 
A status update feature was added to the run() function. 
The GUI now displays a "Writing mesh files..." message immediately upon execution, 
providing better visual confirmation of the export progress.
"""

import sys
import salome
import SMESH
from salome.smesh import smeshBuilder
import os, time

# Compatibility layer for PyQt4 and PyQt5 to ensure the GUI runs in different Salome versions
try:
    from PyQt4 import QtGui, QtCore
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *
except:
    from PyQt5.QtWidgets import QWidget, QMessageBox
    from PyQt5 import QtCore, QtGui
    import PyQt5.QtCore as QtCore
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import Qt

# Debug level: 0 = quiet, 1 = standard info, 2+ = verbose technical details
debug = 1
verify = True  # If True, checks and fixes face orientation (ensures normals point outward)

class MeshBuffer(object):
    """
    Optimization class that buffers face nodes to reduce expensive calls to the Salome API.
    """
    def __init__(self, mesh, v):
        i = 0
        faces = list()
        keys = list()
        fnodes = mesh.GetElemFaceNodes(v, i)

        while fnodes:
            faces.append(fnodes)
            keys.append(tuple(sorted(fnodes))) # Create a unique key for the face regardless of node order
            i += 1
            fnodes = mesh.GetElemFaceNodes(v, i)
        
        self.v = v         
        self.faces = faces 
        self.keys = keys
        self.fL = i        

    @staticmethod
    def Key(fnodes):
        """Generates a hashable key by sorting node IDs."""
        return tuple(sorted(fnodes))
    
    @staticmethod
    def ReverseKey(fnodes):
        """Generates a key with reversed order, used for identifying baffle faces."""
        if type(fnodes) is tuple:
            return tuple(reversed(fnodes))
        else:
            return tuple(sorted(fnodes, reverse=True)) 

def exportToFoam(mesh, dirname='polyMesh'):
    """
    Core algorithm to convert Salome Mesh structures to OpenFOAM polyMesh files.
    """
    starttime = time.time()
    
    # Create the directory structure if it doesn't exist
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    try:
        filePoints = open(dirname + '/points', 'w')
        fileFaces = open(dirname + '/faces', 'w')
        fileOwner = open(dirname + '/owner', 'w')
        fileNeighbour = open(dirname + '/neighbour', 'w')
        fileBoundary = open(dirname + '/boundary', 'w')
    except Exception:
        print('Could not open files for writing.')
        return

    smesh = smeshBuilder.New()
    volumes = mesh.GetElementsByType(SMESH.VOLUME)
    
    # Step 1: Identify boundary faces
    # Filter for faces that are on the 'free' boundary of the volume mesh
    filter = smesh.GetFilter(SMESH.EDGE, SMESH.FT_FreeFaces)
    extFaces = set(mesh.GetIdsFromFilter(filter))
    nrExtFaces = len(extFaces)
    
    buffers = list()
    nrFaces = 0
    for v in volumes:
        b = MeshBuffer(mesh, v)
        nrFaces += b.fL
        buffers.append(b)

    # Calculate total and internal face counts
    nrFaces = int((nrFaces + nrExtFaces) / 2)
    nrIntFaces = int(nrFaces - len(extFaces))

    # Step 2: Process Groups into OpenFOAM Boundaries (Patches)
    faces = [] 
    facesSorted = dict() 
    bcFaces = [] 
    bcFacesSorted = dict()
    grpStartFace = [] 
    grpNrFaces = [] 
    grpNames = [] 
    ofbcfid = 0   
    nrExtFacesInGroups = 0

    for gr in mesh.GetGroups():
        if gr.GetType() == SMESH.FACE:
            grpNames.append(gr.GetName())
            grIds = gr.GetIDs()
            nr = len(grIds)
            if nr > 0:
                grpStartFace.append(nrIntFaces + ofbcfid)
                grpNrFaces.append(nr)

            for sfid in grIds:
                fnodes = mesh.GetElemNodes(sfid)
                key = MeshBuffer.Key(fnodes)
                if not key in bcFacesSorted:
                    bcFaces.append(fnodes)
                    bcFacesSorted[key] = ofbcfid
                    ofbcfid += 1
                else:
                    raise Exception('Face %d belongs to multiple groups!' % sfid)

            # Handle Baffles (Internal faces treated as boundaries)
            if __isGroupBaffle__(mesh, gr, extFaces):
                nrIntFaces -= nr
                grpStartFace = [x - nr for x in grpStartFace]
                grpNrFaces[-1] = nr * 2
                for sfid in gr.GetIDs():
                    fnodes = mesh.GetElemNodes(sfid)
                    key = MeshBuffer.ReverseKey(fnodes)
                    bcFaces.append(fnodes)
                    bcFacesSorted[key] = ofbcfid
                    ofbcfid += 1
            else:
                nrExtFacesInGroups += nr

    # Step 3: Map Owners and Neighbours
    # This loop determines which cell 'owns' a face and which is the 'neighbour'
    owner = [-1] * nrFaces
    neighbour = [-1] * nrIntFaces
    offid = 0
    ofvid = 0 
    for b in buffers:
        nodes = mesh.GetElemNodes(b.v)
        fi = 0
        while fi < b.fL:
            fnodes = b.faces[fi]
            key = b.keys[fi]
            try:
                # If key exists, it's an internal face being visited the second time (Neighbour)
                fidinof = facesSorted[key]
                neighbour[fidinof] = ofvid
            except KeyError:
                try:
                    # Check if it is a Boundary Face
                    bcind = bcFacesSorted[key]
                    if owner[nrIntFaces + bcind] == -1:
                        owner[nrIntFaces + bcind] = ofvid
                        bcFaces[bcind] = fnodes
                    else:
                        key = MeshBuffer.ReverseKey(fnodes)
                        bcind = bcFacesSorted[key]
                        bcFaces[bcind] = fnodes
                        owner[nrIntFaces + bcind] = ofvid
                except KeyError:
                    # New internal face being visited the first time (Owner)
                    if verify:
                        if not __verifyFaceOrder__(mesh, nodes, fnodes):
                            fnodes.reverse() # Correct orientation to point out of owner cell
                    faces.append(fnodes)
                    facesSorted[key] = offid
                    owner[offid] = ofvid
                    offid += 1
            fi += 1
        ofvid += 1

    # Step 4: Sort into Upper Triangular Order
    # Required for OpenFOAM solver efficiency
    ownedfaces = 1
    quickrange = range if sys.version_info.major > 2 else xrange
    for faceId in quickrange(0, nrIntFaces):
        cellId = owner[faceId]
        if faceId + 1 < len(owner) and cellId == owner[faceId + 1]:
            ownedfaces += 1
            continue
        if ownedfaces > 1:
            sId = faceId - ownedfaces + 1
            eId = faceId
            inds = range(sId, eId + 1)
            if sys.version_info.major > 2:
                sorted_inds = sorted(inds, key=neighbour.__getitem__)
            else:
                inds.sort(key = neighbour.__getitem__)
                sorted_inds = inds
            neighbour[sId:eId + 1] = map(neighbour.__getitem__, sorted_inds)
            faces[sId:eId + 1] = map(faces.__getitem__, sorted_inds)
        ownedfaces = 1

    converttime = time.time() - starttime

    # Step 5: Write PolyMesh files
    __writeHeader__(filePoints, 'points')
    points = mesh.GetElementsByType(SMESH.NODE)
    filePoints.write('\n%d\n(\n' % len(points))
    for ni in points:
        pos = mesh.GetNodeXYZ(ni)
        filePoints.write('\t(%.10g %.10g %.10g)\n' % (pos[0], pos[1], pos[2]))
    filePoints.write(')\n')
    filePoints.close()

    __writeHeader__(fileFaces, 'faces')
    fileFaces.write('\n%d\n(\n' % nrFaces)
    for node in faces + bcFaces:
        fileFaces.write('\t%d(' % len(node))
        for p in node: fileFaces.write('%d ' % (p - 1))
        fileFaces.write(')\n')
    fileFaces.write(')\n')
    fileFaces.close()

    __writeHeader__(fileOwner, 'owner', len(points), ofvid, nrFaces, nrIntFaces)
    fileOwner.write('\n%d\n(\n' % len(owner))
    for cell in owner: fileOwner.write(' %d \n' % cell)
    fileOwner.write(')\n')
    fileOwner.close()

    __writeHeader__(fileNeighbour, 'neighbour', len(points), ofvid, nrFaces, nrIntFaces)
    fileNeighbour.write('\n%d\n(\n' % len(neighbour))
    for cell in neighbour: fileNeighbour.write(' %d\n' % cell)
    fileNeighbour.write(')\n')
    fileNeighbour.close()

    __writeHeader__(fileBoundary, 'boundary')
    fileBoundary.write('%d\n(\n' % len(grpStartFace))
    for ind, gname in enumerate(grpNames):
        fileBoundary.write('\t%s\n\t{\n' % gname)
        fileBoundary.write('\ttype\t\t%s;\n' % str(bound[ind].currentText()))
        fileBoundary.write('\tnFaces\t\t%d;\n' % grpNrFaces[ind])
        fileBoundary.write('\tstartFace\t%d;\n' % grpStartFace[ind])
        fileBoundary.write('\t}\n')
    fileBoundary.write(')\n')
    fileBoundary.close()

    # --- NEW LOGIC: Export Volume Groups as cellZones ---
    # This section identifies all VOLUME-type groups in Salome and creates a 
    # cellZones file mapping Salome cell IDs to OpenFOAM cell IDs.
    nrCellZones = 0
    cellZonesName = list()
    for grp in mesh.GetGroups():
        if grp.GetType() == SMESH.VOLUME:
            nrCellZones += 1
            cellZonesName.append(grp.GetName())

    if nrCellZones > 0:
        fileCellZones = open(dirname + '/cellZones', 'w')
        scToOFc = dict([sa, of] for of, sa in enumerate(volumes))
        __writeHeader__(fileCellZones, 'cellZones')
        fileCellZones.write('\n%d(\n' % nrCellZones)
        for grp in mesh.GetGroups():
            if grp.GetType() == SMESH.VOLUME:
                fileCellZones.write(grp.GetName() + '\n{\n')
                fileCellZones.write('\ttype\tcellZone;\n')
                fileCellZones.write('\tcellLabels\tList<label>\n')
                cellSalomeIDs = grp.GetIDs()
                fileCellZones.write('%d\n(\n' % len(cellSalomeIDs))
                for csId in cellSalomeIDs:
                    fileCellZones.write('%d\n' % scToOFc[csId])
                fileCellZones.write(');\n}\n')
        fileCellZones.write(')\n')
        fileCellZones.close()

    print('Export Complete. Total time: %.3fs' % (time.time() - starttime))

def __writeHeader__(file, fileType, nrPoints=0, nrCells=0, nrFaces=0, nrIntFaces=0):
    """Writes the mandatory OpenFOAM file header."""
    file.write("/*" + "-"*68 + "*\\\n" )
    file.write("| SalomeToFoamExporter " + " "*(47) + "|\n")
    file.write("\*" + "-"*68 + "*/\n")
    file.write("FoamFile\n{\n")
    file.write("\tversion\t\t2.0;\n\tformat\t\tascii;\n")
    file.write("\tclass\t\t")
    if fileType == "points": file.write("vectorField;\n")
    elif fileType == "faces": file.write("faceList;\n")
    elif fileType in ["owner", "neighbour"]:
        file.write("labelList;\n")
        file.write("\tnote\t\t\"nPoints: %d nCells: %d nFaces: %d nInternalFaces: %d\";\n" % (nrPoints, nrCells, nrFaces, nrIntFaces))
    elif fileType == "boundary": file.write("polyBoundaryMesh;\n")
    elif fileType == "cellZones": file.write("regIOobject;\n")
    file.write("\tlocation\t\"constant/polyMesh\";\n")
    file.write("\tobject\t\t" + fileType + ";\n}\n\n")

# Utility functions for geometric calculations (Normal, Center of Gravity, etc.)
def __verifyFaceOrder__(mesh, vnodes, fnodes):
    vc = __cog__(mesh, vnodes)
    fc = __cog__(mesh, fnodes)
    fcTovc = __diff__(vc, fc)
    fn = __calcNormal__(mesh, fnodes)
    return __dotprod__(fn, fcTovc) <= 0.0

def __cog__(mesh, nodes):
    c = [0.0, 0.0, 0.0]
    for n in nodes:
        pos = mesh.GetNodeXYZ(n)
        for i in range(3): c[i] += pos[i]
    return [x/len(nodes) for x in c]

def __calcNormal__(mesh, nodes):
    p0, p1, pn = mesh.GetNodeXYZ(nodes[0]), mesh.GetNodeXYZ(nodes[1]), mesh.GetNodeXYZ(nodes[-1])
    u, v = __diff__(p1, p0), __diff__(pn, p0)
    return [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]

def __diff__(u, v): return [u[i]-v[i] for i in range(3)]
def __dotprod__(u, v): return sum(u[i]*v[i] for i in range(3))

def findSelectedMeshes():
    """Returns a list of meshes currently selected in the Salome Object Browser."""
    meshes = list()
    smesh = smeshBuilder.New()
    for i in range(salome.sg.SelectedCount()):
        selobj = salome.myStudy.FindObjectID(salome.sg.getSelected(i)).GetObject()
        meshes.append(smesh.Mesh(selobj))
    return meshes if meshes else None

def __isGroupBaffle__(mesh, group, extFaces):
    """Checks if a face group is internal (a baffle) or on the boundary."""
    for sid in group.GetIDs():
        if not sid in extFaces: return True
    return False

def run():
    """Callback for the 'OK' button to start export."""
    dialog.setEnabled(False)
    l_status.setText("Writing mesh files...")
    QApplication.processEvents() # Force GUI update to show status
    
    meshes = findSelectedMeshes()
    for m in meshes:
        outdir = str(l_direcOutput.text()) + "/constant/polyMesh"
        exportToFoam(m, outdir)
        QMessageBox.information(None, 'Information', "Mesh exported to: " + outdir)
        dialog.close()

def hide(): dialog.hide()
def meshFile():
    path = QFileDialog.getExistingDirectory(qApp.activeWindow(), 'Select output directory')
    l_direcOutput.setText(str(path))

# --- GUI SETUP ---
dialog = QDialog()
dialog.setWindowTitle("Salome to OpenFOAM (cellZone Support)")
layout = QGridLayout(dialog)
bound = [] # Stores references to dropdown menus for patches

# Output Directory Selection
layout.addWidget(QLabel("Output Directory:"), 1, 0)
l_direcOutput = QLineEdit()
pb_direcOutput = QPushButton("...")
layout.addWidget(l_direcOutput, 2, 0)
layout.addWidget(pb_direcOutput, 2, 1)

l_status = QLabel("")
layout.addWidget(l_status, 100, 0, 1, 2)

# Group/Boundary Type Mapping
# This section dynamically builds the UI based on whether a group is a face (Boundary)
# or a volume (cellZone).
meshes = findSelectedMeshes()
if meshes:
    for mesh in meshes:
        row = 6
        layout.addWidget(QLabel("Groups Mesh:"), row, 0)
        layout.addWidget(QLabel("Boundary Type:"), row, 1)
        row += 1
        for gr in mesh.GetGroups():
            layout.addWidget(QLabel(gr.GetName()), row, 0)
            if gr.GetType() == SMESH.FACE:
                cmb = QComboBox()
                cmb.addItems(["patch", "wall", "symmetry", "empty", "wedge", "cyclic"])
                bound.append(cmb)
                layout.addWidget(cmb, row, 1)
            elif gr.GetType() == SMESH.VOLUME:
                lbl = QLabel("CellZone")
                lbl.setStyleSheet("color: green; font-weight: bold;")
                layout.addWidget(lbl, row, 1)
            row += 1

okbox = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
layout.addWidget(okbox, row + 1, 0, 1, 2)
okbox.accepted.connect(run)
okbox.rejected.connect(hide)
pb_direcOutput.clicked.connect(meshFile)
dialog.show()
