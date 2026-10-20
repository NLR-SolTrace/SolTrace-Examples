"""
nsttf example function based approach
TODO: class based with PySolTrace
"""

import os, sys
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

from pysoltrace import api, dot_h, math_utils
import pysoltrace.soltrace_constants as _STC
import pysoltrace.soltrace_structs as _STS
import pysoltrace.soltrace_json as stJSON
from pysoltrace.point import Point
from pysoltrace.cst_templates import ArbitraryHeliostat

"""NSTTF information"""
DNI = 930 # [W/m^2]
LATITUDE  = 35.962278    # [deg], NSTTF original tower latitude (approximate)
LONGITUDE = -106.5122622 # [deg], NSTTF original tower longitude (approximate)
TZ        = 'MST'
TZINFO    = ZoneInfo("America/Denver")
NSTTF_LOC = _STS.sun_location(LATITUDE, LONGITUDE, -7.0)

"""
convert between (+x: west, +y: zenith, +z: north)
            and (+x: east, +y: north,  +z: zenith)
"""
CONVERT_COORDS = np.array([[-1., 0., 0.],
                           [ 0., 0., 1.],
                           [ 0., 1., 0.]])

# file set up
current_dir = Path(__file__).parent
json_f      = current_dir / 'nsttf.json'
data_dir    = current_dir / 'nsttf_data'
coords_f    = data_dir / 'coordinates.csv'
ids_f       = data_dir / 'ids.csv'
canting_dir = data_dir / 'canting'

################################
# set up optical property sets #
################################

def add_optical_property_sets(stapi: api, ) -> dict[str, 
                                               tuple[int, tuple[_STS.optical_properties_set, 
                                                                _STS.optical_properties_face, 
                                                                _STS.optical_properties_face]]]:
    optical_property_sets = {}

    # TODO: make date classes genuinely expect str and the normal IntEnum -> convert on .ctype
    rec_set  = _STS.optical_properties_set(b'receiver',
                                           1.1, 1.1,
                                           _STC.optical_interaction.REFLECTION.value)   
    rec_face = _STS.optical_properties_face(0, 0, .95, .2,
                                            _STC.optical_error_dist.GAUSSIAN.value)
    rec_id = stapi.data.optic.add(rec_set, rec_face, rec_face)
    optical_property_sets['receiver'] = (rec_id, (rec_set, rec_face, rec_face))

    helio_set   = _STS.optical_properties_set(b'heliostat',
                                              1.1, 1.1,
                                              _STC.optical_interaction.REFLECTION.value)
    helio_front = _STS.optical_properties_face(0, 0.885, 1.2, .05,
                                               _STC.optical_error_dist.GAUSSIAN.value)
    helio_back  = _STS.optical_properties_face(0, 0, 1.2, .05,
                                               _STC.optical_error_dist.GAUSSIAN.value)
    helio_id = stapi.data.optic.add(helio_set, helio_front, helio_back)
    optical_property_sets['heliostat'] = (helio_id, (helio_set, helio_front, helio_back))

    ap_set   = _STS.optical_properties_set(b'aperture',
                                           1.1, 1.1,
                                           _STC.optical_interaction.REFLECTION.value)
    ap_front = _STS.optical_properties_face(1, 0.5, 523.6, 0.1,
                                            _STC.optical_error_dist.GAUSSIAN.value)
    ap_back  = _STS.optical_properties_face(1, 0, 523.6, 0.1,
                                            _STC.optical_error_dist.GAUSSIAN.value)
    ap_id = stapi.data.optic.add(ap_set, ap_front, ap_back)
    optical_property_sets['aperture'] = (ap_id, (ap_set, ap_front, ap_back))

    tower_set  = _STS.optical_properties_set(b'tower',
                                             1.1, 1.1,
                                             _STC.optical_interaction.REFLECTION.value)
    tower_face = _STS.optical_properties_face(1, 0, 0.95, 0.2,
                                              _STC.optical_error_dist.GAUSSIAN.value)
    tower_id = stapi.data.optic.add(tower_set, tower_face, tower_face)
    optical_property_sets['tower'] = (tower_id, (tower_set, tower_face, tower_face))

    snout_set   = _STS.optical_properties_set(b'snout',
                                              1.1, 1.1,
                                              _STC.optical_interaction.REFLECTION.value)
    snout_front = _STS.optical_properties_face(0, 0.2, 0.95, 0.2,
                                               _STC.optical_error_dist.GAUSSIAN.value)
    snout_back  = _STS.optical_properties_face(0, 0, 0.95, 0.2,
                                               _STC.optical_error_dist.GAUSSIAN.value)
    snout_id = stapi.data.optic.add(snout_set, snout_front, snout_back)
    optical_property_sets['snout'] = (snout_id, (snout_set, snout_front, snout_back))

    return optical_property_sets

