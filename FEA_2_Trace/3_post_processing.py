from pathlib import Path
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import ttk

import trimesh
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from functools import lru_cache


if __name__ == "__main__":
    # RESULTS_PATH = "results/processed_meshes.pkl"
    RESULTS_PATH = "results/processed_meshes_wTrace.pkl"
    df = pd.read_pickle(RESULTS_PATH)
    print(f"Loaded {len(df)} result rows from: {RESULTS_PATH}")
    print(df.columns)

    # Create Group Results
    # sim_avg_path = "results/sim_avg_results"
    sim_avg_path = "results/grouped_avg_results_v4"
    sim_avg_results = df.drop(columns=["simulation_time_s", 
                                    "n_facet_vertices",
                                    "n_facet_faces", 
                                    "n_facet_vertices"]).groupby(["expected_elevation_angle_deg", 
                                                                    "expected_azimuth_angle_deg", 
                                                                    "wind_speed_mps"]).mean(numeric_only=True)
    sim_avg_results.to_pickle(sim_avg_path + ".pkl")
    sim_avg_results.to_csv(sim_avg_path + ".csv")
    print(sim_avg_results.head())

    # TODO: Move group results creation to a separate function for clarity


    groups = df.groupby(["expected_elevation_angle_deg", "expected_azimuth_angle_deg", "wind_speed_mps"])
    keys = list(groups.groups.keys())

    N_HIST_BINS = 50
    MAX_BOX_TICKS = 20
    FIGURE_DIR = Path("results/figures")
    FIGURE_DPI = 200
    TRACE_TIME_S = 5.0
    MAX_CURVE_POINTS = 2000
    TRACE_LABELS = {
        "ST_baseline": "No Slope Error",
        "ST_mean_slope_error": "Mean Slope Error",
        "ST_mesh": "STL Mesh",
    }
    FLUX_OPTIONS = [(label, name) for name, label in TRACE_LABELS.items()]
    for reference in ("ST_baseline", "ST_mean_slope_error"):
        for mode in ("absolute", "relative"):
            FLUX_OPTIONS.append((
                f"{mode.title()} difference: STL Mesh - {TRACE_LABELS[reference]}",
                f"{mode}:{reference}",
            ))

    
    def in_plane_basis(normal):
        # Orthonormal (u, v) spanning the plane perpendicular to the normal; y is the global up axis
        ref = np.array([0.0, 1.0, 0.0]) if abs(normal[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
        u = np.cross(ref, normal)
        u /= np.linalg.norm(u)
        v = np.cross(normal, u)
        return u, v


    @lru_cache(maxsize=None)
    def load_case(key):
        """Load every timestep of a case, projecting the mesh onto the plane normal to the tracking normal."""
        case = groups.get_group(key).sort_values("simulation_time_s")
        steps = []
        for _, row in case.iterrows():
            tracking_normal = row[["avg_facet_normal_x", "avg_facet_normal_y", "avg_facet_normal_z"]].to_numpy(dtype=float)
            tracking_normal /= np.linalg.norm(tracking_normal)

            #print(f"Loading mesh for simulation time {row['simulation_time_s']:.3f} s from {row['isolated_mesh_path']}")
            mesh = trimesh.load(row["isolated_mesh_path"])
            slope_error_mrad = np.arccos(np.clip(mesh.face_normals @ tracking_normal, -1.0, 1.0)) * 1000.0

            u, v = in_plane_basis(tracking_normal)
            pts = mesh.vertices - mesh.vertices.mean(axis=0)
            xy = np.column_stack((pts @ u, pts @ v))

            steps.append({"t": row["simulation_time_s"], "xy": xy, "faces": np.asarray(mesh.faces),
                        "se": slope_error_mrad, "area": np.asarray(mesh.area_faces)})

        all_se = np.concatenate([s["se"] for s in steps])
        return steps, float(all_se.min()), float(all_se.max())


    def plot_trace_panels(fig, ax_energy, ax_flux, key, cumulative_metric, flux_choice):
        ax_energy.set_title(f"Encircled energy | t = {TRACE_TIME_S:g} s")
        ax_energy.set_xlabel("Radius (m)")
        ax_energy.set_ylabel("Cumulative power (kW)" if cumulative_metric == "cumulative_power"
                            else "Cumulative efficiency (%)")
        ax_flux.set_xlabel("X-axis position (m)")
        ax_flux.set_ylabel("Y-axis position (m)")
        case = groups.get_group(key)
        trace_rows = case.loc[np.isclose(case["simulation_time_s"], TRACE_TIME_S, rtol=0.0, atol=1e-6)]
        trace_results = next((value for value in trace_rows.get("ST_results", [])
                            if isinstance(value, dict)), None)
        if trace_results is None:
            for axis in (ax_energy, ax_flux):
                axis.text(0.5, 0.5, "No ray-tracing results at t = 5 s",
                        transform=axis.transAxes, ha="center", va="center")
            ax_flux.set_title(f"Receiver flux | t = {TRACE_TIME_S:g} s")
            return

        for name, label in TRACE_LABELS.items():
            result = trace_results[name]
            radius = np.asarray(result["radius"])
            values = np.asarray(result[cumulative_metric])
            sample_idx = np.linspace(0, len(radius) - 1, min(len(radius), MAX_CURVE_POINTS), dtype=int)
            scale = 100.0 if cumulative_metric == "cumulative_efficiency" else 1.0
            ax_energy.plot(radius[sample_idx], values[sample_idx] * scale, label=label)
        if cumulative_metric == "cumulative_efficiency":
            ax_energy.set_ylim(0, 100)
        ax_energy.legend()

        if ":" in flux_choice:
            mode, reference = flux_choice.split(":", 1)
            mesh_flux = np.asarray(trace_results["ST_mesh"]["flux_map (kW/m^2)"]) * 1000.0
            reference_flux = np.asarray(trace_results[reference]["flux_map (kW/m^2)"]) * 1000.0
            flux = mesh_flux - reference_flux
            title = f"STL Mesh - {TRACE_LABELS[reference]}"
            colorbar_label = "Flux difference (W/m^2)"
            if mode == "relative":
                mean_mesh_flux = mesh_flux.mean()
                if mean_mesh_flux <= 0:
                    ax_flux.text(0.5, 0.5, "Relative difference unavailable: zero mean mesh flux",
                                transform=ax_flux.transAxes, ha="center", va="center", wrap=True)
                    ax_flux.set_title(f"Relative flux difference | t = {TRACE_TIME_S:g} s")
                    return
                flux = flux / mean_mesh_flux
                colorbar_label = "Flux difference / mean STL Mesh flux (-)"
            limit = max(float(np.max(np.abs(flux))), np.finfo(float).eps)
            levels = np.linspace(-limit, limit, 25)
            cmap = "RdBu_r"
            title = f"{mode.title()} difference: {title}"
        else:
            flux = np.asarray(trace_results[flux_choice]["flux_map (kW/m^2)"]) * 1000.0
            title = TRACE_LABELS[flux_choice]
            colorbar_label = "Flux (W/m^2)"
            levels = 25
            cmap = "turbo"

        width, height = trace_results["receiver_aperture"]
        x_rec = -width / 2.0 + (np.arange(flux.shape[0]) + 0.5) * width / flux.shape[0]
        y_rec = -height / 2.0 + (np.arange(flux.shape[1]) + 0.5) * height / flux.shape[1]
        contour = ax_flux.contourf(x_rec, y_rec, flux.T, levels=levels, cmap=cmap)
        fig.colorbar(contour, ax=ax_flux, label=colorbar_label)
        active_bins = np.isfinite(flux) & (flux != 0)
        active_x, active_y = np.where(active_bins)
        if active_x.size:
            dx = width / flux.shape[0]
            dy = height / flux.shape[1]
            ax_flux.set_xlim(x_rec[active_x.min()] - dx / 2.0,
                            x_rec[active_x.max()] + dx / 2.0)
            ax_flux.set_ylim(y_rec[active_y.min()] - dy / 2.0,
                            y_rec[active_y.max()] + dy / 2.0)
        ax_flux.set_aspect("equal")
        ax_flux.set_title(f"{title}\nt = {TRACE_TIME_S:g} s")


    def figure_path(key, t):
        el, az, w = key
        case_dir = FIGURE_DIR / f"el{el:g}_az{az:g}_wind{w:g}mps"
        case_dir.mkdir(parents=True, exist_ok=True)
        return case_dir / f"t_{t:08.3f}s.png"


    def make_figure(key, idx, cumulative_metric="cumulative_efficiency", flux_choice="ST_mesh"):
        steps, vmin, vmax = load_case(key)
        idx = min(idx, len(steps) - 1)
        s = steps[idx]
        se = s["se"]
        elkey, azkey, windkey = key

        fig, axes = plt.subplots(3, 2, figsize=(14, 9), gridspec_kw={"width_ratios": [1.2, 1]})
        (ax_map, ax_hist), (ax_box, ax_cum), (ax_energy, ax_flux) = axes

        # Top-left: 2D projected slope error map (shared color scale across all timesteps)
        tpc = ax_map.tripcolor(s["xy"][:, 0], s["xy"][:, 1], s["faces"], facecolors=se,
                            cmap="turbo", vmin=vmin, vmax=vmax)
        fig.colorbar(tpc, ax=ax_map, label="Slope Error (mrad)")
        ax_map.set_aspect("equal")
        ax_map.set_xlabel("In-plane u (m)")
        ax_map.set_ylabel("In-plane v (m)")
        ax_map.set_title("Slope error projected along tracking normal")

        # Top-right: relative frequency histogram (shared bins across all timesteps)
        mean, median = se.mean(), np.median(se)
        lo, hi = np.percentile(se, [25.0, 75.0])
        ax_hist.hist(se, bins=np.linspace(vmin, vmax, N_HIST_BINS + 1), weights=np.full(se.size, 100.0 / se.size),
                    color="lightgray", edgecolor="black")
        ax_hist.axvline(mean, color="tab:red", ls="--", lw=2, label=f"Mean = {mean:.2f} mrad")
        ax_hist.axvline(median, color="tab:blue", ls="--", lw=2, label=f"Median = {median:.2f} mrad")
        ax_hist.axvline(lo, color="tab:green", ls="--", lw=2, label=f"25/75% interval = [{lo:.2f}, {hi:.2f}] mrad")
        ax_hist.axvline(hi, color="tab:green", ls="--", lw=2)
        ax_hist.set_xlim(vmin, vmax)
        ax_hist.set_xlabel("Slope Error (mrad)")
        ax_hist.set_ylabel("Relative frequency (% of faces)")
        ax_hist.set_title("Slope error distribution")
        ax_hist.legend()

        # Bottom-left: slope error distribution over time, selected timestep highlighted
        times = [st["t"] for st in steps]
        bp = ax_box.boxplot([st["se"] for st in steps], positions=np.arange(len(steps)), patch_artist=True,
                            showfliers=False, widths=0.6, medianprops={"color": "black"})
        for i, box in enumerate(bp["boxes"]):
            box.set_facecolor("tab:orange" if i == idx else "lightgray")
            box.set_edgecolor("black")
            box.set_linewidth(2.5 if i == idx else 1.0)
        ax_box.axvspan(idx - 0.5, idx + 0.5, color="tab:orange", alpha=0.15, zorder=0)
        tick_step = max(1, int(np.ceil(len(steps) / MAX_BOX_TICKS)))
        tick_idx = np.arange(0, len(steps), tick_step)
        ax_box.set_xticks(tick_idx)
        ax_box.set_xticklabels([f"{times[i]:.2f}" for i in tick_idx], rotation=45, ha="right")
        ax_box.set_xlabel("Simulation time (s)")
        ax_box.set_ylabel("Slope Error (mrad)")
        ax_box.set_title("Slope error distribution over time (whiskers = 1.5 IQR)")

        # Bottom-right: cumulative heliostat area with slope error below X (area-weighted)
        order = np.argsort(se)
        se_sorted = se[order]
        area_sorted = s["area"][order]
        cum_pct = np.cumsum(area_sorted) / area_sorted.sum() * 100.0
        ax_cum.plot(se_sorted, cum_pct, color="black", lw=2)
        a_mean = np.average(se, weights=s["area"])
        a_q1, a_med, a_q3 = np.interp([25.0, 50.0, 75.0], cum_pct, se_sorted)
        ax_cum.axvline(a_mean, color="tab:red", ls="--", lw=2, label=f"Mean = {a_mean:.2f} mrad")
        ax_cum.axvline(a_med, color="tab:blue", ls="--", lw=2, label=f"Median = {a_med:.2f} mrad")
        ax_cum.axvline(a_q1, color="tab:green", ls="--", lw=2, label=f"25/75% = [{a_q1:.2f}, {a_q3:.2f}] mrad")
        ax_cum.axvline(a_q3, color="tab:green", ls="--", lw=2)
        for q in (25.0, 50.0, 75.0):
            ax_cum.axhline(q, color="gray", ls=":", lw=1)
        ax_cum.set_xlim(vmin, vmax)
        ax_cum.set_ylim(0, 100)
        ax_cum.set_xlabel("Slope Error X (mrad)")
        ax_cum.set_ylabel("Heliostat area with slope error < X (%)")
        ax_cum.set_title("Cumulative area distribution (area-weighted)")
        ax_cum.legend(loc="lower right")

        plot_trace_panels(fig, ax_energy, ax_flux, key, cumulative_metric, flux_choice)
        fig.suptitle(f"El={elkey:g} deg, Az={azkey:g} deg, Wind={windkey:g} m/s  |  Slope panels: t = {s['t']:.3f} s")
        fig.tight_layout(rect=(0, 0, 1, 0.97))
        return fig, s["t"]


    plot_state = {"canvas": None, "figure": None}


    def plot_timestep(key, idx, cumulative_metric, flux_choice):
        if idx is None:
            return
        fig, t = make_figure(key, idx, cumulative_metric, flux_choice)
        saved_path = None
        if save_var.get():
            saved_path = figure_path(key, t)
            fig.savefig(saved_path, dpi=FIGURE_DPI, bbox_inches="tight")

        if plot_state["canvas"] is not None:
            plot_state["canvas"].get_tk_widget().destroy()
        if plot_state["figure"] is not None:
            plt.close(plot_state["figure"])

        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        plot_state["canvas"] = canvas
        plot_state["figure"] = fig
        message = f"Displaying t = {t:.3f} s"
        if saved_path is not None:
            message += f" | Saved: {saved_path}"
        status_var.set(message)


    def save_all_timesteps():
        key = keys[case_combo.current()]
        steps, _, _ = load_case(key)
        status_var.set(f"Saving {len(steps)} figures...")
        root.update_idletasks()
        for i in range(len(steps)):
            fig, t = make_figure(key, i, cumulative_metric_var.get(), selected_flux())
            fig.savefig(figure_path(key, t), dpi=FIGURE_DPI, bbox_inches="tight")
            plt.close(fig)
        status_var.set(f"Saved {len(steps)} figures to: {figure_path(key, steps[0]['t']).parent}")


    def selected_flux():
        selected = flux_combo.current()
        return FLUX_OPTIONS[selected][1]

    def update_metric(_event=None):
        metric = "cumulative_efficiency" if metric_combo.current() == 0 else "cumulative_power"
        cumulative_metric_var.set(metric)
        update_plot()


    def update_plot(_event=None):
        case_idx = case_combo.current()
        if case_idx < 0:
            return
        key = keys[case_idx]
        idx = int(time_slider.get())
        steps, _, _ = load_case(key)
        idx = min(idx, len(steps) - 1)
        time_label_var.set(f"Time: {steps[idx]['t']:.3f} s")
        plot_timestep(key, idx, cumulative_metric_var.get(), selected_flux())


    def update_time_options(_event=None):
        key = keys[case_combo.current()]
        steps, _, _ = load_case(key)
        time_slider.configure(from_=0, to=max(0, len(steps) - 1))
        time_slider.set(0)
        update_plot()


    root = tk.Tk()
    root.title("Transient simulation post-processing")
    root.geometry("1500x1050")

    controls = ttk.Frame(root, padding=8)
    controls.pack(side=tk.TOP, fill=tk.X)
    selection_controls = ttk.Frame(controls)
    selection_controls.pack(side=tk.TOP, fill=tk.X)
    display_controls = ttk.Frame(controls)
    display_controls.pack(side=tk.TOP, fill=tk.X, pady=(6, 0))

    case_labels = [f"El={el:g} deg, Az={az:g} deg, Wind={w:g} m/s" for el, az, w in keys]
    case_combo = ttk.Combobox(selection_controls, values=case_labels, state="readonly", width=42)
    case_combo.current(0)
    case_combo.pack(side=tk.LEFT, padx=(0, 8))
    case_combo.bind("<<ComboboxSelected>>", update_time_options)

    time_slider = tk.Scale(
        selection_controls,
        from_=0,
        to=0,
        orient=tk.HORIZONTAL,
        resolution=1,
        showvalue=False,
        label="Timestep",
        length=400,
    )
    time_slider.pack(side=tk.LEFT, padx=8)
    time_slider.bind("<ButtonRelease-1>", update_plot)
    time_slider.bind("<KeyRelease>", update_plot)
    time_label_var = tk.StringVar(value="Time: --")
    ttk.Label(selection_controls, textvariable=time_label_var).pack(side=tk.LEFT, padx=8)

    cumulative_metric_var = tk.StringVar(value="cumulative_efficiency")
    metric_combo = ttk.Combobox(
        display_controls,
        values=("Cumulative efficiency", "Cumulative power"),
        state="readonly",
        width=22,
    )
    metric_combo.current(0)
    metric_combo.pack(side=tk.LEFT, padx=8)
    metric_combo.bind("<<ComboboxSelected>>", update_metric)

    flux_combo = ttk.Combobox(
        display_controls,
        values=[label for label, _ in FLUX_OPTIONS],
        state="readonly",
        width=38,
    )
    flux_combo.current(next(i for i, (_, value) in enumerate(FLUX_OPTIONS) if value == "ST_mesh"))
    flux_combo.pack(side=tk.LEFT, padx=8)
    flux_combo.bind("<<ComboboxSelected>>", update_plot)

    save_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(display_controls, text="Save displayed figure", variable=save_var).pack(side=tk.LEFT, padx=8)
    ttk.Button(display_controls, text="Save all timesteps", command=save_all_timesteps).pack(side=tk.LEFT, padx=8)

    plot_frame = ttk.Frame(root)
    plot_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    status_var = tk.StringVar(value="")
    ttk.Label(root, textvariable=status_var, anchor=tk.W, padding=(8, 4)).pack(side=tk.BOTTOM, fill=tk.X)

    update_time_options()
    root.mainloop()

    # TODO: This doesn't die when the window is closed; consider adding proper cleanup or exit handling.
    # Kill terminal or any background processes if needed
