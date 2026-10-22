import os
import numpy as np
import pandas as pd
import trimesh
import matplotlib.pyplot as plt
# import timeit

from api.pysoltrace import PySolTrace, Point

# Simulation global parameters
N_RAYS = 1.e7
REC_LENGTH_MULT = 5.5
REC_DISTANCE = 500.0    # [m] Distance from heliostat to receiver
REC_NX = 100            # Number of grid points along the x-axis for the receiver
REC_NY = 100            # Number of grid points along the y-axis for the receiver

PLOT_FLUX = False
PRINT_ST_RESULTS = False

def setup_soltrace(case: dict, use_avg_facet_norm: bool = True) -> dict:
    # Setup the PySolTrace environment
    ST = PySolTrace()

    #--- Create sun (using limb-darkened sun-shape)
    sun = ST.add_sun()
    sun.position = Point(0.0, 0.0, 100.0)   # Sun position directly overhead
    sun.shape = 'd'
    sun.sigma = 4.65
    # Limb-darkened sun-shape
    pts = np.linspace(0, 4.65, 26)
    intensity = np.maximum(1.0 - 0.5138*((pts/4.65)**4), 0.0)
    intensity[-1] = 0.0
    sun.user_intensity_table = [[pts[i], intensity[i]] for i in range(len(pts))]

    #--- Create optical property sets
    helio_optic = ST.add_optic("Heliostat")
    helio_optic.front.reflectivity = 1.0
    helio_optic.front.slope_error = 0.0     # Assume zero slope error
    helio_optic.front.spec_error = 0.0
    helio_optic.back.reflectivity = 0.0
    helio_optic.back.slope_error = 100.0
    helio_optic.back.spec_error = 0.0

    absorber = ST.add_optic("Absorber")
    absorber.front.reflectivity = 0.0
    absorber.front.slope_error = 0.0
    absorber.front.spec_error = 0.0
    absorber.back.reflectivity = 0.0
    absorber.back.slope_error = 0.0
    absorber.back.spec_error = 0.0

    #--- Create heliostat stage (Stage 0)
    mesh = trimesh.load_mesh(case['isolated_mesh_path'])
    centroid = mesh.centroid
    mesh.apply_translation(-centroid)  # translate the mesh to center it at the origin

    # For debugging orientation of the mesh relative to the tracking vector
    if False:
        # Initialize face colors with a default color (e.g., gray) for all faces
        default_color = np.array([200, 200, 200, 255], dtype=np.uint8)
        mesh.visual.face_colors = np.tile(default_color, (len(mesh.faces), 1))
        # Color a portion of the mesh for visualization (e.g., highlight the tracking vector direction)
        selected_faces = np.zeros(len(mesh.faces), dtype=bool)
        selected_faces[:800] = True  # example: select the first 10 faces for visualization
        # Apply a new color (e.g., red) to the selected portion
        highlight_color = np.array([255, 0, 0, 255], dtype=np.uint8)
        mesh.visual.face_colors[selected_faces] = highlight_color
        mesh.show(viewer='gl', flags={"axis": True})

    # Translate mesh to make the z-axis align with the tracking vector 
    #   i.e., facets are on the x-y plane (consistent with SolTrace elements)
    if use_avg_facet_norm:
        # Use the average facet normal as the tracking vector (removes wind-induced tracking error)
        tracking_vector = np.array([case['avg_facet_normal_x'], 
                                    case['avg_facet_normal_y'], 
                                    case['avg_facet_normal_z']])
        tracking_vector = tracking_vector / np.linalg.norm(tracking_vector)

        elevation_angle_deg = np.degrees(np.arcsin(tracking_vector[1]))  # Elevation angle from the y-component of the normal
        azimuth_angle_deg = np.degrees(np.arctan2(-tracking_vector[2], -tracking_vector[0]))
    else: # Use design tracking vector
        elevation_angle_deg = case['expected_elevation_angle_deg']
        azimuth_angle_deg = case['expected_azimuth_angle_deg']

    # Just reverse the rotations...
    # mesh.show(viewer='gl', flags={"axis": True})
    rot_matrix = trimesh.transformations.rotation_matrix(np.radians(azimuth_angle_deg), [0, 1, 0])
    mesh.apply_transform(rot_matrix)
    # mesh.show(viewer='gl', flags={"axis": True})
    rot_matrix = trimesh.transformations.rotation_matrix(np.radians(elevation_angle_deg), [0, 0, 1])
    mesh.apply_transform(rot_matrix)
    # mesh.show(viewer='gl', flags={"axis": True})
    rot_matrix = trimesh.transformations.rotation_matrix(np.radians(90), [0, 1, 0])
    mesh.apply_transform(rot_matrix)
    # mesh.show(viewer='gl', flags={"axis": True})


    if False:
        # Build local frame: z = tracking/expected vector
        up = np.array([0.0, 0.0, 1.0])
        if abs(np.dot(up, z_new)) > 0.999:  # tracking vector nearly vertical -> fall back to global y
            up = np.array([0.0, 1.0, 0.0])
        y_new = up - np.dot(up, z_new) * z_new
        y_new /= np.linalg.norm(y_new)
        x_new = np.cross(y_new, z_new)

        # Rotation mapping world coordinates into the local (x_new, y_new, z_new) frame
        to_local = np.eye(4)
        to_local[:3, :3] = np.vstack([x_new, y_new, z_new])
        mesh.apply_transform(to_local)
        # Apply an additional rotation to align the mesh with the desired orientation
        rot_matrix = trimesh.transformations.rotation_matrix(np.radians(-90), [0, 0, 1])
        mesh.apply_transform(rot_matrix)

    # Confirmed the mesh is correctly oriented and transformed - Debugging purposes
    # mesh.show(viewer='gl', flags={"axis": True})

    #---- Creating Heliostat Stage
    helio_stage = ST.add_stage()
    helio_stage.name = 'Heliostat'
    # TODO: set up stage orientation based on the local frame (x_new, y_new, z_new)
    # Maybe not needed... if we just use a straight on 

    # Adding backside elements for each submesh (to simulate a perfectly flat heliostat)
    submeshes = mesh.split(only_watertight=False)
    backing_area = 0.0
    backing = list()
    for submesh in submeshes:
        center = submesh.centroid
        submesh.apply_translation(-center)  # Translate the submesh so that its center is at the origin

        # Find bounds of submesh (i.e., facet)
        bounds = submesh.bounds
        width = bounds[1][0] - bounds[0][0]
        height = bounds[1][1] - bounds[0][1]
        depth = bounds[1][2] - bounds[0][2]

        # Add each triangle element
        element = helio_stage.add_element()
        element.position = Point(center[0], center[1], center[2] - depth * 2.0)
        element.aim = element.position + Point(0.0, 0.0, 1.0) * 1000.0  # Aim upwards
        element.zrot = 0.0
        element.aperture_rectangle(width - 0.001, height - 0.001) # NOTE: reduced slightly to avoid edge hits
        element.surface_flat()
        element.optic = helio_optic     # Applying heliostat optic for "ideal" case first
        element.enabled = True
        backing.append(element)
        backing_area += (width - 0.001) * (height - 0.001)

    #---- Adding the receiver stage 
    mesh_bounds = mesh.bounds
    rec_width = mesh_bounds[1][0] - mesh_bounds[0][0]
    rec_height = mesh_bounds[1][1] - mesh_bounds[0][1]
    depth = mesh_bounds[1][2] - mesh_bounds[0][2]
    # print(f"Mesh width: {rec_width:.5f} m, Mesh height: {rec_height:.5f} m, Mesh depth: {depth:.5f} m")

    rec_stage = ST.add_stage()
    rec_stage.name = 'Receiver'
    receiver = rec_stage.add_element()
    receiver.position = Point(0.0, 0.0, REC_DISTANCE)
    receiver.aperture_rectangle(round(rec_width*REC_LENGTH_MULT, 2), round(rec_height*REC_LENGTH_MULT, 2))
    receiver.surface_flat()
    receiver.optic = absorber
    receiver.enabled = True

    # ST.write_soltrace_input_file('test_sim_setup_process.stinput')
    # ---- Simulate baseline scenario (i.e., perfect flat surface)
    print("Simulating baseline scenario...")
    results = dict()
    results['receiver_aperture'] = receiver.aperture_params[0:2]
    results['ST_baseline'] = simulate_soltrace(ST, receiver, backing, backing_area, 
                                               print_results=PRINT_ST_RESULTS, plot_flux=PLOT_FLUX)
    assert abs(results['ST_baseline']['Intercept efficiency (%)'] - 100.0) < 1e-1, f"Intercept efficiency is {results['ST_baseline']['Intercept efficiency (%)']}"

    # ---- Simulate scenario with uniform slope error
    print("Simulating scenario with uniform slope error...")
    helio_optic.front.slope_error = case['slope_error_mean_weighted_mrad']
    results['ST_mean_slope_error'] = simulate_soltrace(ST, receiver, backing, backing_area, 
                                                       print_results=PRINT_ST_RESULTS, plot_flux=PLOT_FLUX)
    assert abs(results['ST_mean_slope_error']['Intercept efficiency (%)'] - 100.0) < 1e-1, f"Intercept efficiency is {results['ST_mean_slope_error']['Intercept efficiency (%)']}"
    helio_optic.front.slope_error = 0.0 

    # ----- Adding high-fidelity heliostat mesh
    # For debugging purposes, limit the number of faces
    MAX_FACE_COUNT = 100_000    
    # mesh.apply_scale(1.0)
    face_count = min(len(mesh.faces), MAX_FACE_COUNT)
    if len(mesh.faces) > MAX_FACE_COUNT:
        print(f"Limiting mesh faces to {MAX_FACE_COUNT} out of {len(mesh.faces)}")

    helio_elements = list()  # List to store heliostat elements
    last_percent = -1
    # Pull mesh data for faster access -> 100x speedup
    tri_centers = mesh.triangles_center
    face_normals = mesh.face_normals
    tri_vertices = mesh.vertices
    for face_index, face in enumerate(mesh.faces):
        if face_index >= MAX_FACE_COUNT:
            break

        element = helio_stage.add_element()
        # Set the position and aim of the SolTrace element based on the mesh face center and normal
        center = tri_centers[face_index]
        element.position = Point(center[0], center[1], center[2])
        normal = face_normals[face_index]
        element.aim = element.position + Point(normal[0], normal[1], normal[2]) * 100_000.

        # Aperture requires a bit of work to rotate z-axis with the face normal
        vertices = tri_vertices[face] - center
        z_axis = np.array([0.0, 0.0, 1.0])
        rotation_axis = np.cross(normal, z_axis)
        axis_length = np.linalg.norm(rotation_axis)
        if axis_length > 1e-8:
            rotation_axis /= axis_length
            rotation_angle = np.arccos(np.clip(np.dot(normal, z_axis), -1.0, 1.0))
            rot_matrix = trimesh.transformations.rotation_matrix(rotation_angle, rotation_axis)
            vertices = vertices @ rot_matrix[:3, :3].T

        element.aperture_irr_triangle(vertices[0][0], vertices[0][1],
                                      vertices[1][0], vertices[1][1],
                                      vertices[2][0], vertices[2][1])
        element.surface_flat()
        element.zrot = 0.0 # TODO: check this assumption
        element.optic = helio_optic
        element.enabled = True
        helio_elements.append(element)

        # Print progress for the current face
        processed = face_index + 1
        percent = processed * 100 // face_count
        if percent != last_percent:
            filled = percent * 30 // 100
            print(f"\rImporting Mesh to SolTrace: [{'#' * filled}{'-' * (30 - filled)}] {percent:3d}% ({processed}/{face_count})",
                  end="\n" if processed == face_count else "", flush=True)
            last_percent = percent

    # ---- Updating backing elements to absorbers ----
    # Making the backing elements absorbers to track ray hits (rays that leak past the heliostat mesh)
    for b in backing:
        b.optic = absorber

    # For debugging, .stinput file truncates input value (resulting in precisions loss with mesh small elements)
    # ST.write_soltrace_input_file('test_stl_process.stinput')

    print("Simulating scenario with mesh elements...")
    results['ST_mesh'] = simulate_soltrace(ST, receiver, helio_elements, mesh.area, 
                                           print_results=PRINT_ST_RESULTS, plot_flux=PLOT_FLUX)
    assert abs(results['ST_mesh']['Intercept efficiency (%)'] - 100.0) < 1e-1, f"Intercept efficiency is {results['ST_mesh']['Intercept efficiency (%)']}"

    # Confirm that backing elements have zero hit counts
    rayData = ST.raydata
    helio_stage = rayData[rayData['stage'] == 1]
    hit_rays = helio_stage[helio_stage['element'].isin([-(el.id+1) for el in backing])]['number']
    if len(hit_rays) > 0:
        print(f"#### WARNING: Backing elements received {len(hit_rays)} hits.")

    # Check the cumulative power of the three cases are equal
    assert abs(results['ST_mesh']['cumulative_power'].iloc[-1] - results['ST_baseline']['cumulative_power'].iloc[-1]) < 1e-1, "Cumulative power mismatch between mesh and baselinecases."
    assert abs(results['ST_mesh']['cumulative_power'].iloc[-1] - results['ST_mean_slope_error']['cumulative_power'].iloc[-1]) < 1e-1, "Cumulative power mismatch between mesh and mean slope error cases."

    return results

