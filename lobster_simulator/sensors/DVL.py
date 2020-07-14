from __future__ import annotations

import math
from typing import List, TYPE_CHECKING

from lobster_simulator.common.Calculations import *

if TYPE_CHECKING:
    from lobster_simulator.robot.AUV import AUV
from lobster_simulator.sensors.Sensor import Sensor
from lobster_simulator.simulation_time import *
from lobster_simulator.tools.Constants import *
from lobster_simulator.tools.DebugVisualization import DebugLine
from lobster_simulator.tools.Translation import *

SEAFLOOR_DEPTH = 100  # meters

MINIMUM_ALTITUDE = 0.05  # meters
MAXIMUM_ALTITUDE = 50  # meters

MINIMUM_TIME_STEP = SimulationTime(int(seconds_to_microseconds(1 / 26)))
MAXIMUM_TIME_STEP = SimulationTime(int(seconds_to_microseconds(1 / 4)))


class DVL(Sensor):

    def __init__(self, robot: AUV, position: Vec3, orientation: Quaternion, time_step: SimulationTime):
        self.beamVisualizers = [DebugLine(width=2) for _ in range(4)]

        angle = math.radians(22.5)
        beam_offset = 50 * math.tan(angle)

        self._previous_altitudes = [0, 0, 0, 0]
        self._previous_velocity = Vec3([0, 0, 0])

        print(beam_offset)

        self.beam_end_points = [
            Vec3([0, beam_offset, 50]),
            Vec3([0, -beam_offset, 50]),
            Vec3([beam_offset, 0, 50]),
            Vec3([-beam_offset, 0, 50])
        ]

        super().__init__(robot, position, orientation, time_step)

    # The dvl doesn't use the base sensor update method, because it has a variable frequency which is not supported.
    def update(self, time: SimulationTime):

        altitudes = list()
        bottom_locks = list()

        for i in range(4):
            # The beam end points are multiplied by 2, to be able to handle the transition between not having a lock and
            # having a lock
            local_endpoint = vec3_local_to_world(self._sensor_position, self._sensor_orientation,
                                                 2 * self.beam_end_points[i])
            world_endpoint = vec3_local_to_world(self._robot.get_position(), self._robot.get_orientation(),
                                                 local_endpoint)

            result = PybulletAPI.rayTest(self.get_position(), world_endpoint)

            if result[0] >= 0.5:
                self.beamVisualizers[i].update(self.get_position(), world_endpoint, color=[1, 0, 0])
            else:
                self.beamVisualizers[i].update(self.get_position(), world_endpoint, color=[0, 1, 0])

            altitudes.append(result[0] * 100)

        # TODO: check if the DVL indeed gives the altitude as the average of the 4 altitudes
        current_altitude = float(np.mean(altitudes))
        current_velocity = self._robot.get_velocity()
        bottom_lock = all(bottom_locks)

        self._queue = list()

        dt = time - self._previous_update_time
        real_values = self._get_real_values(dt)

        while self._next_sample_time <= time:
            interpolated_altitudes = list()
            for i in range(4):
                interpolated_altitudes.append(interpolate(x=self._next_sample_time.microseconds,
                                                          x1=self._previous_update_time.microseconds,
                                                          x2=time.microseconds,
                                                          y1=self._previous_altitudes[i],
                                                          y2=altitudes[i]))

            interpolated_velocity = interpolate_vec(x=self._next_sample_time.microseconds,
                                                    x1=self._previous_update_time.microseconds,
                                                    x2=time.microseconds,
                                                    y1=self._previous_velocity,
                                                    y2=current_velocity)

            average_interpolated_altitude = float(np.mean(interpolated_altitudes))

            interpolated_bottom_lock = all(i < MAXIMUM_ALTITUDE for i in interpolated_altitudes)

            self._queue.append(
                {
                    'time': self._time_step.milliseconds,
                    'vx': interpolated_velocity[X],
                    'vy': interpolated_velocity[Y],
                    'vz': interpolated_velocity[Z],
                    # TODO check whether the dvl gives the altitude straight down or relative to its orientation
                    # 'altitude': average_interpolated_altitude,
                    'altitude': SEAFLOOR_DEPTH - self.get_position()[Z],
                    'velocity_valid': interpolated_bottom_lock,
                    "format": "json_v1"
                }
            )


            # The timestep of the DVL depends on the altitude (higher altitude is lower frequency)
            time_step_micros = interpolate(average_interpolated_altitude,
                                           MINIMUM_ALTITUDE, MAXIMUM_ALTITUDE,
                                           MINIMUM_TIME_STEP.microseconds, MAXIMUM_TIME_STEP.microseconds)



            self._time_step = SimulationTime(int(time_step_micros))

            self._next_sample_time += self._time_step



        self._previous_update_time = SimulationTime(time.microseconds)
        self._previous_altitudes = altitudes
        self._previous_velocity = current_velocity

        if self._queue:
            print(self._queue)

    def _get_real_values(self, dt: SimulationTime) -> List[Vec3]:
        location = self._robot.get_position()

        distance_to_seafloor = SEAFLOOR_DEPTH - location[Z]

        velocity = self._robot.get_velocity()

    def get_position(self):
        return vec3_local_to_world(self._robot.get_position(), self._robot.get_orientation(), self._sensor_position)

    # def get_orientation(self):
