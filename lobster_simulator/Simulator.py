from typing import Dict
import copy
import pybullet as p
import pybullet_data
import json
import time as t

from pkg_resources import resource_stream

from lobster_simulator.robot.Lobster import Lobster
from lobster_simulator.simulation_time import SimulationTime
from enum import Enum, auto


class Models(Enum):
    SCOUT_ALPHA = auto()
    PTV = auto()


class Simulator:

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

        self.time: SimulationTime = SimulationTime(0)
        self.previous_update_time: SimulationTime = SimulationTime(0)
        self.previous_update_real_time: float = t.perf_counter()  # in seconds
        self.time_step: SimulationTime = SimulationTime(initial_microseconds=time_step)
        self.gui = gui

        self.cycle = 0

        if model == Models.SCOUT_ALPHA:
            model_config = 'scout-alpha.json'
        else:
            model_config = 'ptv.json'

        with resource_stream('lobster_simulator', f'data/{model_config}') as f:
            lobster_config = json.load(f)

        print(lobster_config)

        self.motor_mapping = {motor['name']: i for i, motor in enumerate(lobster_config['motors'])}

        print(self.motor_mapping)

        self.physics_client_id = -1
        if gui:
            self.physics_client_id = p.connect(p.GUI)
            self.simulator_frequency_slider = p.addUserDebugParameter("simulation frequency", 10, 1000,
                                                                      1 / self.time_step.microseconds)
            self.buoyancy_force_slider = p.addUserDebugParameter("buoyancyForce", 0, 1000, 550)

        else:
            self.physics_client_id = p.connect(p.DIRECT)

        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setTimeStep(self.time_step.seconds)
        p.setGravity(0, 0, -10)
        p.loadURDF("plane.urdf", [0, 0, -100])

        self.lobster = Lobster(lobster_config)

    def get_pybullet_id(self):
        return self.physics_client_id

    def get_time_in_seconds(self) -> float:
        return self.time.seconds

    def get_position(self):
        return self.lobster.get_position()

    def set_time_step(self, time_step: int):
        self.time_step = SimulationTime(time_step)
        p.setTimeStep(self.time_step.seconds)

    def set_rpm_motors(self, rpm_motors):
        self.lobster.set_desired_rpm_motors(rpm_motors)

    def set_thrust_motors(self, pwm_motors: Dict[str, float]):
        for (motor, value) in pwm_motors.items():
            self.lobster.set_desired_thrust_motor(self.motor_mapping[motor], value)

    def step_until(self, time: float):  # todo not sure if this was int or float
        """
        Execute steps until time (in seconds) has reached
        :param time:
        :return:
        """
        while (self.time + self.time_step).seconds <= time:
            self.do_step()

    def do_step(self):
        self.time.add_time_step(self.time_step.microseconds)
        if self.gui:
            self.lobster.set_buoyancy(p.readUserDebugParameter(self.buoyancy_force_slider))

            camera_info = p.getDebugVisualizerCamera()
            p.resetDebugVisualizerCamera(
                cameraDistance=camera_info[10],
                cameraYaw=camera_info[8],
                cameraPitch=camera_info[9],
                cameraTargetPosition=self.lobster.get_position()
            )

        self.lobster.update(self.time_step, self.time)

        p.stepSimulation()

        self.cycle += 1
        if self.cycle % 50 == 0:
            # print("test"+str(
            #     (self.time - self.previous_update_time).microseconds / seconds_to_microseconds(
            #         t.perf_counter() - self.previous_update_real_time)))
            self.previous_update_time = copy.copy(self.time)
            self.previous_update_real_time = t.perf_counter()