def simulate_soltrace(ST: PySolTrace, receiver, heliostat, helio_area,
                      print_results: bool = False, plot_flux: bool = False):
    # Run the SolTrace simulation
    ST.num_ray_hits = N_RAYS
    ST.max_rays_traced = 100 * N_RAYS
    ST.is_sunshape = True
    ST.is_surface_errors = True
    ST.dni = 1000.0
    print("Running SolTrace simulation...")
    res = 0
    run_count = 0
    while res == 0:
        if run_count > 0:
            if run_count > 3:
                raise RuntimeError("SolTrace simulation failed after multiple attempts.")
            print(f"Rerunning simulation, attempt #{run_count}")
        res = ST.run(123, as_power_tower = False, nthread = 20, no_callback=False, use_embree=True)
        run_count += 1

    print("Processing SolTrace results...")
    results = process_soltrace_results(ST, helio_area, fluxBinNx=REC_NX, fluxBinNy=REC_NY)
    encir_energy = encircled_energy(ST, receiver, heliostat)
    results.update(encir_energy)
    
    if print_results:
        print("Simulation Results:")
        for key, value in results.items():
            if isinstance(value, float):
                print(f"{key}: {value:.4f}")

    if plot_flux:
        ST.plot_flux(receiver, REC_NX, REC_NY)

    return results

