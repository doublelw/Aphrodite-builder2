"""
Battery Management System (BMS) algorithms.

Implements core BMS functions for organic battery packs:
  - SOC (State of Charge) estimation
  - SOH (State of Health) tracking
  - Cell balancing strategies
  - Thermal management
  - Degradation modeling for organic batteries
"""
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum


class SOCMethod(Enum):
    COULOMB_COUNTING = "coulomb"
    OPEN_CIRCUIT_VOLTAGE = "ocv"
    KALMAN_FILTER = "kalman"
    ADAPTIVE = "adaptive"


@dataclass
class CellState:
    """Real-time state of a single battery cell."""
    cell_id: int
    voltage: float          # V
    current: float          # A (positive = charging)
    temperature: float      # C
    soc: float              # 0-1
    soh: float              # 0-1 (capacity retention)
    internal_resistance: float  # mOhm
    cycle_count: int = 0
    capacity_mAh: float = 0.0


@dataclass
class BMSConfig:
    """BMS configuration for organic battery pack."""
    n_cells_series: int = 4
    n_cells_parallel: int = 1
    cell_capacity_mAh: float = 250.0
    max_voltage: float = 4.2
    min_voltage: float = 2.5
    max_charge_current_C: float = 1.0  # C-rate
    max_discharge_current_C: float = 5.0
    max_temperature: float = 55.0
    min_temperature: float = -20.0
    balance_threshold_mV: float = 20.0
    organic_degradation_rate: float = 0.0002  # per cycle, organic batteries


class SOCEstimator:
    """
    State of Charge estimation for organic batteries.

    Supports multiple methods:
    - Coulomb counting (simple, drifts over time)
    - OCV lookup (needs rest period)
    - Extended Kalman Filter (most accurate)
    - Adaptive fusion (best for organic batteries)
    """

    def __init__(self, config: BMSConfig):
        self.config = config

    def coulomb_counting(self, soc_prev: float, current_A: float,
                         dt_hours: float) -> float:
        """Simple coulomb counting SOC update."""
        capacity_Ah = self.config.cell_capacity_mAh / 1000.0
        delta_soc = current_A * dt_hours / capacity_Ah
        return max(0.0, min(1.0, soc_prev + delta_soc))

    def ocv_to_soc(self, ocv: float, chemistry: str = "organic") -> float:
        """Convert open-circuit voltage to SOC using lookup curve."""
        # Simplified OCV-SOC curve for organic cathode
        # Real curves should be measured experimentally
        if chemistry == "organic":
            # Typical organic battery: 2.5V (0%) to 4.2V (100%)
            v_min = self.config.min_voltage
            v_max = self.config.max_voltage
            if ocv <= v_min:
                return 0.0
            if ocv >= v_max:
                return 1.0
            # Non-linear curve typical of organic electrodes
            normalized = (ocv - v_min) / (v_max - v_min)
            return normalized ** 0.8
        return 0.0

    def extended_kalman(self, state: CellState, voltage_measured: float,
                        current_measured: float, dt: float) -> float:
        """
        Extended Kalman Filter SOC estimation.

        State model: SOC(k+1) = SOC(k) - I*dt/Q + w
        Measurement: V = OCV(SOC) - I*R + v
        """
        # Prediction step
        capacity_Ah = self.config.cell_capacity_mAh / 1000.0
        soc_pred = state.soc - (current_measured * dt / 3600.0) / capacity_Ah

        # Innovation step
        v_predicted = self._soc_to_ocv(soc_pred) - current_measured * state.internal_resistance / 1000.0
        innovation = voltage_measured - v_predicted

        # Simple Kalman gain (simplified for clarity)
        k_gain = 0.1
        soc_updated = soc_pred + k_gain * innovation / (self.config.max_voltage - self.config.min_voltage)

        return max(0.0, min(1.0, soc_updated))

    def _soc_to_ocv(self, soc: float) -> float:
        """Inverse of ocv_to_soc."""
        v_min = self.config.min_voltage
        v_max = self.config.max_voltage
        return v_min + (v_max - v_min) * (soc ** (1.0 / 0.8))


