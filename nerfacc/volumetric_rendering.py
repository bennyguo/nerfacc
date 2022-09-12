import math
from typing import Callable, Tuple

import torch

from .cuda import (  # ComputeWeight,; VolumeRenderer,; ray_aabb_intersect,
    ray_marching,
    volumetric_rendering_steps,
)
from .utils import ray_aabb_intersect, volumetric_accumulate, volumetric_weights


def volumetric_rendering(
    query_fn: Callable,
    rays_o: torch.Tensor,
    rays_d: torch.Tensor,
    scene_aabb: torch.Tensor,
    scene_occ_binary: torch.Tensor,
    scene_resolution: Tuple[int, int, int],
    render_bkgd: torch.Tensor = None,
    render_n_samples: int = 1024,
    render_est_n_samples: int = None,
    render_step_size: int = None,
    **kwargs,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """A *fast* version of differentiable volumetric rendering."""
    device = rays_o.device
    if render_bkgd is None:
        render_bkgd = torch.ones(3, device=device)

    rays_o = rays_o.contiguous()
    rays_d = rays_d.contiguous()
    scene_aabb = scene_aabb.contiguous()
    scene_occ_binary = scene_occ_binary.contiguous()
    render_bkgd = render_bkgd.contiguous()

    n_rays = rays_o.shape[0]
    if render_step_size is None:
        # Note: CPU<->GPU is not idea, try to pre-define it outside this function.
        render_step_size = (
            (scene_aabb[3:] - scene_aabb[:3]).max() * math.sqrt(3) / render_n_samples
        )

    # get packed samples from ray marching & occupancy check.
    with torch.no_grad():
        t_min, t_max = ray_aabb_intersect(rays_o, rays_d, scene_aabb)

        (
            packed_info,
            frustum_origins,
            frustum_dirs,
            frustum_starts,
            frustum_ends,
        ) = ray_marching(
            # rays
            rays_o,
            rays_d,
            t_min,
            t_max,
            # density grid
            scene_aabb,
            scene_resolution,
            scene_occ_binary,
            # sampling
            render_step_size,
        )

        frustum_positions = (
            frustum_origins + frustum_dirs * (frustum_starts + frustum_ends) / 2.0
        )
        steps_counter = packed_info[:, -1].sum(0, keepdim=True)

    # compat the samples thru volumetric rendering
    with torch.no_grad():
        densities = query_fn(
            frustum_positions, frustum_dirs, only_density=True, **kwargs
        )
        compact_packed_info, compact_selector = volumetric_rendering_steps(
            packed_info.contiguous(),
            frustum_starts.contiguous(),
            frustum_ends.contiguous(),
            densities.contiguous(),
        )
        compact_frustum_positions = frustum_positions[compact_selector]
        compact_frustum_dirs = frustum_dirs[compact_selector]
        compact_frustum_starts = frustum_starts[compact_selector]
        compact_frustum_ends = frustum_ends[compact_selector]
        compact_steps_counter = compact_packed_info[:, -1].sum(0, keepdim=True)

    # network
    compact_query_results = query_fn(
        compact_frustum_positions, compact_frustum_dirs, **kwargs
    )
    compact_rgbs, compact_densities = compact_query_results[0], compact_query_results[1]

    # accumulation
    compact_weights, compact_ray_indices, alive_ray_mask = volumetric_weights(
        compact_packed_info,
        compact_frustum_starts,
        compact_frustum_ends,
        compact_densities,
    )
    accumulated_color = volumetric_accumulate(
        compact_weights, compact_ray_indices, compact_rgbs, n_rays
    )
    accumulated_weight = volumetric_accumulate(
        compact_weights, compact_ray_indices, None, n_rays
    )
    accumulated_depth = volumetric_accumulate(
        compact_weights,
        compact_ray_indices,
        (compact_frustum_starts + compact_frustum_ends) / 2.0,
        n_rays,
    )

    accumulated_depth = torch.clip(accumulated_depth, t_min[:, None], t_max[:, None])
    accumulated_color = accumulated_color + render_bkgd * (1.0 - accumulated_weight)

    return (
        accumulated_color,
        accumulated_depth,
        accumulated_weight,
        alive_ray_mask,
        steps_counter,
        compact_steps_counter,
    )
