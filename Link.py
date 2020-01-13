import pybullet as p


class Link:

    def __init__(self,
                 mass=0,
                 collision_shape=-1,
                 visual_shape=-1,
                 position=None,
                 orientation=None,
                 inertial_frame_position=None,
                 inertial_frame_orientation=None,
                 parent_index=0,
                 joint_type=p.JOINT_REVOLUTE,
                 joint_axis=None):

        if joint_axis is None:
            joint_axis = [0, 0, 1]
        if inertial_frame_orientation is None:
            inertial_frame_orientation = [0, 0, 0, 1]
        if inertial_frame_position is None:
            inertial_frame_position = [0, 0, 0]
        if orientation is None:
            orientation = [0, 0, 0, 1]
        if position is None:
            position = [0, 0, 0]

        self.mass = mass
        self.joint_axis = joint_axis
        self.joint_type = joint_type
        self.parent_index = parent_index
        self.inertial_frame_orientation = inertial_frame_orientation
        self.inertial_frame_position = inertial_frame_position
        self.orientation = orientation
        self.visualShape = visual_shape
        self.collisionShape = collision_shape
        self.position = position