################
# set up tower #
################

def add_tower(stapi: api, optical_id: int) -> tuple[int, _STS.element]:
    # TODO: move ctype wrappers to a new
    # NOTE: maybe make position and aim double[3]? avoid people knowing about unpacking
    """
    element_args = (double[3], double[3], double, default True, default False) # maybe just directly as function args
    ap_surf = (type_a, type_s, params_a, params_s)
    data.element.add(element_args, aperture/surface, optical_id)
    """
    tower_args = _STS.element([0, 0, 30.05],
                              [0, 1, 30.05],
                              0, True, False)
    tower_geom = _STS.geometry([10, 60.1], 
                               [],
                                _STC.aperture.RECTANGLE.value, 
                               _STC.surface.FLAT.value)
    tower_id = stapi.data.element.add(tower_args, optical_id, tower_geom)
    return (tower_id, tower_args)
########################
# set up G3P3 receiver #
########################

g3p3_stage_pos = np.array([-40, 8.5, 44.8177])
g3p3_stage_aim = np.array([0,   122, 44.8177])
g3p3_unstager = math_utils.get_unstager(g3p3_stage_pos, g3p3_stage_aim, 0)

G3P3_TARGET = g3p3_unstager([0, 0, 0.662347])

G3P3_GROUP = 0
def add_G3P3(stapi: api, aperture_optical_id: int, snout_optical_id: int) -> dict[str, tuple[int, _STS.element]]:
    """add G3P3 elements 
    
    elements added:
        aperture
        tunnel bottom, east, west, top
        shield northeast, north, northwest, east, west, southeast, south, southwest
    """
    # reused geometries
    two_by_two = _STS.geometry([2, 2], [],
                               _STC.aperture.RECTANGLE.value, 
                               _STC.surface.FLAT.value)
    three_ish_by_two = _STS.geometry([3.3, 2], [],
                                     _STC.aperture.RECTANGLE.value, 
                                     _STC.surface.FLAT.value)
    two_by_one_ish = _STS.geometry([2, 1.75], [],
                                   _STC.aperture.RECTANGLE.value, 
                                   _STC.surface.FLAT.value)
    
    g3p3 = {}

    # aperture
    ap_el_args = _STS.element(*G3P3_TARGET,
                              *g3p3_unstager([0, 1, 0.662347]),
                              0, True, False,
                              G3P3_GROUP)
    ap_el_geom = _STS.geometry([1.32475, 1.32475], 
                               [],
                               _STC.aperture.RECTANGLE.value, 
                               _STC.surface.FLAT.value)
    ap_id = stapi.data.element.add(ap_el_args, aperture_optical_id, ap_el_geom)
    g3p3['aperture'] = (ap_id, ap_el_args)

    # tunnel bottom
    tb_el_args = _STS.element(g3p3_unstager([0, 0, 0]),
                              g3p3_unstager([0, 0.608432, 0.793606]),
                              0, True, False,
                              G3P3_GROUP)
    tb_el_geom = _STS.geometry([0.662347, 0, -0.662347, 0, -1.65, -0.945053, 1.65, -0.945053], 
                               [],
                               _STC.aperture.IRREGULAR_QUADRILATERAL.value, 
                               _STC.surface.FLAT.value)
    tb_id = stapi.data.element.add(tb_el_args, snout_optical_id, tb_el_geom)
    g3p3['tunnel bottom'] = (tb_id, tb_el_args)

    # tunnel east
    te_el_args = _STS.element(g3p3_unstager([0.662347, 0, 0]),
                              g3p3_unstager([0.057569, 0.796394, 0]),
                              0, True, False,
                              G3P3_GROUP)
    te_el_geom = _STS.geometry([0, 1.32475, -1.24012, 1.175, -1.24012, -0.575, 0, 0], 
                               [],
                               _STC.aperture.IRREGULAR_QUADRILATERAL.value, 
                               _STC.surface.FLAT.value)
    te_id = stapi.data.element.add(te_el_args, snout_optical_id, te_el_geom)
    g3p3['tunnel east'] = (te_id, te_el_args)

    # tunnel west
    tw_el_args = _STS.element(g3p3_unstager([-0.662347, 0, 0]),
                              g3p3_unstager([-0.057569, 0.796394, 0]),
                              0, True, False,
                              G3P3_GROUP)
    tw_el_geom = _STS.geometry([1.24012, 1.175, 0, 1.32475, 0, 0, 1.24012, -0.575], 
                               [],
                               _STC.aperture.IRREGULAR_QUADRILATERAL.value, 
                               _STC.surface.FLAT.value)
    tw_id = stapi.data.element.add(tw_el_args, snout_optical_id, tw_el_geom)
    g3p3['tunnel west'] = (tw_id, tw_el_args)

    # tunnel top
    tt_el_args = _STS.element(g3p3_unstager([0, 0, 1.32475]),
                              g3p3_unstager([0, 0.195795, 0.344105]),
                              0, True, False,
                              G3P3_GROUP)
    tt_el_geom = _STS.geometry([0.662347, 0, -0.662347, 0, -1.65, -0.764803, 1.65, -0.764803], 
                               [],
                               _STC.aperture.IRREGULAR_QUADRILATERAL.value, 
                               _STC.surface.FLAT.value)
    tt_id = stapi.data.element.add(tt_el_args, snout_optical_id, tt_el_geom)
    g3p3['tunnel top'] = (tt_id, tt_el_args)

    # shield northeast, uses two_by_two
    sne_el_args = _STS.element(g3p3_unstager([2.65, 0.75, 2.175]),
                               g3p3_unstager([2.65, 1.75, 2.175]),
                               0, True, False,
                               G3P3_GROUP)
    sne_id = stapi.data.element.add(sne_el_args, snout_optical_id, two_by_two)
    g3p3['shield northeast'] = (sne_id, sne_el_args)

    # shield north, uses three_ish_by_two
    sn_el_args = _STS.element(g3p3_unstager([0, 0.75, 2.175]),
                              g3p3_unstager([0, 1.75, 2.175]),
                              0, True, False,
                              G3P3_GROUP)
    sn_id = stapi.data.element.add(sn_el_args, snout_optical_id, three_ish_by_two)
    g3p3['shield north'] = (sn_id, sn_el_args)

    # shield northwest, uses two_by_two
    snw_el_args = _STS.element(g3p3_unstager([-2.65, 0.75, 2.175]),
                               g3p3_unstager([-2.65, 1.75, 2.175]),
                               0, True, False,
                               G3P3_GROUP)
    snw_id = stapi.data.element.add(snw_el_args, snout_optical_id, two_by_two)
    g3p3['shield northwest'] = (snw_id, snw_el_args)

    # shield east, uses two_by_one_ish
    se_el_args = _STS.element(g3p3_unstager([2.65, 0.75, 0.375]),
                              g3p3_unstager([2.65, 1.75, 0.245313]),
                              0, True, False,
                              G3P3_GROUP)
    se_id = stapi.data.element.add(se_el_args, snout_optical_id, two_by_one_ish)
    g3p3['shield east'] = (se_id, se_el_args)

    # shield west, uses two_by_one_ish
    sw_el_args = _STS.element(g3p3_unstager([-2.65, 0.75, 0.375]),
                              g3p3_unstager([-2.65, 1.75, 0.245313]),
                              0, True, False,
                              G3P3_GROUP)
    sw_id = stapi.data.element.add(sw_el_args, snout_optical_id, two_by_one_ish)
    g3p3['shield west'] = (sw_id, sw_el_args)

    # shield southeast, uses two_by_two
    sse_el_args = _STS.element(g3p3_unstager([2.65, 0.75, -1.575]),
                               g3p3_unstager([2.65, 1.75, -1.575]),
                               0, True, False,
                               G3P3_GROUP)
    sse_id = stapi.data.element.add(sse_el_args, snout_optical_id, two_by_two)
    g3p3['shield southeast'] = (sse_id, sse_el_args)

    # shield south, uses three_ish_by_two
    ss_el_args = _STS.element(g3p3_unstager([0, 0.75, -1.575]),
                              g3p3_unstager([0, 1.75, -1.575]),
                              0, True, False,
                              G3P3_GROUP)
    ss_id = stapi.data.element.add(ss_el_args, snout_optical_id, three_ish_by_two)
    g3p3['shield south'] = (ss_id, ss_el_args)

    # shield southwest, uses two_by_two
    ssw_el_args = _STS.element(g3p3_unstager([-2.65, 0.75, -1.575]),
                               g3p3_unstager([-2.65, 1.75, -1.575]),
                               0, True, False,
                               G3P3_GROUP)
    ssw_id = stapi.data.element.add(ssw_el_args, snout_optical_id, two_by_two)
    g3p3['shield southwest'] = (ssw_id, ssw_el_args)

    return g3p3

