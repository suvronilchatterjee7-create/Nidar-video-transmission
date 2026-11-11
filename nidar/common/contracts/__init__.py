"""Typed contracts between modules: docs/INTERFACES.md made executable.

One normalised contract per stream type, plus adapters for anything that does not speak it.
[ADIAT-inspired: streaming/contracts.py, adapters.py]
"""
from nidar.common.contracts.base import SCHEMA_VERSION, DroneId, ProcessResult, StageTimings, run_isolated
from nidar.common.contracts.gcs import GcsDisplayModel, MissionPhase
from nidar.common.contracts.link import (
    GcsCommand,
    LinkStatus,
    OperatorAction,
    Radio,
    ResourcePlan,
    SnrReport,
)
from nidar.common.contracts.mission import GeoPolygon, MissionDefinition, MissionFileParser
from nidar.common.contracts.perception import Detection, GeotagObservation, SurvivorStatus, SurvivorTrack
from nidar.common.contracts.state import DroneState, DroneStatus, EstimatorHealth
from nidar.common.contracts.swarm import (
    AssignmentCostTerms,
    AuctionAssignment,
    DeliveryEvent,
    DensityKernel,
    PartitionCell,
    PartitionUpdate,
)
from nidar.common.contracts.video import (
    AnalogueBlock,
    CertifiedFloorDesign,
    FloorBlock,
    FloorController,
    GopHeader,
    MetadataBlock,
    PilotPlan,
    SnrPredictor,
    VideoDecoder,
    VideoEncoder,
    VideoFrame,
    VideoQualityReport,
    VideoSource,
)

__all__ = [
    "SCHEMA_VERSION", "DroneId", "ProcessResult", "StageTimings", "run_isolated",
    "GcsDisplayModel", "MissionPhase",
    "GcsCommand", "LinkStatus", "OperatorAction", "Radio", "ResourcePlan", "SnrReport",
    "GeoPolygon", "MissionDefinition", "MissionFileParser",
    "Detection", "GeotagObservation", "SurvivorStatus", "SurvivorTrack",
    "DroneState", "DroneStatus", "EstimatorHealth",
    "AssignmentCostTerms", "AuctionAssignment", "DeliveryEvent", "DensityKernel", "PartitionCell",
    "PartitionUpdate",
    "AnalogueBlock", "CertifiedFloorDesign", "FloorBlock", "FloorController", "GopHeader", "MetadataBlock",
    "PilotPlan", "SnrPredictor", "VideoDecoder", "VideoEncoder", "VideoFrame", "VideoQualityReport",
    "VideoSource",
]
