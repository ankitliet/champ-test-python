"""
    module for Maintenance State
"""
from enum import Enum


class MaintenanceState(Enum):
    """
    function return maintenance state
    """
    ACTIVE = 'active'
    INACTIVE = 'inactive'
