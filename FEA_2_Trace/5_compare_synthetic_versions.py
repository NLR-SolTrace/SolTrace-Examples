from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DATA_DIR = Path(__file__).resolve().parent
VERSIONS = ("v1", "v2", "v3", "v4")
KEY_COLUMNS = [
    "expected_elevation_angle_deg",
    "expected_azimuth_angle_deg",
    "wind_speed_mps",
]
METRICS = {
    "el_tracking_error_mrad": "Elevation tracking error",
    "az_tracking_error_mrad": "Azimuth tracking error",
    "slope_error_mean_weighted_mrad": "Weighted mean slope error",
}


def load_version_data() -> dict[str, pd.DataFrame]:
    version_data = {}
    required_columns = set(KEY_COLUMNS) | set(METRICS)

    for version in VERSIONS:
        path = DATA_DIR / f"synthetic_heliostat_data_{version}.csv"
        data = pd.read_csv(path)
        missing_columns = required_columns.difference(data.columns)
        if missing_columns:
            raise ValueError(
                f"{path.name} is missing required columns: {sorted(missing_columns)}"
            )
        if data.duplicated(KEY_COLUMNS).any():
            raise ValueError(f"{path.name} contains duplicate operating-point keys")
        version_data[version] = data.set_index(KEY_COLUMNS).sort_index()

    reference_index = version_data[VERSIONS[0]].index
    for version in VERSIONS[1:]:
        version_index = version_data[version].index
        if not reference_index.equals(version_index):
            missing_count = len(reference_index.difference(version_index))
            extra_count = len(version_index.difference(reference_index))
            raise ValueError(
                f"{version} operating points do not match v1: "
                f"{missing_count} missing, {extra_count} extra"
            )

    return version_data


def calculate_pairwise_errors(
    version_data: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    pairwise_differences = []

    for earlier, later in combinations(VERSIONS, 2):
        signed_difference = (
            version_data[later][list(METRICS)]
            - version_data[earlier][list(METRICS)]
        )
        long_difference = (
            signed_difference.rename_axis(KEY_COLUMNS)
            .reset_index()
            .melt(
                id_vars=KEY_COLUMNS,
                var_name="metric",
                value_name="signed_difference_mrad",
            )
        )
        long_difference["comparison"] = f"{earlier} to {later}"
        pairwise_differences.append(long_difference)

    error_differences = pd.concat(pairwise_differences, ignore_index=True)
    error_differences["absolute_difference_mrad"] = error_differences[
        "signed_difference_mrad"
    ].abs()

    summary = (
        error_differences.groupby(["metric", "comparison"], sort=False)[
            "signed_difference_mrad"
        ]
        .agg(
            bias_mrad="mean",
            mae_mrad=lambda values: values.abs().mean(),
            rmse_mrad=lambda values: np.sqrt(np.mean(values**2)),
            p95_abs_mrad=lambda values: values.abs().quantile(0.95),
            max_abs_mrad=lambda values: values.abs().max(),
        )
    )
    return error_differences, summary


def plot_pairwise_errors(
    error_differences: pd.DataFrame,
    summary: pd.DataFrame,
) -> tuple[plt.Figure, np.ndarray]:
    comparisons = [
        f"{left} to {right}" for left, right in combinations(VERSIONS, 2)
    ]
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(comparisons)))
    figure, axes = plt.subplots(
        2, 3, figsize=(17, 10), constrained_layout=True
    )

    for column, (metric, title) in enumerate(METRICS.items()):
        metric_summary = summary.loc[metric]
        rmse_matrix = pd.DataFrame(0.0, index=VERSIONS, columns=VERSIONS)
        for left, right in combinations(VERSIONS, 2):
            value = metric_summary.loc[f"{left} to {right}", "rmse_mrad"]
            rmse_matrix.loc[left, right] = value
            rmse_matrix.loc[right, left] = value

        heatmap_axis = axes[0, column]
        image = heatmap_axis.imshow(rmse_matrix, cmap="magma", vmin=0)
        heatmap_axis.set_xticks(range(len(VERSIONS)), VERSIONS)
        heatmap_axis.set_yticks(range(len(VERSIONS)), VERSIONS)
        heatmap_axis.set_title(f"{title}\nPairwise RMSE (mrad)")
        matrix_max = rmse_matrix.to_numpy().max()
        for row in range(len(VERSIONS)):
            for matrix_column in range(len(VERSIONS)):
                value = rmse_matrix.iloc[row, matrix_column]
                text_color = "white" if value < matrix_max * 0.55 else "black"
                heatmap_axis.text(
                    matrix_column,
                    row,
                    f"{value:.3f}",
                    ha="center",
                    va="center",
                    color=text_color,
                )
        figure.colorbar(
            image, ax=heatmap_axis, shrink=0.82, label="RMSE (mrad)"
        )

        distribution_axis = axes[1, column]
        metric_errors = error_differences.loc[
            error_differences["metric"] == metric
        ]
        distributions = [
            metric_errors.loc[
                metric_errors["comparison"] == comparison,
                "absolute_difference_mrad",
            ]
            for comparison in comparisons
        ]
        boxes = distribution_axis.boxplot(
            distributions,
            tick_labels=comparisons,
            patch_artist=True,
            showfliers=False,
            whis=(5, 95),
        )
        for patch, color in zip(boxes["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.8)
        distribution_axis.set_title(
            f"{title}\nAbsolute pairwise differences"
        )
        distribution_axis.set_ylabel("Absolute difference (mrad)")
        distribution_axis.tick_params(axis="x", rotation=35)
        distribution_axis.grid(axis="y", alpha=0.25)

    figure.suptitle(
        "Prediction disagreement across synthetic heliostat datasets\n"
        "Boxes show 5th-95th percentile whiskers across 364 matched operating points",
        fontsize=15,
    )
    return figure, axes


def main() -> None:
    version_data = load_version_data()
    error_differences, summary = calculate_pairwise_errors(version_data)
    print(summary.round(4).to_string())

    figure, _ = plot_pairwise_errors(error_differences, summary)
    output_path = DATA_DIR / "synthetic_data_version_error_comparison.png"
    figure.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.show()
    print(f"\nSaved comparison figure to: {output_path}")


if __name__ == "__main__":
    main()