# measurement plane
# curtain

########################
# Solar 1 target setup #
########################

SOLAR_1_TARGET  = [5.65, 4.25, 64.54]
target_aim      = [5.65, 100, 64.54] # looking directly north
SOLAR_1_GROUP   = G3P3_GROUP + 1

def add_solar_1(stapi: api, optical_id: int) -> tuple[int, _STS.element]:
    # create element arguments object
    solar_1_el_args = _STS.element(SOLAR_1_TARGET, 
                                   target_aim,
                                   0, True, False,
                                   SOLAR_1_GROUP)
    # 2x2 [m] square, flat has no parameters
    solar_1_el_grom = _STS.geometry([2, 2], [],
                                    _STC.aperture.RECTANGLE.value, 
                                    _STC.surface.FLAT.value)
    # add element arguments, including optical property id and geometry
    solar_1_id = stapi.data.element.add(solar_1_el_args, optical_id, solar_1_el_grom)
    return (solar_1_id, solar_1_el_args)

# heliostat and facet information
PED_HEIGHT = 4.02           # [m],   heliostat pedistal height
TRACK_ERR  = 0.0005         # [rad], heliostat tracking error
PIV_OFFSET = 0.1778         # [m],   facet pivot offset
RECT_AP    = 1.2192         # [m],   facet side length
PARA_SURF  = 0.0034203      # [m],   parabolic focal length
CANT_ERR   = 0.0017         # [rad], facet canting error

