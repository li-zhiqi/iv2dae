#!/usr/bin/python3
import re, sys
import collada as dae
import numpy as np
#log = print
def log(*args):
    pass

_sep_pat = 'Separator\s*\{\s*(.*)\s*}'
_unit_pat = 'Units\s*\{\s*units\s*([^\}\s]*)\s*\}\s*'
_main_pat = '''\
(Material\s*\{
    \s*diffuseColor\s*(.*)\s*
    \s*\}
)?\
\s*Separator\s*\{\s*
    \s*Normal\s*\{\s*
        \s*vector\s*\[([0-9+-.e,\s]+)\]
    \s*\}
    \s*NormalBinding\s*\{\s*
        \s*value\s*([\w_]+)
    \s*\}
    \s*Coordinate[3,4]\s*\{\s*
        \s*point\s*\[([0-9+-.e,\s]+)\]
    \s*\}
    \s*FaceSet\s*\{\s*
        \s*numVertices\s*\[([0-9+-.e,\s]+)\]
    \s*\}
\s*}'''

_SCALE = 1
def dae_parse_normal_vectors(normal_vectors, id_):
    normal_vectors_list = normal_vectors.split(',')
    num_normal_vectors = len(normal_vectors_list)
    dim_normal_vectors = len(normal_vectors_list[0].split())
    assert(dim_normal_vectors == 3)
    normal_vectors_ = []
    for vector in normal_vectors_list:
        for n in vector.split():
            normal_vectors_.append(float(n)*_SCALE)
    normal_source = dae.source.FloatSource("normal_source_{0}".format(id_),
            np.array(normal_vectors_), ('X', 'Y', 'Z'))
    log('normal vector size {0}'.format(len(normal_vectors_)))
    return normal_source, num_normal_vectors
def dae_parse_vertices(vertices, id_):
    vertices_list = vertices.split(',')
    num_vertices = len(vertices_list)
    dim_vertices = len(vertices_list[0].split())
    assert(dim_vertices == 3)
    vertices_ = []
    for v in vertices_list:
        for n in v.split():
            vertices_.append(float(n)*_SCALE)
    vertices_source = dae.source.FloatSource("vertices_source_{0}".format(id_),
            np.array(vertices_), ("X", "Y", "Z"))
    log('vertices size {0}'.format(len(vertices_)))
    return vertices_source, num_vertices
def dae_parse_faceset(faceset, id_):
    faceset_list = faceset.split(',')
    num_faceset = len(faceset_list)
    faceset_ = []
    for n in faceset_list:
        faceset_.append(int(n))
        assert(faceset_[-1] == 3)
    return faceset_, num_faceset
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('iv2dae input.iv output.dae')
        sys.exit(0)
    iv_file_name = sys.argv[1]
    dae_file_name = sys.argv[2]
    iv_file = open(iv_file_name).read()
    m = re.search(_sep_pat, iv_file, re.DOTALL)
    if m is None:
        log('Parse Error\n')
    top_level = m.group(1)
    m = re.search(_unit_pat, top_level, re.DOTALL)
    UNIT = m.group(1).strip()
    if UNIT == "MILLIMETERS":
        _SCALE = 0.001
    log('using scale ', _SCALE)
    main_pat_ = re.compile(_main_pat)
    start = 0
    dae_obj = dae.Collada()
    material_node = None
    effect_id = 0
    material_id = 0
    id_ = 0
    nodes = []
    while True: 
        m = main_pat_.search(top_level, start)
        if m is None:
            break
        start = m.end()
        if m.group(1) is not None:
            material = m.group(2)
            color = [float(x) for x in material.strip().split()]
            effect_id_str = 'effect{0}'.format(effect_id) 
            dae_effect = dae.material.Effect(effect_id_str, 
                    [], 'phong', diffuse=color)
            dae_obj.effects.append(dae_effect)
            effect_id += 1
            dae_material = dae.material.Material("material{0}".format(material_id),
                    "material", dae_effect)
            material_node = dae.scene.MaterialNode("materialref{0}".format(material_id),
                    dae_material, inputs=[])
            dae_obj.materials.append(dae_material)
            material_id += 1
        geometry_id_str = 'geometry{0}'.format(id_)
        normal_vectors = m.group(3)
        normal_source, num_normal_vectors = dae_parse_normal_vectors(normal_vectors, id_)
        vertices = m.group(5)
        vertices_source, num_vertices = dae_parse_vertices(vertices, id_)
        dae_geometry = dae.geometry.Geometry(dae_obj, geometry_id_str,
                "geometry", [normal_source, vertices_source], [])
        geometry_node = dae.scene.GeometryNode(dae_geometry, [material_node])
        faceset = m.group(6)
        _, num_faceset = dae_parse_faceset(faceset, id_)
        assert(num_vertices == num_normal_vectors)
        assert(num_vertices == 3*num_faceset)
        input_list = dae.source.InputList()
        input_list.addInput(0, "VERTEX", '#vertices_source_{0}'.format(id_))
        input_list.addInput(1, "NORMAL", '#normal_source_{0}'.format(id_))
        indices = []
        for i in range(num_vertices):
            indices += [i, i]
        triangleset = dae_geometry.createTriangleSet(np.array(indices), 
                input_list, "material{0}".format(material_id-1))
        dae_geometry.primitives.append(triangleset)
        dae_obj.geometries.append(dae_geometry)
        node = dae.scene.Node("node{0}".format(id_), [geometry_node])
        nodes.append(node)
        id_ += 1
        log('>>> group {0} processed'.format(id_))
    dae_scene =  dae.scene.Scene("scene{0}".format(id_), nodes)
    dae_obj.scenes.append(dae_scene)
    dae_obj.scene = dae_scene
    dae_obj.write(dae_file_name)
    log("process ends, dae file written to ", dae_file_name)
