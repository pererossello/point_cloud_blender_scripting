import bpy
import numpy as np


"""
CLEANUP of the scene before we start
"""
# Delete all objects in the scene
if bpy.data.objects:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

# delete all meshes
if bpy.data.meshes:
    for mesh in bpy.data.meshes:
        bpy.data.meshes.remove(mesh)

# delete all materials in the scene
if bpy.data.materials:
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)

# delete all gemoetry nodes
if bpy.data.node_groups:
    for group in bpy.data.node_groups:
        bpy.data.node_groups.remove(group)


"""
CREATE the reference object the point clouds will be copies of
GIVE it an emissive material
HIDE it from viewport and render
"""
# Make a sphere that will be our reference object for all the points in the point cloud
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.005, location=(0, 0, 0))
reference_object = bpy.context.object

# Give it an emissive material
emissive_material = bpy.data.materials.new(name="Emissive")
emissive_material.use_nodes = True
emissive_material.node_tree.nodes.clear()
emissive_material_output = emissive_material.node_tree.nodes.new(
    "ShaderNodeOutputMaterial"
)
emissive_material_emission = emissive_material.node_tree.nodes.new("ShaderNodeEmission")
emissive_material_emission.inputs["Strength"].default_value = 1
emissive_material_emission.inputs["Color"].default_value = (1, 0.1, 0.1, 1)
emissive_material.node_tree.links.new(
    emissive_material_output.inputs["Surface"],
    emissive_material_emission.outputs["Emission"],
)

# assign material to reference sphere
bpy.context.object.data.materials.append(emissive_material)

# Hide from render and viewport
bpy.context.object.hide_render = True
bpy.context.object.hide_set(True)

"""
CREATE the positions of the point clouds (generally you read these from data)
"""

# We create a uniform sphere of points

N = 10000  # number of points

pos_0 = np.random.rand(int(1.1 * N * 6 * np.pi), 3) * 2 - 1
r = np.linalg.norm(pos_0, axis=1)
# We have created a uniform cube and now we filter out the points that are outside the unit sphere
pos_0 = pos_0[r < 1][:N]

"""
GIVE each particle a trajectory
"""

T = 100  # number of time steps

positions = np.zeros((T, N, 3))
positions[0, :, :] = pos_0  # initial positions

# We just make them rotate around z axis
rho = np.linalg.norm(pos_0[:, :2], axis=1)
for i in range(1, T):
    phi = np.arctan2(pos_0[:, 1], pos_0[:, 0]) + i * 2 * np.pi / T
    positions[i, :, 0] = np.cos(phi) * rho
    positions[i, :, 1] = np.sin(phi) * rho
    positions[i, :, 2] = pos_0[:, 2]


"""
CREATE the point cloud
"""

mesh = bpy.data.meshes.new("PointCloud")
point_cloud = bpy.data.objects.new("PointCloudObject", mesh)
bpy.context.collection.objects.link(point_cloud)

mesh.from_pydata(positions[0, :, :], [], [])
mesh.update()


"""
MAKE the point cloud move
"""


def update_mesh(scene):
    frame_index = scene.frame_current - 0  # Assuming frame starts at 1 and indexes at 0

    if frame_index < len(positions):
        for i, vertex in enumerate(mesh.vertices):
            # Update vertex positions based on current frame
            vertex.co = positions[frame_index, i, :]
        mesh.update()


bpy.app.handlers.frame_change_post.append(update_mesh)

# Set start and end frames
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = T


"""
ADD the reference object to the points in point cloud
for this we use geometry nodes
"""

gn_modifier = point_cloud.modifiers.new(name="GeometryNodes", type="NODES")
gn_group = bpy.data.node_groups.new(name="PointCloudGeometry", type="GeometryNodeTree")

gn_group.inputs.new("NodeSocketGeometry", "Mesh")  # We need to create a socket
gn_group.outputs.new("NodeSocketGeometry", "Instance")  # We need to create a socket

output_node = gn_group.nodes.new("NodeGroupOutput")
input_node = gn_group.nodes.new("NodeGroupInput")
points_node = gn_group.nodes.new("GeometryNodeMeshToPoints")
instance_node = gn_group.nodes.new("GeometryNodeInstanceOnPoints")
object_info_node = gn_group.nodes.new("GeometryNodeObjectInfo")

input_node.location = (-400, 0)
output_node.location = (400, 0)
points_node.location = (-100, 0)
instance_node.location = (100, 0)
object_info_node.location = (-100, -200)

gn_group.links.new(input_node.outputs[0], points_node.inputs["Mesh"])
gn_group.links.new(instance_node.outputs[0], output_node.inputs["Instance"])
gn_group.links.new(points_node.outputs["Points"], instance_node.inputs["Points"])
object_info_node.inputs["Object"].default_value = reference_object
gn_group.links.new(
    object_info_node.outputs["Geometry"], instance_node.inputs["Instance"]
)

gn_modifier.node_group = gn_group


"""
ADD a camera
"""

bpy.ops.object.camera_add(location=(0, -6, 0), rotation=(np.pi / 2, 0, 0))
