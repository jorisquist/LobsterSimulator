import pybullet as p
import numpy as np
import math

from typing import List

from pkg_resources import resource_filename

from lobster_simulator.common.general_exceptions import ArgumentNoneError
from lobster_simulator.robot.Motor import Motor
from lobster_simulator.sensors.Accelerometer import Accelerometer
from lobster_simulator.sensors.DepthSensor import DepthSensor
from lobster_simulator.sensors.Gyroscope import Gyroscope
from lobster_simulator.sensors.IMU import IMU
from lobster_simulator.sensors.Magnetometer import Magnetometer
from lobster_simulator.simulation_time import SimulationTime
from lobster_simulator.tools.DebugLine import DebugLine


class Lobster:

    def __init__(self, config):
        if config is None:
            raise ArgumentNoneError("config parameter should not be None")

        self.center_of_volume = config['center_of_volume']

        self.id = p.loadURDF(resource_filename("lobster_simulator", "data/Model_URDF.SLDASM.urdf"),
                             [0, 0, 0],
                             # p.getQuaternionFromEuler([math.pi / 2, 0, 0]))
                             p.getQuaternionFromEuler([0, 0, 0]))

        config_motors = config['motors']

        self.motors: List[Motor] = list()
        for i in range(len(config_motors)):
            self.motors.append(Motor.new_T200(self.id, config_motors[i]['name'],
                                              np.array(config_motors[i]['position']),
                                              np.array(config_motors[i]['direction'])))

        # p.changeDynamics(self.id, -1, linearDamping=0.9, angularDamping=0.9)
        p.changeDynamics(self.id, -1, linearDamping=0, angularDamping=0)

        self.motor_debug_lines = list()
        self._motor_count = len(config_motors)
        self.rpm_motors = list()
        self.desired_rpm_motors = list()
        for i in range(self._motor_count):
            self.rpm_motors.append(0)
            self.desired_rpm_motors.append(0)
            self.motor_debug_lines.append(DebugLine(self.motors[i].position, self.motors[i].position))

        self.buoyancySphereShape = p.createVisualShape(p.GEOM_SPHERE, radius=0.2, rgbaColor=[1, 0, 0, 1])
        self.buoyancyPointIndicator = p.createMultiBody(0, -1, self.buoyancySphereShape, [0, 0, 0],
                                                        useMaximalCoordinates=0)

        self.depth_sensor = DepthSensor(self, [1, 0, 0], None, SimulationTime(4000))
        # self.imu = IMU(self.id, [0, 0, 0], [0, 0, 0, 0], SimulationTime(1000))
        self.accelerometer = Accelerometer(self, [1, 0, 0], None, SimulationTime(4000))
        self.gyroscope = Gyroscope(self, [1, 0, 0], None, SimulationTime(4000))
        self.magnetometer = Magnetometer(self, [1, 0, 0], None, SimulationTime(4000))

        self.max_thrust = 100
        self.buoyancy = 550

    def set_buoyancy(self, value):
        self.buoyancy = value

    def set_desired_rpm_motors(self, desired_rpm_motors):
        for i in range(len(desired_rpm_motors)):
            self.motors[i].set_desired_rpm(desired_rpm_motors[i])

    def set_desired_rpm_motor(self, index, desired_rpm):
        self.desired_rpm_motors[index] = desired_rpm

    def set_desired_thrust_motors(self, desired_thrusts):
        for i in range(len(desired_thrusts)):
            self.motors[i].set_desired_thrust(desired_thrusts[i])

    def set_desired_thrust_motor(self, index: int, desired_thrust: float):
        self.motors[index].set_desired_thrust(desired_thrust)

    def update(self, dt: SimulationTime, time: SimulationTime):
        """

        :param dt: dt in microseconds
        :param time: time in microseconds
        :return:
        """
        lobster_pos, lobster_orn = self.get_position_and_orientation()

        # for value in self.imu.get_all_values():
        #     [print(f'{value}, ', end='') for value in self.imu._get_real_values(dt)]
        #     [print(f'{value}, ', end='') for value in value]
        #     print()

        self.depth_sensor.update(time)
        self.accelerometer.update(time)
        self.gyroscope.update(time)
        self.magnetometer.update(time)

        print(self.accelerometer.get_accelerometer_value())


        for i in range(self._motor_count):
            self.motors[i].update(dt.microseconds)

        # Apply forces for the  facing motors
        for i in range(self._motor_count):
            self.motors[i].apply_thrust()
            self.motor_debug_lines[i].update(self.motors[i].position,
                                             self.motors[i].position
                                             + self.motors[i].direction * self.motors[i].get_thrust() / 100,
                                             self.id)

        # Determine the point where the buoyancy force acts on the robot
        buoyancy_force_pos = np.reshape(np.array(p.getMatrixFromQuaternion(lobster_orn)), (3, 3)).dot(
            np.array(self.center_of_volume)) + lobster_pos

        # Apply the buoyancy force
        p.applyExternalForce(objectUniqueId=self.id, linkIndex=-1,
                             forceObj=[0, 0, self.buoyancy], posObj=np.array(buoyancy_force_pos), flags=p.WORLD_FRAME)

    def get_position_and_orientation(self):
        return p.getBasePositionAndOrientation(self.id)

    def get_position(self):
        position, _ = self.get_position_and_orientation()
        return position

    def get_orientation(self):
        _, orientation = self.get_position_and_orientation()
        return orientation

    def get_velocity(self):
        return p.getBaseVelocity(self.id)[0]

    def get_rotational_velocity(self):
        return p.getBaseVelocity(self.id)[1]
