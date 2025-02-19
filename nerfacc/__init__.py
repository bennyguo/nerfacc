"""
Copyright (c) 2022 Ruilong Li, UC Berkeley.
"""
import warnings

from .cdf import ray_resampling
from .contraction import ContractionType, contract, contract_inv
from .grid import Grid, OccupancyGrid, query_grid
from .intersection import ray_aabb_intersect
from .losses import distortion as loss_distortion
from .pack import pack_data, unpack_data, unpack_info
from .ray_marching import ray_marching, ray_marching_alpha
from .version import __version__
from .vol_rendering import (
    accumulate_along_rays,
    render_visibility,
    render_weight_from_alpha,
    render_weight_from_density,
    rendering,
    rendering_alpha,
)


# About to be deprecated
def unpack_to_ray_indices(*args, **kwargs):
    warnings.warn(
        "`unpack_to_ray_indices` will be deprecated. Please use `unpack_info` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return unpack_info(*args, **kwargs)


__all__ = [
    "__version__",
    "Grid",
    "OccupancyGrid",
    "query_grid",
    "ContractionType",
    "contract",
    "contract_inv",
    "ray_aabb_intersect",
    "ray_marching",
    "ray_marching_alpha",
    "accumulate_along_rays",
    "render_visibility",
    "render_weight_from_alpha",
    "render_weight_from_density",
    "rendering",
    "rendering_alpha",
    "pack_data",
    "unpack_data",
    "unpack_info",
    "ray_resampling",
    "loss_distortion",
    "unpack_to_ray_indices",
]