# read in and combine coords and ids
coords_file = open(coords_f)
ids_file = open(ids_f)

# coordinates files has x-y as ground plane
coord, id = coords_file.readline(), ids_file.readline()
# first coord has weird first 3 characters
coord = coord[3:]

HELIOSTATS: list[ArbitraryHeliostat] = []

HELIOSTAT_GROUP = SOLAR_1_GROUP + 1
# TODO: add element.set_name()
while len(coord):
    temp = [*map(float, coord.split(','))]

    h = ArbitraryHeliostat(id[1:-1], temp, SOLAR_1_TARGET, [0, 0, 1000], TRACK_ERR, HELIOSTAT_GROUP)

    canting_f = canting_dir / f'{h.name}_Off_Axis_Canting_Details_TowerTop_Target.csv'

    f = open(canting_f)
    canting_details = np.genfromtxt(f, delimiter=',', skip_header=1)
    canting_details = np.array([
        canting_details[:, 0],
        canting_details[:, 1],
        canting_details[:, 2],
        canting_details[:, 3] + PIV_OFFSET,
        canting_details[:, 6],
        canting_details[:, 7],
        canting_details[:, 8],
    ]).T
    f.close()

    h.add_facets_local(canting_details,
                       -1,
                       _STC.aperture.RECTANGLE.value, [RECT_AP, RECT_AP],
                       _STC.surface.PARABOLA.value, [PARA_SURF, PARA_SURF],
                       CANT_ERR)

    HELIOSTATS.append(h)

    coord, id = coords_file.readline(), ids_file.readline()

coords_file.close()
ids_file.close()

def add_heliostats(stapi: api,
                   optical_id: int,
                   target: np.array,
                   sun: np.array) -> dict[str, list[tuple[int, _STS.element]]]:
    heliostats = {}
    for h in HELIOSTATS:
        # set optical property to heliostat
        h.set_optical_property(optical_id)
        # set the heliostats target (in global coordinates)
        h.set_target_global(target)
        # recalculate facet positions based on solar position
        h.reaim(sun)
        # add heliostat's facets' elements and track information
        heliostats[h.name] = h.add(stapi)
    return heliostats