def process_soltrace_results(PT: PySolTrace, fieldArea, fluxBinNx:int = 25, fluxBinNy:int = 25):
    """
    Returns a dictionary of results with the following keys:
        'Absorbed power (kW)'
        'Field efficiency (%)'
        'Max flux (kW/m^2)'
        'Average flux (kW/m^2)'
        'Peak concentration ratio (-)'
        'Average concentration ratio (-)'
        'Shadowing and cosine efficiency (%)'
        'Blocking efficiency (%)'
        'Reflection and attenuation efficiency (%)'
        'Intercept efficiency (%)'
        'Absorption efficiency (%)'
        'Field efficiency w/o receiver (%)'
        'flux_map (kW/m^2)'
    """
    rayData = PT.raydata

    results = {}
    rec_stage = rayData[rayData['stage'] == 2]
    # absorbed by the receiver
    abs_power = len(rec_stage[rec_stage['element'] == -1]) * PT.powerperray / 1.e3
    results['Absorbed power (kW)'] = abs_power
    results['Field efficiency (%)'] = abs_power * 100. / (fieldArea * PT.dni / 1.e3)

    flux_st = PT.bin_rays(PT.stages[-1].elements[-1], nx=fluxBinNx, ny=fluxBinNy)
    results['flux_map (kW/m^2)'] = flux_st / 1.e3
    results['Max flux (kW/m^2)'] = flux_st.max() / 1.e3
    results['Average flux (kW/m^2)'] = flux_st.mean() / 1.e3

    results['Peak concentration ratio (-)'] = flux_st.max() / PT.dni
    results['Average concentration ratio (-)'] = flux_st.mean() / PT.dni

    # Count rays using dataframe operations
    field_stage = rayData[rayData['stage'] == 1]
    nhin = field_stage['number'].nunique()      # Rays that hit the heliostat field

    ray_counts = field_stage['number'].value_counts()
    multi_hits = ray_counts[ray_counts > 1].index
    fieldMultiHits = field_stage[field_stage['number'].isin(multi_hits)]
    nhblock = len(fieldMultiHits[fieldMultiHits['element'] < 0])    # Rays blocked by heliostats after initial reflection

    single_hits = ray_counts[ray_counts == 1].index
    fieldSingleHits = field_stage[field_stage['number'].isin(single_hits)]
    nhabs = len(fieldSingleHits[fieldSingleHits['element'] < 0])    # Rays absorbed by heliostats

    rec_stage = rayData[rayData['stage'] == 2]
    nrin = len(rec_stage[(rec_stage['element'] == 1) | (rec_stage['element'] == -1)])   # Rays that hit the receiver
    nrabs = len(rec_stage[rec_stage['element'] == -1])              # Rays absorbed by the receiver
    nhout = nhin - nhblock - nhabs                                  # Rays that leave the heliostat field

    # NOTE: Ray counts must be multipled by the reflect_ratio value if not equal to 1

    # Calculate efficiency metrics
    Abox = (PT.sunstats['xmax'] - PT.sunstats['xmin']) * (PT.sunstats['ymax'] - PT.sunstats['ymin'])
    nsunrays = PT.sunstats['nsunrays']

    results['Shadowing and cosine efficiency (%)'] = nhin / nsunrays * Abox / fieldArea * 100.
    results['Blocking efficiency (%)'] = (1. - (nhblock / (nhin - nhabs))) * 100.
    results['Reflection and attenuation efficiency (%)'] = (nhin - nhabs) / nhin * 100.
    results['Intercept efficiency (%)'] = nrin / nhout * 100.
    results['Absorption efficiency (%)'] = nrabs / nrin * 100.
    results['Field efficiency w/o receiver (%)'] = (results['Field efficiency (%)'] / 100.) / (results['Absorption efficiency (%)'] / 100.) * 100.

    return results