class SOHTracker:
    """State of Health tracking and degradation modeling."""

    def __init__(self, config: BMSConfig):
        self.config = config

    def update_soh(self, soh_prev: float, cycle_count: int,
                   avg_temperature: float = 25.0) -> float:
        """
        Update SOH based on degradation model.

        Organic batteries typically degrade via:
        - Dissolution of active material in electrolyte
        - Side reactions at electrode surface
        - Structural changes during cycling
        """
        base_degradation = self.config.organic_degradation_rate

        # Temperature acceleration (Arrhenius-like)
        temp_factor = 1.0
        if avg_temperature > 40:
            temp_factor = 2.0 ** ((avg_temperature - 40) / 10.0)

        degradation = base_degradation * temp_factor

        return max(0.0, soh_prev - degradation)

    def remaining_cycles(self, soh: float, eol_threshold: float = 0.8) -> int:
        """Estimate remaining cycles before end of life."""
        remaining_soh = soh - eol_threshold
        if remaining_soh <= 0:
            return 0
        return int(remaining_soh / self.config.organic_degradation_rate)

    def capacity_fade_curve(self, initial_capacity: float,
                            n_cycles: int) -> List[Tuple[int, float]]:
        """Generate capacity fade prediction curve."""
        curve = []
        soh = 1.0
        for cycle in range(0, n_cycles + 1, 50):
            capacity = initial_capacity * soh
            curve.append((cycle, capacity))
            soh = self.update_soh(soh, cycle)
        return curve


class CellBalancer:
    """Cell balancing strategies for battery packs."""

    def __init__(self, config: BMSConfig):
        self.config = config

    def check_balance(self, cells: List[CellState]) -> List[dict]:
        """Check which cells need balancing."""
        voltages = [c.voltage for c in cells]
        v_max = max(voltages)
        v_min = min(voltages)
        v_avg = sum(voltages) / len(voltages)

        actions = []
        for cell in cells:
            diff = cell.voltage - v_avg
            if abs(diff) > self.config.balance_threshold_mV / 1000.0:
                actions.append({
                    "cell_id": cell.cell_id,
                    "action": "discharge" if diff > 0 else "charge",
                    "voltage": cell.voltage,
                    "deviation_mV": diff * 1000,
                })

        return actions

    def passive_balance(self, cells: List[CellState]) -> List[dict]:
        """Passive balancing: bleed high cells through resistor."""
        actions = []
        v_max = max(c.voltage for c in cells)

        for cell in cells:
            if cell.voltage > v_max - self.config.balance_threshold_mV / 1000.0:
                continue
            actions.append({
                "cell_id": cell.cell_id,
                "action": "bleed",
                "current_mA": 50,
                "target_voltage": v_max - self.config.balance_threshold_mV / 1000.0,
            })

        return actions


class ThermalManager:
    """Thermal management for organic battery packs."""

    # Organic batteries may have different thermal characteristics
    ORGANIC_SPECIFIC_HEAT = 1.2  # J/(g*K), lower than Li-ion
    ORGANIC_THERMAL_CONDUCTIVITY = 0.3  # W/(m*K)

    def __init__(self, config: BMSConfig):
        self.config = config

    def check_thermal(self, cells: List[CellState]) -> dict:
        """Check thermal status and recommend actions."""
        temps = [c.temperature for c in cells]
        t_max = max(temps)
        t_min = min(temps)
        t_avg = sum(temps) / len(temps)

        status = "normal"
        action = "none"

        if t_max > self.config.max_temperature:
            status = "critical"
            action = "reduce_current_and_activate_cooling"
        elif t_max > self.config.max_temperature - 10:
            status = "warning"
            action = "activate_cooling"
        elif t_min < self.config.min_temperature:
            status = "warning"
            action = "activate_heating"

        return {
            "status": status,
            "action": action,
            "max_temp": t_max,
            "min_temp": t_min,
            "avg_temp": t_avg,
            "delta_temp": t_max - t_min,
        }

    def estimate_heat_generation(self, current_A: float,
                                 internal_resistance_mOhm: float) -> float:
        """Estimate heat generation in Watts."""
        return current_A ** 2 * internal_resistance_mOhm / 1000.0
