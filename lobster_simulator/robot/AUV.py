import numpy as np

from typing import List, Tuple

from pkg_resources import resource_filename

from lobster_simulator.common.Quaternion import Quaternion
from lobster_simulator.common.Vec3 import Vec3
from lobster_simulator.robot.buoyancyCylinder import BuoyancyCylinder
from lobster_simulator.sensors.DVL import DVL
from lobster_simulator.tools.PybulletAPI import PybulletAPI, Frame
from lobster_simulator.common.general_exceptions import ArgumentNoneError
from lobster_simulator.robot.Motor import Motor
from lobster_simulator.sensors.Accelerometer import Accelerometer
from lobster_simulator.sensors.DepthSensor import DepthSensor
from lobster_simulator.sensors.Gyroscope import Gyroscope
from lobster_simulator.sensors.Magnetometer import Magnetometer
from lobster_simulator.simulation_time import SimulationTime
from lobster_simulator.tools.DebugVisualization import DebugLine, DebugSphere
from lobster_simulator.tools.Translation import *


class AUV:

    def __init__(self, config):
        if config is None:
            raise ArgumentNoneError("config parameter should not be None")

        self._center_of_volume = Vec3(config['center_of_volume'])

        self.damping_matrix: np.ndarray = np.diag(config['damping_matrix_diag'])

        self._id = PybulletAPI.loadURDF(resource_filename("lobster_simulator", "data/Model_URDF.SLDASM.urdf"),
                                        Vec3([0, 0, 5]),
                                        PybulletAPI.getQuaternionFromEuler(Vec3([0, 0, 0])))

        self._buoyancy_cylinder = BuoyancyCylinder(self, 0.2, 1.5, 20)

        config_motors = config['motors']

        self._motors: List[Motor] = list()
        for i in range(len(config_motors)):
            self._motors.append(Motor.new_T200(self._id, config_motors[i]['name'],
                                               Vec3(config_motors[i]['position']),
                                               Vec3(config_motors[i]['direction'])))

        # Set damping to zero, because default is not zero
        PybulletAPI.changeDynamics(self._id, linearDamping=0.0, angularDamping=0.0)

        self._motor_debug_lines = list()
        self._motor_count = len(config_motors)
        self._rpm_motors = list()
        self._desired_rpm_motors: List[float] = list()
        for i in range(self._motor_count):
            self._rpm_motors.append(0)
            self._desired_rpm_motors.append(0.0)
            self._motor_debug_lines.append(DebugLine(self._motors[i]._position, self._motors[i]._position,
                                                     parentIndex=self._id, color=[0, 0, 1]))

        self.up_indicator = DebugSphere(0.05, [1, 0, 0, 1])

        self._depth_sensor = DepthSensor(self, Vec3([1, 0, 0]), SimulationTime(4000))
        self._accelerometer = Accelerometer(self, Vec3([1, 0, 0]), SimulationTime(4000))
        self._gyroscope = Gyroscope(self, Vec3([1, 0, 0]), SimulationTime(4000))
        self._magnetometer = Magnetometer(self, Vec3([1, 0, 0]), SimulationTime(4000))
        self._dvl = DVL(self, Vec3([-.5, 0, 0.10]), SimulationTime(4000))

        self._max_thrust = 100
        # self._buoyancy: float = 55000

    # TODO: This should in the future be based on the volume of the robot.
    def set_buoyancy(self, value: float):
        """
        Sets the force of the buoyance that acts on the robot
        :param value: Bouyance force in Newtons.
        """
        self._buoyancy = value

    def set_desired_rpm_motors(self, desired_rpm_motors: List[float]):
        for i in range(len(desired_rpm_motors)):
            self._motors[i].set_desired_rpm(desired_rpm_motors[i])

    def set_desired_rpm_motor(self, index: int, desired_rpm: float):
        self._desired_rpm_motors[index] = desired_rpm

    def set_desired_thrust_motors(self, desired_thrusts: List[float]):
        for i in range(len(desired_thrusts)):
            self._motors[i].set_desired_thrust(desired_thrusts[i])

    def set_desired_thrust_motor(self, index: int, desired_thrust: float):
        self._motors[index].set_desired_thrust(desired_thrust)

    def update(self, dt: SimulationTime, time: SimulationTime):
        """
        Updates the UUV by the specified time.
        :param dt: dt in microseconds
        :param time: time in microseconds
        """
        lobster_pos, lobster_orn = self.get_position_and_orientation()

        self._depth_sensor.update(time, dt)
        self._accelerometer.update(time, dt)
        self._gyroscope.update(time, dt)
        self._magnetometer.update(time, dt)
        self._dvl.update(time, dt)

        self._buoyancy_cylinder._update()

        PybulletAPI.rayTest(lobster_pos, lobster_pos + Vec3([0, 0, 200]))

        for i in range(self._motor_count):
            self._motors[i].update(dt.microseconds)

        # Apply forces for the  facing motors
        for i in range(self._motor_count):
            self._motors[i].apply_thrust()

            # Update debug lines in a max frequency. Check the first line if it can be updated.
            if self._motor_debug_lines[0].can_update():
                for i in range(self._motor_count):
                    self._motor_debug_lines[i].update(self._motors[i]._position,
                                                      self._motors[i]._position
                                                      + self._motors[i]._direction * self._motors[i].get_thrust() / 100,
                                                      self._id)

        self.up_indicator.update_position(
            vec3_local_to_world(self.get_position(), self.get_orientation(), Vec3([-.5, 0, 0.10])))

        # # Apply the buoyancy force
        # self.apply_force(self._center_of_volume, Vec3([0, 0, -self._buoyancy]), relative_direction=False)

        self.apply_damping()

    def get_position_and_orientation(self) -> Tuple[Vec3, Quaternion]:
        """
        Gets both the position and the orientation of the robot.
        :return: Tuple with the position and the orientation.
        """
        return PybulletAPI.getBasePositionAndOrientation(self._id)

    def get_position(self) -> Vec3:
        """
        Position of the robot.
        :return: Vec3 with the position.
        """
        position, _ = self.get_position_and_orientation()
        return position

    def get_orientation(self) -> Quaternion:
        """
        Gives the orientation of the robot in the world frame.
        :return: Orientation as a quaternion.
        """
        _, orientation = self.get_position_and_orientation()
        return orientation

    def get_velocity(self) -> Vec3:
        """
        Gets the linear velocity of the Robot in the World frame.
        """
        return PybulletAPI.getBaseVelocity(self._id)[0]

    def get_angular_velocity(self):
        return PybulletAPI.getBaseVelocity(self._id)[1]

    def apply_force(self, force_pos: Vec3, force: Vec3, relative_direction: bool = True) -> None:
        """
        Applies a force to the robot (should only be used for testing purposes).
        :param force_pos: Position of the acting force, given in the local frame
        :param force: Force vector
        :param relative_direction: Determines whether or not the force is defined in the local or world frame.
        """

        if not relative_direction:
            # If the force direction is given in the world frame, it should be rotated to the local frame
            force = vec3_rotate_vector_to_local(self.get_orientation(), force)

        # Apply the force in the local frame
        PybulletAPI.applyExternalForce(self._id, force, force_pos, Frame.LINK_FRAME)

    def set_position_and_orientation(self, position: Vec3 = None, orientation: Quaternion = None) -> None:
        """
        Sets the position and/or the orientation of the robot (should only be used for testing purposes).
        :param position: Position
        :param orientation: Orientation
        """
        if position is None:
            position = self.get_position()
        if orientation is None:
            orientation = self.get_orientation()

        PybulletAPI.resetBasePositionAndOrientation(self._id, position, orientation)

    def set_velocity(self, linear_velocity: Vec3 = None, angular_velocity: Vec3 = None, local_frame=False) -> None:
        """
        Sets the linear and/or angular velocity of the robot (should only be used for testing purposes).
        :param linear_velocity: The linear velocity that the robot should have.
        :param angular_velocity: The angular velocity that the robot should have.
        :param local_frame: Whether the velocities are given in the local or world frame.
        """
        if linear_velocity is None:
            linear_velocity = self.get_velocity()
        if angular_velocity is None:
            angular_velocity = self.get_angular_velocity()

        if local_frame:
            linear_velocity = vec3_rotate_vector_to_world(self.get_orientation(), linear_velocity)
            angular_velocity = vec3_rotate_vector_to_world(self.get_orientation(), angular_velocity)

        PybulletAPI.resetBaseVelocity(self._id, linear_velocity, angular_velocity)

    def apply_damping(self):
        """
        Applies damping to the robot on its linear and angular velocity.
        See https://docs.lobster-robotics.com/scout/robots/scout-alpha/scout-simulator-model
        """

        velocity = vec3_rotate_vector_to_local(self.get_orientation(), self.get_velocity())
        angular_velocity = vec3_rotate_vector_to_local(self.get_orientation(), self.get_angular_velocity())

        damping = -np.dot(self.damping_matrix, np.concatenate((velocity.array, angular_velocity.array)))

        # Multiply the damping for now to get slightly more accurate results
        damping *= 10

        linear_damping_force = Vec3(damping[:3])
        angular_damping_torque = Vec3(damping[3:])

        PybulletAPI.applyExternalForce(self._id, forceObj=linear_damping_force, posObj=Vec3([0, 0, 0]),
                                       frame=Frame.LINK_FRAME)
        PybulletAPI.applyExternalTorque(self._id, torqueObj=angular_damping_torque, frame=Frame.LINK_FRAME)