def calculate_receiver_power(PT: PySolTrace, receiver, heliostat):
    """
    Calculates the power absorbed by the receiver

    :param PT: PySolTrace instance

    :return total absorbed power: [kWt]
    """
    rayData = PT.raydata
    if rayData.empty:
        raise LookupError("RayData is empty when trying to calculate receiver power")
    
    # Filter ray data by mirror element
    power = 0.0
    for el in heliostat:
        hit_rays = rayData[rayData['element'] == el.id+1]['number']
        hitRayData = rayData[rayData['number'].isin(hit_rays)]
        power += len(hitRayData[hitRayData['element'] == -(receiver.id+1)]) * PT.powerperray / 1.e3
    
    return power    

def encircled_energy(PT: PySolTrace, receiver, heliostat):
    """
    Calculates the encircled energy on the receiver outward from the heliostat aimpoint.
    
    :param PT: PySolTrace instance

    :return encircled energy: pd.DataFrame with columns (radius [m], cumulative_power [kWt], cumulative_efficiency [-])
    """
    rayData = PT.raydata
    if rayData.empty:
        raise LookupError("RayData is empty when trying to calculate encircled energy.")
    
    if receiver.surface not in ['f']:
        raise(RuntimeError(f"Surface type {receiver.surface} is not supported for flux plot generation. Must be 'f'."))
    
    # Remove any rays coming directly from the sun TODO: will most likely have to remove
    sun_vec = PT.sun.position.unitize()
    rayData = rayData[~((abs(sun_vec.x + rayData['cos_x']) <= 1e-6)
                        & (abs(sun_vec.y + rayData['cos_y']) <= 1e-6)
                        & (abs(sun_vec.z + rayData['cos_z']) <= 1e-6))]

    # Filter ray data by rays that hit the receiver
    el_id = receiver.id + 1
    st_id = receiver.stage_id+1
    recRayData = rayData[rayData.stage==st_id]
    recRayData = recRayData[recRayData.element==-el_id]  # absorbed rays only
    recRayData = recRayData.copy()

    # Rays that hit the heliostat
    rayData = PT.raydata
    hit_rays = rayData[rayData['element'].isin([el.id+1 for el in heliostat])]['number']
    recRayData = recRayData[recRayData['number'].isin(hit_rays)]

    # Compute the euler angles for the target element
    eu_angles = PT.util_calc_euler_angles(np.array(receiver.position.as_list()), np.array(receiver.aim.as_list()), receiver.zrot)
    # Compute the transform matrix
    transforms = PT.util_calc_transforms(eu_angles)

    # initialize
    loc = recRayData[['loc_x','loc_y','loc_z']].to_numpy()
    e_pos = np.array(receiver.position.as_list())

    pos_t = PT.util_transform_to_local(loc, np.array([0,0,1]), e_pos, transforms['rreftoloc'])['posloc']
    recRayData['loc_xt'] = pos_t.T[0]
    recRayData['loc_yt'] = pos_t.T[1]
    recRayData['loc_zt'] = pos_t.T[2]

    # Assumes center aimpoint is (0,0) in local coords
    recRayData['radius'] = np.sqrt(recRayData['loc_xt']**2 + recRayData['loc_yt']**2)
    recRayData = recRayData.sort_values(by=['radius'])
    recRayData = recRayData.reset_index(drop=True)
    recRayData['cumulative_power'] = PT.powerperray * (recRayData.index + 1) / 1.e3  # kWt

    if False:
        plt.figure()
        plt.plot(recRayData['radius'], recRayData['cumulative_power'])
        plt.xlabel('Radius (m)')
        plt.ylabel('Cumulative Power (kWt)')
        plt.tight_layout()
        plt.show()

    power2receiver = recRayData['cumulative_power'].iloc[-1] 
    #power2receiver = calculate_receiver_power(PT, receiver, heliostat)  # Slow  TODO: Debug why...
    recRayData['cumulative_efficiency'] = recRayData['cumulative_power'] / power2receiver if power2receiver > 0 else 0.0

    assert abs(recRayData['cumulative_efficiency'].iloc[-1] - 1.0) <= 1e-3, f"Final cumulative efficiency {recRayData['cumulative_efficiency'].iloc[-1]} does not equal 1.0"

    return recRayData[['radius', 'cumulative_power', 'cumulative_efficiency']]

