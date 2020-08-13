from lobster_common.quaternion import Quaternion
from lobster_common.vec3 import Vec3

import time

from pkg_resources import resource_filename

from lobster_simulator.common.pybullet_api import PybulletAPI


class DebugLine:
    """
    Class used to create a debug line in the GUI.
    """
    _MIN_UPDATE_INTERVAL = 0.03

    def __init__(self, from_location: Vec3 = None, to_location: Vec3 = None, width=5, color=None, parentIndex=-1):
        if color is None:
            color = [1, 1, 1]

        self.parentIndex = parentIndex

        if from_location is None:
            from_location = Vec3([0, 0, 0])

        if to_location is None:
            to_location = Vec3([0, 0, 0])

        self.from_location = from_location
        self.to_location = to_location

        self._width = width
        self._color = color

        self._id = -1
        self._id = self._update_debug_line()
        self._latest_update_time = 0

    def remove(self):
        PybulletAPI.removeUserDebugItem(self._id)

    def update(self, from_location: Vec3 = None, to_location: Vec3 = None, frame_id: int = None, color=None) -> None:
        """
        Update the pose of the debug line.
        """
        if from_location:
            self.from_location = from_location
        if to_location:
            self.to_location = to_location

        if not self.can_update():
            return
        if frame_id:
            self.parentIndex = frame_id

        if color:
            self._color = color

        self._id = self._update_debug_line()
        self._latest_update_time = time.time()

    def can_update(self) -> bool:
        """
        Checks if time has passed to allow a new debug line to be created.
        """
        return time.time() - self._latest_update_time > self._MIN_UPDATE_INTERVAL

    def _update_debug_line(self) -> int:
        return PybulletAPI.addUserDebugLine(lineFromXYZ=self.from_location,
                                            lineToXYZ=self.to_location,
                                            lineWidth=self._width,
                                            lineColorRGB=self._color,
                                            parentObjectUniqueId=self.parentIndex,
                                            replaceItemUniqueId=self._id)


class DebugSphere:

    def __init__(self, radius, rgba_color):
        self.sphereId = PybulletAPI.createVisualSphere(radius, rgba_color)

    def update_position(self, position: Vec3):
        PybulletAPI.resetBasePositionAndOrientation(self.sphereId, posObj=position)


class DebugScout:

    def __init__(self, pos: Vec3 = None):
        if not pos:
            pos = Vec3([0, 0, 0])

        self.id = PybulletAPI.loadURDF(resource_filename("lobster_simulator",
                                                                "data/scout-alpha-visual.urdf"), pos)

    def set_position_and_orientation(self, position: Vec3, orientation: Quaternion):
        PybulletAPI.resetBasePositionAndOrientation(self.id, posObj=position, ornObj=orientation)