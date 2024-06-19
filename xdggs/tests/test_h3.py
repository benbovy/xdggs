import itertools

import numpy as np
import pytest
import shapely
import shapely.testing
import xarray as xr
from xarray.core.indexes import PandasIndex

from xdggs import h3

# from the h3 gallery, at resolution 3
cell_ids = [
    np.array([0x832830FFFFFFFFF]),
    np.array([0x832831FFFFFFFFF, 0x832832FFFFFFFFF]),
    np.array([0x832833FFFFFFFFF, 0x832834FFFFFFFFF, 0x832835FFFFFFFFF]),
]
cell_centers = [
    np.array([[38.19320895, -122.19619676]]),
    np.array([[38.63853196, -123.43390346], [38.82387033, -121.00991811]]),
    np.array(
        [
            [39.27846774, -122.2594399],
            [37.09786649, -122.13425086],
            [37.55231005, -123.35925909],
        ]
    ),
]
dims = ["cells", "zones"]
resolutions = [1, 5, 15]
variable_names = ["cell_ids", "zonal_ids", "zone_ids"]

variables = [
    xr.Variable(
        dims[0], cell_ids[0], {"grid_name": "h3", "resolution": resolutions[0]}
    ),
    xr.Variable(
        dims[1], cell_ids[0], {"grid_name": "h3", "resolution": resolutions[0]}
    ),
    xr.Variable(
        dims[0], cell_ids[1], {"grid_name": "h3", "resolution": resolutions[1]}
    ),
    xr.Variable(
        dims[1], cell_ids[2], {"grid_name": "h3", "resolution": resolutions[2]}
    ),
]
variable_combinations = [
    (old, new) for old, new in itertools.product(variables, repeat=2)
]


class TestH3Info:

    @pytest.mark.parametrize(
        ["resolution", "error"],
        (
            (0, None),
            (1, None),
            (-1, ValueError("resolution must be an integer between")),
        ),
    )
    def test_init(self, resolution, error):
        if error is not None:
            with pytest.raises(type(error), match=str(error)):
                h3.H3Info(resolution=resolution)
            return

        actual = h3.H3Info(resolution=resolution)

        assert actual.resolution == resolution

    @pytest.mark.parametrize(
        ["mapping", "expected"],
        (
            ({"resolution": 0}, 0),
            ({"resolution": 1}, 1),
            ({"resolution": -1}, ValueError("resolution must be an integer between")),
        ),
    )
    def test_from_dict(self, mapping, expected):
        if isinstance(expected, Exception):
            with pytest.raises(type(expected), match=str(expected)):
                h3.H3Info.from_dict(mapping)
            return

        actual = h3.H3Info.from_dict(mapping)
        assert actual.resolution == expected

    def test_roundtrip(self):
        mapping = {"grid_name": "h3", "resolution": 0}

        grid = h3.H3Info.from_dict(mapping)
        actual = grid.to_dict()

        assert actual == mapping

    @pytest.mark.parametrize(
        ["resolution", "cell_ids", "expected_coords"],
        (
            (
                1,
                np.array([0x81283FFFFFFFFFF]),
                np.array(
                    [
                        [
                            [-121.70715692, 36.5742183],
                            [-119.00228227, 40.57057179],
                            [-122.13483148, 44.05769081],
                            [-127.95866237, 43.41920841],
                            [-130.22263777, 39.44242422],
                            [-127.13810062, 36.07979648],
                            [-121.70715692, 36.5742183],
                        ]
                    ]
                ),
            ),
            (
                3,
                np.array([0x832831FFFFFFFFF, 0x832832FFFFFFFFF]),
                np.array(
                    [
                        [
                            [-122.99764068, 38.13012709],
                            [-122.63105838, 38.7055711],
                            [-123.06903465, 39.21268153],
                            [-123.87318668, 39.14165748],
                            [-124.23124622, 38.566387],
                            [-123.7937797, 38.06195413],
                            [-122.99764068, 38.13012709],
                        ],
                        [
                            [-120.57845933, 38.30365554],
                            [-120.19218037, 38.87491264],
                            [-120.62501818, 39.3938676],
                            [-121.44467346, 39.33890002],
                            [-121.82297225, 38.76738776],
                            [-121.38971139, 38.25108747],
                            [-120.57845933, 38.30365554],
                        ],
                    ]
                ),
            ),
            (
                2,
                np.array([0x822837FFFFFFFFF, 0x821987FFFFFFFFF, 0x82285FFFFFFFFFF]),
                np.array(
                    [
                        [
                            [-121.70715692, 36.5742183],
                            [-120.15030816, 37.77836118],
                            [-120.62501818, 39.3938676],
                            [-122.69909887, 39.78423084],
                            [-124.23124622, 38.566387],
                            [-123.71598552, 36.97229615],
                            [-121.70715692, 36.5742183],
                        ],
                        [
                            [-21.86089163, 59.14600883],
                            [-24.48971137, 58.33329382],
                            [-24.24608918, 56.81195076],
                            [-21.53679367, 56.10124011],
                            [-18.98719147, 56.88329845],
                            [-19.06702945, 58.40493644],
                            [-21.86089163, 59.14600883],
                        ],
                        [
                            [-132.06227559, 43.79453729],
                            [-130.64994419, 45.0396523],
                            [-131.29015942, 46.41694831],
                            [-133.36750995, 46.52708205],
                            [-134.72528083, 45.27804582],
                            [-134.06255972, 43.92295857],
                            [-132.06227559, 43.79453729],
                        ],
                    ]
                ),
            ),
        ),
    )
    def test_cell_boundaries(self, resolution, cell_ids, expected_coords):
        expected = shapely.polygons(expected_coords)

        grid = h3.H3Info(resolution=resolution)

        actual = grid.cell_boundaries(cell_ids)

        shapely.testing.assert_geometries_equal(actual, expected)