if __name__ == "__main__":
    results_dir = "results"

    RESULTS_PATH = "processed_meshes.pkl"
    SAVE_RESULTS_PATH = "processed_meshes_wTrace.pkl"

    case_key_columns = [
        "expected_elevation_angle_deg",
        "expected_azimuth_angle_deg",
        "wind_speed_mps",
        "simulation_time_s",
    ]

    df = pd.read_pickle(os.path.join(results_dir, RESULTS_PATH))
    df = df.drop(columns=["ST_results"], errors="ignore")

    try:
        trace_df = pd.read_pickle(os.path.join(results_dir, SAVE_RESULTS_PATH))
        df = df.merge(
            trace_df[case_key_columns + ["ST_results"]],
            on=case_key_columns,
            how="left",
            validate="one_to_one",
        )
        df["ST_results"] = df["ST_results"].where(df["ST_results"].notna(), None)
        
    except FileNotFoundError:
        print(f"No existing trace results found at: {os.path.join(results_dir, SAVE_RESULTS_PATH)}")
        df["ST_results"] = None

    # Loop through each case and run SolTrace if results are not already available
    for i, case in df.iterrows():
        if case['simulation_time_s'] != 5.0:    # Only trace cases with simulation time of 5.0 s
            continue

        if case['ST_results'] is not None:      # Only run SolTrace if results are not already available
            continue

        print(f"Running case elevation {case['expected_elevation_angle_deg']} and azimuth {case['expected_azimuth_angle_deg']}...")
        print(f"Wind speed {case['wind_speed_mps']} m/s, Simulation time {case['simulation_time_s']} s")

        # A way to filter cases based on expected elevation and azimuth angles
        # if case['expected_elevation_angle_deg'] != 30:
        #     continue
        # if case['expected_azimuth_angle_deg'] != 60:
        #     continue
        
        df.at[i, 'ST_results'] = setup_soltrace(case)
        # Save after each case to ensure progress is not lost
        df.to_pickle(os.path.join(results_dir, SAVE_RESULTS_PATH))

    print(f"Saved updated results to: {os.path.join(results_dir, SAVE_RESULTS_PATH)}")


    if False:
        plt.figure()
        plt.plot(results['ST_baseline']['radius'][::2], results['ST_baseline']['cumulative_efficiency'][::2], label='Baseline')
        plt.plot(results['ST_mean_slope_error']['radius'][::2], results['ST_mean_slope_error']['cumulative_efficiency'][::2], label='Uniform Slope Error')
        plt.plot(results['ST_mesh']['radius'][::2], results['ST_mesh']['cumulative_efficiency'][::2], label='Wind-induced')
        plt.xlabel('Radius (m)')
        plt.ylabel('Cumulative Efficiency (%)')
        plt.legend()
        plt.tight_layout()
        plt.show()

    if False:
        # diff = results['ST_baseline']['flux_map (kW/m^2)'] - results['flux_map (kW/m^2)'] 
        average_flux = results['ST_mesh']['flux_map (kW/m^2)'].mean()
        diff = (results['ST_mean_slope_error']['flux_map (kW/m^2)'] - results['ST_mesh']['flux_map (kW/m^2)']) / average_flux
        W,H = results['receiver_aperture'] 
        x_rec = np.arange(0, W, W/REC_NX)
        y_rec = np.arange(0, H, H/REC_NY)
        xlabtemp = "X-axis position"
        ylabtemp = "Y-axis position"

        plt.figure(figsize=(9,6))
        plt.title('Difference between uniform slope error and mesh surface flux maps')
        Xr,Yr = np.meshgrid(y_rec, x_rec)
        plt.contourf(Yr, Xr, diff, levels=25)
        plt.colorbar(label='Difference in flux (normalized by average)')
        plt.xlabel(xlabtemp)
        plt.ylabel(ylabtemp)
        plt.tight_layout()
        # plt.imshow(diff, cmap='bwr', interpolation='none')
        plt.show()


    #################################################################################
    # Helpfull mesh properties for debugging and understanding the mesh structure
    #################################################################################
    # mesh.vertices           # list of points representing the vertices of the mesh
    # mesh.faces              # list of faces representing the mesh connectivity (vertices indices)
    # mesh.face_normals       # list of normals for each face of the mesh
    # mesh.triangles_center   # list of center points for each triangle of the mesh
    # mesh.centroid           # center point of the mesh

    # mesh.apply_translation([0.0, 0.0, 0.0])  # apply translation to the mesh (example: no translation)
    # mesh.apply_transform(np.eye(4))  # apply an identity transformation (example: no transformation)
    # rot_matrix = trimesh.transformations.rotation_matrix(np.radians(0), [0, 0, 1])  # example: no rotation
    # mesh.apply_transform(rot_matrix)