def make_NSTTF(stapi: api, sun_pos: np.ndarray, use_G3P3: bool = True):
    # add optical properties to simulation data 
    OPTICAL = add_optical_property_sets(stapi)

    # get ids that were assigned
    RECEIVER_OPTICAL_REF  = OPTICAL['receiver'][0]
    HELIOSTAT_OPTICAL_REF = OPTICAL['heliostat'][0]
    APERTURE_OPTICAL_REF  = OPTICAL['aperture'][0]
    TOWER_OPTICAL_REF     = OPTICAL['tower'][0]
    SNOUT_OPTICAL_REF     = OPTICAL['snout'][0]

    return {
        # add tower element to cast shadow
        'tower': add_tower(stapi, TOWER_OPTICAL_REF),
        # add heliostats aiming at G3P3 or Solar 1 based on 
        # toggle argument, and based on solar position passed
        **add_heliostats(stapi,
                         HELIOSTAT_OPTICAL_REF,
                         G3P3_TARGET if use_G3P3 else SOLAR_1_TARGET,
                         sun_pos),
        # add G3P3 or solar 1 elements based on toggle 
        'G3P3': add_G3P3(stapi, APERTURE_OPTICAL_REF, SNOUT_OPTICAL_REF)
                         if use_G3P3 else
                         None,
        'solar 1': add_solar_1(stapi, RECEIVER_OPTICAL_REF)
                   if not use_G3P3 else
                   None,
    }

# debugging plotting utils
def _plot_projection(ax, pairs, axis_pair, labels):
    """Draw a single 2D projection (quiver plot) onto the given axes.
 
    axis_pair: tuple of indices into the 3D point, e.g. (0, 1) for X-Y.
    labels: tuple of axis label strings, e.g. ("X", "Y").
    """
    i, j = axis_pair
 
    starts_i, starts_j = [], []
    vecs_i, vecs_j = [], []
 
    for start, end in pairs:
        starts_i.append(start[i])
        starts_j.append(start[j])
        vecs_i.append(end[i] - start[i])
        vecs_j.append(end[j] - start[j])
 
    starts_i = np.array(starts_i)
    starts_j = np.array(starts_j)
    vecs_i = np.array(vecs_i)
    vecs_j = np.array(vecs_j)
 
    ax.quiver(
        starts_i, starts_j, vecs_i, vecs_j,
        angles="xy", scale_units="xy", scale=1,
        color="steelblue", width=0.003,
        headwidth=4, headlength=5, alpha=0.85,
    )
 
    # Include both start and end points when setting axis limits so
    # every arrow is fully visible, with a little padding.
    all_i = np.concatenate([starts_i, starts_i + vecs_i])
    all_j = np.concatenate([starts_j, starts_j + vecs_j])
    if len(all_i) > 0:
        pad_i = max((all_i.max() - all_i.min()) * 0.05, 1.0)
        pad_j = max((all_j.max() - all_j.min()) * 0.05, 1.0)
        ax.set_xlim(all_i.min() - pad_i, all_i.max() + pad_i)
        ax.set_ylim(all_j.min() - pad_j, all_j.max() + pad_j)
 
    ax.set_xlabel(labels[0])
    ax.set_ylabel(labels[1])
    ax.set_title(f"{labels[0]}-{labels[1]} projection")
    # ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, linestyle="--", alpha=0.4)
 
 
def plot_all_projections(pairs, show=True, save_prefix=None):
    """Create three separate figures: X-Y, Y-Z, and X-Z projections of
    the given list of (start, end) 3D point pairs.
 
    Parameters
    ----------
    pairs : list of ((x1,y1,z1), (x2,y2,z2))
    show : bool -- whether to call plt.show() at the end
    save_prefix : str or None -- if given, each figure is saved as
        "<save_prefix>_xy.png", "<save_prefix>_yz.png", "<save_prefix>_xz.png"
    """
    projections = [
        ((0, 1), ("X", "Y"), "xy"),
        ((1, 2), ("Y", "Z"), "yz"),
        ((0, 2), ("X", "Z"), "xz"),
    ]
 
    figures = []
    for axis_pair, labels, tag in projections:
        fig, ax = plt.subplots(figsize=(7, 7))
        _plot_projection(ax, pairs, axis_pair, labels)
        fig.tight_layout()
        figures.append(fig)
        if save_prefix:
            fig.savefig(f"{save_prefix}_{tag}.png", dpi=150)
 
    # if show:
    #     plt.show()
 
    return figures

def plot_heat_map(fig, ax, hits, w: float = 1):
    xs = hits['loc_x'].to_numpy()
    zs = hits['loc_z'].to_numpy()
    bin_x = math_utils.freedman_diaconis_np(xs)
    bin_z = math_utils.freedman_diaconis_np(zs)
    bins = max(bin_x, bin_z)

    _, _, _, im = ax.hist2d(xs, zs, bins=bins, cmap='YlOrRd', weights=w*np.ones(len(hits['loc_x'])))
    solar_1_x, solar_1_y, solar_1_z = NSTTF['solar 1'][1].xyz
    ax.scatter(solar_1_x, solar_1_z, marker='x', label='Target(s)', s=40)

    ax.set_xlabel('x')
    ax.set_ylabel('z')
    ax.set_title('Receiver Flux Map')
    ax.set_aspect('equal')
    x_bin_len = (xs.max() - xs.min()) / bins
    z_bin_len = (zs.max() - zs.min()) / bins

    fig.colorbar(im, ax=ax, label=f'W per ({x_bin_len:.3f} x {z_bin_len:.3f})')