@pytest.mark.parametrize("resolution", resolutions)
@pytest.mark.parametrize("dim", dims)
@pytest.mark.parametrize("cell_ids", cell_ids)
def test_init(cell_ids, dim, resolution):
    grid = h3.H3Info(resolution)
    index = h3.H3Index(cell_ids, dim, grid)

    assert index._grid == grid
    assert index._dim == dim

    # TODO: how do we check the index, if at all?
    assert index._pd_index.dim == dim
    assert np.all(index._pd_index.index.values == cell_ids)


@pytest.mark.parametrize("resolution", resolutions)
def test_grid(resolution):
    grid = h3.H3Info(resolution)

    index = h3.H3Index([0], "cell_ids", grid)

    assert index.grid_info is grid


@pytest.mark.parametrize("variable", variables)
@pytest.mark.parametrize("variable_name", variable_names)
@pytest.mark.parametrize("options", [{}])
def test_from_variables(variable_name, variable, options):
    expected_resolution = variable.attrs["resolution"]

    variables = {variable_name: variable}
    index = h3.H3Index.from_variables(variables, options=options)

    assert index._grid.resolution == expected_resolution
    assert (index._dim,) == variable.dims

    # TODO: how do we check the index, if at all?
    assert (index._pd_index.dim,) == variable.dims
    assert np.all(index._pd_index.index.values == variable.data)


@pytest.mark.parametrize(["old_variable", "new_variable"], variable_combinations)
def test_replace(old_variable, new_variable):
    grid = h3.H3Info(resolution=old_variable.attrs["resolution"])
    index = h3.H3Index(
        cell_ids=old_variable.data,
        dim=old_variable.dims[0],
        grid_info=grid,
    )
    new_pandas_index = PandasIndex.from_variables(
        {"cell_ids": new_variable}, options={}
    )

    new_index = index._replace(new_pandas_index)

    assert new_index._grid == index._grid
    assert new_index._dim == index._dim
    assert new_index._pd_index == new_pandas_index


@pytest.mark.parametrize(
    ["cell_ids", "cell_centers"], list(zip(cell_ids, cell_centers))
)
def test_cellid2latlon(cell_ids, cell_centers):
    grid = h3.H3Info(resolution=3)
    index = h3.H3Index(cell_ids=cell_ids, dim="cells", grid_info=grid)

    actual = index._cellid2latlon(cell_ids)
    expected = cell_centers

    np.testing.assert_allclose(actual, expected)


@pytest.mark.parametrize(
    ["cell_centers", "cell_ids"], list(zip(cell_centers, cell_ids))
)
def test_latlon2cellid(cell_centers, cell_ids):
    grid = h3.H3Info(resolution=3)
    index = h3.H3Index(cell_ids=[0], dim="cells", grid_info=grid)

    actual = index._latlon2cellid(cell_centers[:, 0], cell_centers[:, 1])
    expected = cell_ids

    np.testing.assert_equal(actual, expected)


@pytest.mark.parametrize("max_width", [20, 50, 80, 120])
@pytest.mark.parametrize("resolution", resolutions)
def test_repr_inline(resolution, max_width):
    grid = h3.H3Info(resolution=resolution)
    index = h3.H3Index(cell_ids=[0], dim="cells", grid_info=grid)

    actual = index._repr_inline_(max_width)

    assert f"resolution={resolution}" in actual
    # ignore max_width for now
    # assert len(actual) <= max_width
