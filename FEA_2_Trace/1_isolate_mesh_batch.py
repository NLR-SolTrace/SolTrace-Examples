import trimesh
import re
import numpy as np
import os
import pandas as pd

def simulation_time_from_filename(filename):
    """Extract simulation time from the trailing seconds value in an STL filename.

    Args:
        filename (str): Filename ending in a numeric time followed by 's.stl',
            such as 'Structural steel 1e-6s.stl'. Scientific notation is supported.

    Returns:
        float: Simulation time in seconds.

    Raises:
        ValueError: If the filename does not contain a matching time suffix.
    """
    match = re.search(r"([0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)\s*s\.stl$", filename)
    if match is None:
        raise ValueError(f"Could not parse simulation time from: {filename}")
    return float(match.group(1))

def plot_mesh(mesh, caption="", rotate_view=True):
    """Display a mesh with colored coordinate axes in an interactive viewer.

    Args:
        mesh (trimesh.Trimesh): Mesh to display.
        caption (str): Caption passed to the scene viewer.
        rotate_view (bool): Apply the custom camera rotation when True;
            otherwise use the default scene view.

    Returns:
        None: Opens the scene viewer without returning the scene.
    """
    # Axis colors: Red for X, Green for Y, Blue for Z
    axis = trimesh.creation.axis(origin_size = 0.1,
                                 axis_radius = 0.03,
                                 axis_length = 1.5)
    scene = trimesh.Scene([mesh, axis])
    if rotate_view:
        corners = trimesh.bounds.corners(scene.bounds)
        r_e = trimesh.transformations.euler_matrix(
            np.radians(-45), np.radians(-45), np.radians(0), 'ryxz'
        )
        t_r = scene.camera.look_at(corners, rotation=r_e)
        scene.camera_transform = t_r
    scene.show(caption=caption)

def isolate_reference_mesh(case_path, expected_facet_normal):
    """Load a case's reference STL and isolate its outer reflective plane.

    Args:
        case_path (str): Directory containing exactly one reference '.stl' file,
            excluding filenames containing 'iso_mesh'.
        expected_facet_normal (array-like): Unit normal with shape (3,) defining
            the reflective plane's direction. Faces at the maximum vertex
            projection are selected using a tolerance of 1e-6 in mesh units.

    Returns:
        tuple: Reference filename, full reference mesh, isolated reflective mesh,
            and a NumPy array of selected face indices in the full mesh. The
            indices can be reused for simulation meshes with matching topology.

    Raises:
        AssertionError: If reference-file counts, mesh faces, plane selection,
            or isolated face normals fail validation.
    """
    stl_files = [
        filename for filename in os.listdir(case_path)
        if filename.endswith('.stl') and 'iso_mesh' not in filename
    ]
    assert len(stl_files) > 0, f"No STL files found in {case_path}"
    assert len(stl_files) == 1, f"Expected exactly one STL file in {case_path}, found {len(stl_files)}"
    ref_file = stl_files[0]
    ref_mesh = trimesh.load(os.path.join(case_path, ref_file), process=False)
    assert len(ref_mesh.faces) > 0, f"Reference mesh has no faces: {ref_file}"

    plane_tolerance = 1e-6
    vertex_plane_distances = ref_mesh.vertices @ expected_facet_normal
    vertex_on_plane = np.abs(vertex_plane_distances - np.max(vertex_plane_distances)) <= plane_tolerance
    face_on_plane = vertex_on_plane[ref_mesh.faces].all(axis=1)
    assert np.any(face_on_plane), f"No faces lie on the expected plane in the isolated mesh: {ref_file}"
    facet_mesh_idxs = np.where(face_on_plane)[0]
    isolated_mesh = ref_mesh.submesh([facet_mesh_idxs], append=True)

    normal_deviation = np.abs(isolated_mesh.face_normals - expected_facet_normal)
    assert np.all(normal_deviation < 1e-3), f"Isolated mesh normals deviate too much from expected facet normal: {ref_file}"

    return ref_file, ref_mesh, isolated_mesh, facet_mesh_idxs

