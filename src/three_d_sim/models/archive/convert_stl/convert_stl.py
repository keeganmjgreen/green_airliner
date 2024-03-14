from vpython import *

# Convert 3D .stl file ("stereo lithography") to VPython 7 object.

# Limitations:
#    Code for binary files needs to be updated to VPython 7.
#    Does not deal with color.
#    Does not assign texpos values to vertex objects,
#      so cannot add a meaningful texture to the final compound object.

# Original converter and STLbot by Derek Lura 10/06/09
# Be sure to look at the bottom of the STLbot figure!
# Part1.stl found at 3Dcontentcentral.com; also see 3dvia.com

# Factory function and handling of binary files by Bruce Sherwood 1/26/10
# Conversion to VPython 7 by Bruce Sherwood 2018 May 8

# Give this factory function an .stl file and it returns a compound object,
# to permit moving and rotating.

# Specify the file as a file name.

# See http://en.wikipedia.org/wiki/STL_(file_format)
# Text .stl file starts with a header that begins with the word "solid".
# Binary .stl file starts with a header that should NOT begin with the word "solid",
# but this rule seems not always to be obeyed.
# Currently the 16-bit unsigned integer found after each triangle in a binary
# file is ignored; some versions of .stl files put color information in this value.

def stl_to_triangles(fileinfo): # specify file
    # Accept a file name or a file descriptor; make sure mode is 'rb' (read binary)
    fd = open(fileinfo, mode='rb')
    text = fd.read()
    tris = [] # list of triangles to compound
    if False: # prevent executing code for binary file
        pass
    # The following code for binary files must be updated:
    else:
        fd.seek(0)
        fList = fd.readlines()
    
        # Decompose list into vertex positions and normals
        vs = []
        for line in fList:
            FileLine = line.split( )
            if FileLine[0] == b'facet':
                N = vec(float(FileLine[2]), float(FileLine[3]), float(FileLine[4]))
            elif FileLine[0] == b'vertex':
                vs.append( vertex(pos=vec(float(FileLine[1]), float(FileLine[2]), float(FileLine[3])), normal=N, color=color.white) )
                if len(vs) == 3:
                    tris.append(triangle(vs=vs))
                    vs = []
                    
    return compound(tris)

if __name__ == '__main__':
    file_dir = "src/three_d_sim/models/"
    # part = stl_to_triangles(file_dir + 'airliner/airbus-a320--1/Airbus_A320__Before_Scale_Up_ascii.STL')
    # part = stl_to_triangles(file_dir + 'airliner/airbus-a320-cfd-1.snapshot.7/samolot_ascii.stl')
    part = stl_to_triangles(file_dir + "convert_stl/Part1.stl")
    part.size *= 200
    part.pos = vec(250,0,0)
    part.color = color.orange