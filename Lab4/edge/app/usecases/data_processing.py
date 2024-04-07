#!/usr/bin/env python3
from app.entities.agent_data import AgentData
from app.entities.processed_agent_data import ProcessedAgentData

import numpy as np
from numpy.linalg import lstsq
import logging

logger = logging.getLogger()
RANGE_NORMAL = (14000, 18000)
RANGE_SMALL_PITS = ((12000, 14000), (18000, 20000))


def process_agent_data(agent_data: AgentData) -> ProcessedAgentData:
    """
        Process agent data and classify the state of the road surface.
        Parameters:
            agent_data (AgentData): Agent data that contains accelerometer, GPS, and timestamp.
        Returns:
            processed_data (ProcessedAgentData): Processed data containing the classified state of
    the road surface and agent data.
    """
    road_state = ""
    z_acceleration = agent_data.accelerometer.z
    if RANGE_NORMAL[0] < z_acceleration < RANGE_NORMAL[1]:
        road_state = "normal"
    elif any(range_[0] < z_acceleration < range_[1] for range_ in RANGE_SMALL_PITS):
        road_state = "small pits"
    else:
        road_state = "large pits"

    logging.info(f"Prediction: {road_state}, z_acceleration: {z_acceleration}")

    return ProcessedAgentData(road_state=road_state, agent_data=agent_data)
