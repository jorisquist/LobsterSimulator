import copy

import json
import time as t

from pkg_resources import resource_stream

from lobster_simulator.tools.PybulletAPI import PybulletAPI
from lobster_simulator.robot.UUV import UUV
from lobster_simulator.simulation_time import SimulationTime
from enum import Enum, auto


class Models(Enum):
    SCOUT_ALPHA = auto()
    PTV = auto()


class Simulator:
    robot = None

    def __init__(self, time_step: int, model=Models.SCOUT_ALPHA, config=None, gui=True):
        """
        Simulator
        :param time_step: duration of a step in microseconds
        :param config: config of the robot.
        :param gui: start the PyBullet gui when true
        """
        with resource_stream('lobster_simulator', 'data/config.json') as f:
            base_config = json.load(f)

        if config is not None:
            base_config.update(config)

        config = base_config

        self._time: SimulationTime = SimulationTime(0)
        self._previous_update_time: SimulationTime = SimulationTime(0)
        self._previous_update_real_time: float = t.perf_counter()  # in seconds
        self._time_step: SimulationTime = SimulationTime(initial_microseconds=time_step)

        self._cycle = 0

        PybulletAPI.initialize(self._time_step, gui)

        self._simulator_frequency_slider = PybulletAPI.addUserDebugParameter("simulation frequency", 10, 1000,
                                                                             1 / self._time_step.microseconds)
        self._buoyancy_force_slider = PybulletAPI.addUserDebugParameter("buoyancyForce", 0, 1000, 550)

        self._model = model
        self.create_robot(model)

    def get_time_in_seconds(self) -> float:
        return self._time.seconds

    def set_time_step(self, time_step: int):
        self._time_step = SimulationTime(time_step)
        PybulletAPI.setTimeStep(self._time_step)

    def step_until(self, time: float):
        """
        Execute steps until time (in seconds) has reached. The given time will never be exceeded, but could be slightly
        less than the specified time (at most 1 time step off).
        :param time: Time (in seconds) to which the simulator should run
        """
        while (self._time + self._time_step).seconds <= time:
            self.do_step()

    def do_step(self):
        self._time.add_time_step(self._time_step.microseconds)

        if PybulletAPI.gui():
            self.robot.set_buoyancy(PybulletAPI.readUserDebugParameter(self._buoyancy_force_slider))

        PybulletAPI.moveCameraToPosition(self.robot.get_position())

        self.robot.update(self._time_step, self._time)

        PybulletAPI.stepSimulation()

        self._cycle += 1
        if self._cycle % 50 == 0:
            # print("test"+str(
            #     (self.time - self.previous_update_time).microseconds / seconds_to_microseconds(
            #         t.perf_counter() - self.previous_update_real_time)))
            self._previous_update_time = copy.copy(self._time)
            self._previous_update_real_time = t.perf_counter()

    def get_robot(self):
        """
        Gets the current instance of the robot.
        :return: Robot instance
        """
        return self.robot

    def create_robot(self, model):
        """
        Creates a new robot based on the given model.
        :param model: Model of the robot. (Scout-alpha, PTV)
        """

        if model == Models.SCOUT_ALPHA:
            model_config = 'scout-alpha.json'
        else:
            model_config = 'ptv.json'

        with resource_stream('lobster_simulator', f'data/{model_config}') as f:
            lobster_config = json.load(f)

        self.robot = UUV(lobster_config)

    def reset_robot(self):
        """
        Resets the robot using the same configuration.
        """
        self.create_robot(self._model)
