from abc import ABC, abstractmethod
from typing import Optional, List

class BasePostProcessor(ABC):
    """
    Abstract Base Class for CNC Controller Dialects (Post-Processors).
    Encapsulates controller-specific G-Code syntax, safety headers, dwell formatting,
    and canned cycle support.
    """

    dialect_name: str = "base"
    supports_canned_cycles: bool = False

    def format_coord(self, axis: str, value: Optional[float], decimals: int = 3) -> str:
        """Formats an axis coordinate e.g. X10.000 or Z-5.250."""
        if value is None:
            return ""
        return f"{axis.upper()}{value:.{decimals}f}"

    @abstractmethod
    def format_header(
        self,
        units: str = "mm",
        absolute_mode: bool = True,
        feed_mode: str = "G94",
        plane: str = "G17",
        comment: Optional[str] = None,
    ) -> List[str]:
        """Generates safety header block."""
        pass

    @abstractmethod
    def format_tool_comment(self, tool_number: int, tool_name: str = "") -> List[str]:
        """Formats tool selection / manual tool change operator comment."""
        pass

    @abstractmethod
    def format_spindle_start(
        self,
        rpm: int,
        clockwise: bool = True,
        dwell_seconds: float = 0.0,
        spindle_type: str = "router",
        router_model: Optional[str] = "dewalt_611",
        router_dial: Optional[int] = None,
    ) -> List[str]:
        """Formats spindle/router ON command, operator dial comments, and optional spin-up dwell."""
        pass

    @abstractmethod
    def format_spindle_stop(self) -> List[str]:
        """Formats spindle OFF command."""
        pass

    @abstractmethod
    def format_rapid(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        comment: Optional[str] = None,
    ) -> str:
        """Formats G0 rapid motion."""
        pass

    @abstractmethod
    def format_linear(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        feed_rate: Optional[float] = None,
        comment: Optional[str] = None,
    ) -> str:
        """Formats G1 controlled linear motion."""
        pass

    @abstractmethod
    def format_dwell(self, seconds: float) -> str:
        """Formats G4 dwell command according to controller dialect."""
        pass

    @abstractmethod
    def format_footer(
        self,
        park_z: Optional[float] = None,
        park_x: Optional[float] = None,
        park_y: Optional[float] = None,
    ) -> List[str]:
        """Formats program termination block."""
        pass

    @abstractmethod
    def format_straight_drill(
        self,
        x: float,
        y: float,
        start_z: float,
        target_depth_z: float,
        retract_z: float,
        plunge_feed: float,
        dwell_seconds: float = 0.0,
        approach_clearance: float = 1.0,
    ) -> List[str]:
        """Formats a single straight-plunge hole drilling operation."""
        pass

    @abstractmethod
    def format_arc(
        self,
        clockwise: bool,
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        i: Optional[float] = None,
        j: Optional[float] = None,
        r: Optional[float] = None,
        feed_rate: Optional[float] = None,
        comment: Optional[str] = None,
    ) -> str:
        """Formats G2 (CW) or G3 (CCW) circular or helical arc motion."""
        pass

    @abstractmethod
    def format_peck_drill(
        self,
        x: float,
        y: float,
        start_z: float,
        target_depth_z: float,
        peck_depth: float,
        retract_z: float,
        plunge_feed: float,
        dwell_seconds: float = 0.0,
        approach_clearance: float = 1.0,
        peck_retract_type: str = "full_retract",
    ) -> List[str]:
        """Formats a peck drilling operation (expanded for Grbl, G83 for standard)."""
        pass