if __name__ == '__main__':
    """init api"""
    stapi = api()
    print('Initialized api')

    """
    set up simulation parameters
    
    defaults:
        number_of_rays:           int  =   1,000,000
        max_number_of_rays:       int  = 100,000,000
        include_sun_shape_errors: bool = True
        include_optical_errors:   bool = True
    
    override by passing a keyword argument 
    to _STS.simulation_parameters
    NOTE: if using NATIVE runner decrease the number of rays to ~10,000
    """

    # create simulation parameters
    sim_params = _STS.simulation_parameters(latitude=LATITUDE, longitude=LONGITUDE) # , number_of_rays=1000
    # set simulation parameters
    stapi.parameters.set(sim_params)
    print(f'Set simulation parameters:\n{sim_params}')

    """
    set up sun for simulation

    dot_h usually references structs defined in stapi_v2.cpp
    however the solar calculator methods are defined in solar_position_calculator.hpp
    
    available methods: LEGACY, DUFFIE, SOLPOS, SPA_ORIGINAL, SPA
    """
    calc = dot_h.SolarPositionCalculationMethod.SPA

    # NOTE: change time that is simulated
    #       (year, month, day, hour, minute, second)
    dt   = _STS.sun_datetime(2025, 6, 20, 12)

    # api.data.sun.vector returns unit vector so multiply
    # by 1000 to place sun plane above geometry
    sun_pos = 1000 * stapi.data.sun.vector(calc, NSTTF_LOC, dt)
    # using Buie sun shape with CSR = .05
    # 0 as first arg signifies that it's not a user defined sun shape
    buie = _STS.sun(0, *sun_pos, .05, _STC.sun_shape.BUIE_CSR.value)
    # add sun shape
    stapi.data.sun.add(buie)
    print(f'Added sun: {buie}')

    # create NSTTF geometry based on sun position
    # (i.e., need to set up sun first to aim heliostats)
    NSTTF = make_NSTTF(stapi, sun_pos, False)
    print('Added NSTTF geometry')
   
    # save data as SolTrace JSON
    stapi.data.json.dump(json_f)
    print(f'Dumped data into SolTrace JSON: {json_f.resolve()}')

    """
    set up simulation runner

    available runners in dot_h.st_runner_type_t IntEnum:
    EMBREE, OPTIX, NATIVE
    """
    runner_type = dot_h.st_runner_type_t.OPTIX
    stapi.runner.setup(runner_type)
    
    # run simulation and report simulation results
    print(f'Running {runner_type.name.title()} simulation...')
    stapi.runner.run()
    stapi.runner.report()

    print(f'Simulated {len(stapi.result)} intersections.')

    # create DataFrame of the results for easier manipulation
    results = pd.DataFrame(stapi.result.get())
    print(results)
    # calc power_per_ray if dni is passed
    _, _, area, nsunrays = stapi.result.sun_stats()
    dni = 1000

    power_per_ray = area / nsunrays * dni # [W/ray]

    # get rays that intersected target
    hits = results[results['element_map'] == NSTTF['solar 1'][0]]

    # set up plot parameters
    mpl.rcParams['font.size'] = 22
    mpl.rcParams['figure.figsize'] = [16, 9]
    plt.style.use('seaborn-v0_8-colorblind')

    # make and show plots
    fig, ax = plt.subplots(1, 1)
    plot_heat_map(fig, ax, hits, power_per_ray)
    
    plt.show()

    # trying to debug gui thing, i think its that i did add a stage
    # stapi.data.element.add(_STC.element(0, -10, 60, 0, 1, 60, 0, True, False, _STC.aperture.RECTANGLE.value, _STC.surface.FLAT.value),
    #                        RECEIVER_OPTICAL_REF, [1200, 1200], [])

    # pairs = [
    #     ([el.x, el.y, el.z], [el.ax, el.ay, el.az])
    #     for _, el in G3P3.values()
    # ]
    # pairs.append(([solar_1_el_args.x, solar_1_el_args.y, solar_1_el_args.z], [solar_1_el_args.ax, solar_1_el_args.ay, solar_1_el_args.az]))

    # plot_all_projections(pairs)