def calculate_mesh_metrics(facet_mesh, expected_facet_normal, expected_elevation_deg, expected_azimuth_deg):
    """Calculate facet orientation, tracking errors, and slope-error statistics.

    Args:
        facet_mesh (trimesh.Trimesh): Nonempty reflective mesh with face normals
            and areas, positive total area, and a nonzero area-weighted normal.
        expected_facet_normal (array-like): Expected unit normal with shape (3,).
        expected_elevation_deg (float): Expected normal elevation in degrees.
        expected_azimuth_deg (float): Expected normal azimuth in degrees.

    Returns:
        tuple: A metrics dictionary and a NumPy array of per-face slope errors
            in milliradians, ordered like facet_mesh.faces. The dictionary
            contains the area-weighted unit normal components, orientation in
            degrees, signed elevation/azimuth and total tracking errors in
            milliradians, unweighted and area-weighted slope-error means and
            standard deviations in milliradians, and face/vertex counts.
    """
    face_norms = facet_mesh.face_normals
    face_areas = facet_mesh.area_faces
    weighted_norms = face_norms * face_areas[:, np.newaxis]
    avg_norm = np.sum(weighted_norms, axis=0)
    avg_norm /= np.linalg.norm(avg_norm)

    elevation_angle_deg = np.degrees(np.arcsin(avg_norm[1]))
    azimuth_angle_deg = np.degrees(np.arctan2(-avg_norm[2], -avg_norm[0]))
    tracking_error_mrad = np.arccos(np.clip(np.dot(avg_norm, expected_facet_normal), -1.0, 1.0)) * 1000.0
    slope_error_mrad = np.arccos(np.clip(np.dot(face_norms, avg_norm), -1.0, 1.0)) * 1000.0
    slope_error_mean_weighted_mrad = np.sum(slope_error_mrad * face_areas) / np.sum(face_areas)
    slope_error_std_weighted_mrad = np.sqrt(np.sum(face_areas * (slope_error_mrad - slope_error_mean_weighted_mrad)**2) / np.sum(face_areas))

    metrics = {
        "avg_facet_normal_x": avg_norm[0],
        "avg_facet_normal_y": avg_norm[1],
        "avg_facet_normal_z": avg_norm[2],
        "elevation_angle_deg": elevation_angle_deg,
        "el_tracking_error_mrad": np.radians(elevation_angle_deg - expected_elevation_deg) * 1000.0,
        "azimuth_angle_deg": azimuth_angle_deg,
        "az_tracking_error_mrad": np.radians(azimuth_angle_deg - expected_azimuth_deg) * 1000.0,
        "total_tracking_error_mrad": tracking_error_mrad,
        "slope_error_mean_mrad": np.mean(slope_error_mrad),
        "slope_error_std_mrad": np.std(slope_error_mrad),
        "slope_error_mean_weighted_mrad": slope_error_mean_weighted_mrad,
        "slope_error_std_weighted_mrad": slope_error_std_weighted_mrad,
        "n_facet_faces": len(facet_mesh.faces),
        "n_facet_vertices": len(facet_mesh.vertices),
    }
    return metrics, slope_error_mrad

def save_results(existing_results, result_rows, results_dir, save_file_name, case_key_columns):
    """Combine and sort result rows, then overwrite pickle and CSV summaries.

    Args:
        existing_results (pandas.DataFrame or None): Previously loaded results,
            or None for a fresh run.
        result_rows (list[dict]): All new rows accumulated during this run,
            excluding rows already present in existing_results.
        results_dir (str): Existing directory where summaries will be written.
        save_file_name (str): Output basename without '.pkl' or '.csv'.
        case_key_columns (sequence[str]): Columns used to sort the combined
            results. These columns must exist in the combined table.

    Returns:
        pandas.DataFrame: Combined, sorted results with a reset integer index.
            Both output files contain this table; the CSV omits the index.
    """
    new_results = pd.DataFrame(result_rows)
    results = pd.concat(
        [existing_results, new_results] if existing_results is not None else [new_results],
        ignore_index=True,
    )
    results = results.sort_values(list(case_key_columns), ignore_index=True)
    results.to_pickle(os.path.join(results_dir, save_file_name + ".pkl"))
    results.to_csv(os.path.join(results_dir, save_file_name + ".csv"), index=False)
    return results

if __name__ == "__main__":
    verbose = False
    plot_meshes = False

    stl_files_dir = "stl_files"
    results_dir = "results"

    load_file_name = "processed_meshes"
    save_file_name = "processed_meshes"

    # Check if results directory exists, create if not
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    # Check for existing results, load them if available
    case_key_columns = (
        "expected_elevation_angle_deg",
        "expected_azimuth_angle_deg",
        "wind_speed_mps",
        "simulation_time_s",
    )

    existing_results = None
    processed_case_keys = set()
    if os.path.exists(os.path.join(results_dir, load_file_name + ".pkl")):
        existing_results = pd.read_pickle(os.path.join(results_dir, load_file_name + ".pkl"))
        missing_key_columns = set(case_key_columns) - set(existing_results.columns)
        if missing_key_columns:
            raise ValueError(
                f"Existing summary is missing case identity columns: {sorted(missing_key_columns)}"
            )
        processed_case_keys = set(
            existing_results.loc[:, case_key_columns].itertuples(index=False, name=None)
        )
    else:
        print("No existing results found.")

    # List all cases in the STL files directory
    cases = os.listdir(stl_files_dir)
    if verbose:
        print(f"Found {len(cases)} cases in {stl_files_dir}")

    result_rows = []
    results = existing_results if existing_results is not None else pd.DataFrame()
    for case in cases:
        print(f"Processing case: {case}")
        case_path = os.path.join(stl_files_dir, case)
        if not os.path.isdir(case_path):
            print(f"Skipping non-directory case: {case}")
            continue

        # Extract expected elevation and azimuth from the case name
        expected_elevation_deg = float(case.split(' ')[0])
        expected_azimuth_deg = float(case.split(' ')[2])
        expected_facet_normal = np.array([-np.cos(np.radians(expected_elevation_deg)) * np.cos(np.radians(expected_azimuth_deg)),
                                          np.sin(np.radians(expected_elevation_deg)),
                                          -np.cos(np.radians(expected_elevation_deg)) * np.sin(np.radians(expected_azimuth_deg))])

        # Useful Filters
        # if expected_elevation_deg < 29.0: # or expected_elevation_deg > 31.0:
        #     continue

        # if expected_azimuth_deg < 29.0:
        #     continue

        # Isolate the reference (undeformed) mesh based on the expected facet normal
        ref_file, ref_mesh, isolated_mesh, facet_mesh_idxs = isolate_reference_mesh(case_path, expected_facet_normal)

        if verbose:
            print(f"Expected elevation: {expected_elevation_deg}, Expected azimuth: {expected_azimuth_deg}")
            print(f"Expected facet normal: {expected_facet_normal}")
            print(f"Reference mesh: {len(ref_mesh.faces)} faces, {len(ref_mesh.vertices)} vertices")
            print(f"Isolated mesh: {len(isolated_mesh.faces)} faces, {len(isolated_mesh.vertices)} vertices")
        if plot_meshes:
            plot_mesh(ref_mesh, caption=f"Reference mesh: {case}/{ref_file}")
            plot_mesh(isolated_mesh, caption=f"Isolated mesh: {case}/{ref_file}")

        # 5. Export the isolated mesh to a file
        iso_mesh_path = os.path.join(case_path, "iso_mesh_" + ref_file)
        isolated_mesh.export(iso_mesh_path)

        # Process all simulation slices for each wind speed
        files = os.listdir(case_path)
        wind_speeds_cases = [f for f in files if os.path.isdir(os.path.join(case_path, f))]
        wind_speeds = [float(ws.replace("mps", "")) for ws in wind_speeds_cases]

        for ws_case, ws_mps in zip(wind_speeds_cases, wind_speeds):
            # Create a directory to store isolated meshes for this wind speed case
            ws_path = os.path.join(case_path, ws_case)
            iso_mesh_dir = os.path.join(ws_path, "isolated_meshes")
            os.makedirs(iso_mesh_dir, exist_ok=True)

            surface_slope_errors_mrad = np.array([])
            sim_files = [f for f in os.listdir(ws_path) if f.endswith(".stl")]
            for sim_file in sim_files:
                simulation_time = simulation_time_from_filename(sim_file)
                case_key = (
                    expected_elevation_deg,
                    expected_azimuth_deg,
                    ws_mps,
                    simulation_time,
                )
                if case_key in processed_case_keys:
                    continue

                # Read in the simulation mesh and isolate the reflective facets
                sim_file_path = os.path.join(ws_path, sim_file)
                sim_mesh = trimesh.load(sim_file_path, process=False)
                facet_mesh = sim_mesh.submesh([facet_mesh_idxs], append=True)

                if verbose:
                    print(f"Processing file: {sim_file}")
                    print(f"Original simulation mesh: {len(sim_mesh.faces)} faces, {len(sim_mesh.vertices)} vertices")
                    print(f"Isolated reflective facets: {len(facet_mesh.faces)} faces, {len(facet_mesh.vertices)} vertices")

                assert len(facet_mesh.faces) == len(isolated_mesh.faces), f"Mismatch in number of faces between isolated simulation mesh ({len(facet_mesh.faces)}) and isolated reference mesh ({len(isolated_mesh.faces)})"
                assert len(facet_mesh.vertices) == len(isolated_mesh.vertices), f"Mismatch in number of vertices between isolated simulation mesh ({len(facet_mesh.vertices)}) and isolated reference mesh ({len(isolated_mesh.vertices)})"

                if plot_meshes:
                    if simulation_time_from_filename(sim_file) == 0.2:
                        plot_mesh(facet_mesh, caption=f"Isolated simulation reflective facets: {sim_file}")

                # Save the isolated mesh from this simulation file
                iso_mesh_file = "iso_mesh_" + sim_file
                iso_mesh_path = os.path.join(iso_mesh_dir, iso_mesh_file)
                facet_mesh.export(iso_mesh_path)

                metrics, case_slope_error_mrad = calculate_mesh_metrics(
                    facet_mesh, expected_facet_normal, expected_elevation_deg, expected_azimuth_deg
                )

                if max(case_slope_error_mrad) >= 15.0:
                    print(f"WARNING: Max slope error exceeded: {max(case_slope_error_mrad)} mrad, simulation file: {sim_file}, wind speed: {ws_mps} mps")

                surface_slope_errors_mrad = np.concatenate((surface_slope_errors_mrad, case_slope_error_mrad))
                if verbose:
                    avg_norm = np.array([metrics[f"avg_facet_normal_{axis}"] for axis in ("x", "y", "z")])
                    print(f"\tAverage normal: {avg_norm}")
                    print(f"\tElevation angle: {metrics['elevation_angle_deg']:.3f} degrees")
                    print(f"\tAzimuth angle: {metrics['azimuth_angle_deg']:.3f} degrees")
                    print(f"\tTotal tracking error: {metrics['total_tracking_error_mrad']:.3f} mrad")
                    print(f"\tMean slope error: {metrics['slope_error_mean_mrad']:.3f} mrad")
                    print(f"\tStandard deviation of slope error: {metrics['slope_error_std_mrad']:.3f} mrad")
                    print(f"\tWeighted mean slope error: {metrics['slope_error_mean_weighted_mrad']:.3f} mrad")
                    print(f"\tWeighted standard deviation of slope error: {metrics['slope_error_std_weighted_mrad']:.3f} mrad")

                result_rows.append({
                    "expected_elevation_angle_deg": expected_elevation_deg,
                    "expected_azimuth_angle_deg": expected_azimuth_deg,
                    "wind_speed_mps": ws_mps,
                    "simulation_time_s": simulation_time,
                    **metrics,
                    "original_mesh_path": sim_file_path,
                    "isolated_mesh_path": iso_mesh_path,
                })
                results = save_results(
                    existing_results, result_rows, results_dir, save_file_name, case_key_columns
                )
                processed_case_keys.add(case_key)

            # Print table of results for the current wind speed case - showing only new results added
            print(f"\nResults for case: {ws_case}")
            case_results = pd.DataFrame(result_rows)
            if case_results.empty:
                print("There were previously processed results for this case (i.e.,no new results added)")
            else:
                case_results = case_results[(case_results["expected_elevation_angle_deg"] == expected_elevation_deg)
                                            & (case_results["expected_azimuth_angle_deg"] == expected_azimuth_deg)
                                            & (case_results["wind_speed_mps"] == ws_mps)]
                if case_results.empty:
                    print("There were previously processed results for this case (i.e.,no new results added)")
                else:
                    case_results = case_results.sort_values("simulation_time_s")
                    print(case_results[["simulation_time_s",
                                        "elevation_angle_deg",
                                        "azimuth_angle_deg",
                                        "el_tracking_error_mrad",
                                        "az_tracking_error_mrad",
                                        "slope_error_mean_weighted_mrad"
                                        ]].to_string(index=False))

    print(f"Added {len(result_rows)} new result rows; saved {len(results)} total rows to: "
          f"{os.path.join(results_dir, save_file_name)}.pkl and {os.path.join(results_dir, save_file_name)}.csv"
    )
