from typing import List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

l = lambda _m, _b: lambda x: _m * x + _b

m = lambda p_a, p_b: (p_b - p_a)[1] / (p_b - p_a)[0]  # slope of a line
b = lambda p_a, p_b: p_a[1] - p_a[0] * m(p_a, p_b)  # y-intercept of a line


def _check_if_point_along_line(
    line_point_a: np.ndarray, line_point_b: np.ndarray, other_point: np.ndarray
) -> bool:
    line_m = m(line_point_a, line_point_b)  # slope
    line_b = b(line_point_a, line_point_b)  # y-intercept
    line = l(line_m, line_b)
    return np.isclose(other_point[1], line(other_point[0]))


def _check_if_point_along_ray(
    ray_anchor_point: np.ndarray, ray_through_point: np.ndarray, other_point: np.ndarray
) -> bool:
    if not _check_if_point_along_line(ray_anchor_point, ray_through_point, other_point):
        return False
    # ray_m = m(ray_anchor_point, ray_through_point)
    # orthogonal_line = l(_m=(-1 / ray_m), _b=(ray_anchor_point[1] - ray_m * ray_anchor_point[0]))
    if ray_anchor_point[0] < ray_through_point[0]:
        if ray_anchor_point[0] <= other_point[0]:
            return True
    elif ray_through_point[0] < ray_anchor_point[0]:
        if other_point[0] <= ray_anchor_point[0]:
            return True
    else:
        raise NotImplementedError
    return False


def generate_planar_curve_points(
    p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, R: float, plot: bool = False
) -> List[np.ndarray]:
    ### lines 12 and 23

    m_12 = m(p1, p2)
    m_23 = m(p2, p3)

    b_12 = b(p1, p2)
    b_23 = b(p2, p3)

    l_12 = l(m_12, b_12)
    l_23 = l(m_23, b_23)

    ### signs corresponding to lines 12 and 23

    s_12 = np.array([1, 1, -1, -1])
    s_23 = np.array([1, -1, -1, 1])

    ### offset lines 12 and 23

    b_o = lambda _s, _m, _b: _s * R * np.sqrt(_m**2 + 1) + _b
    b_o12 = b_o(s_12, m_12, b_12)
    b_o23 = b_o(s_23, m_23, b_23)

    ### circle centerpoint = intersection of offset lines 12 and 23

    c_x = (b_o23 - b_o12) / (m_12 - m_23)
    l_o12 = l(m_12, b_o12)
    c_y = l_o12(c_x)
    c = np.array([c_x, c_y])

    ### intersection points of circle with lines 12 and 23

    # parameters of quadratic eq:
    A = lambda m, b: 1 + m**2
    B = lambda m, b: 2 * ((b - c_y) * m - c_x)
    C = lambda m, b: c_x**2 + (b - c_y) ** 2 - R**2
    # quadratic formula:
    q = lambda a, b, c: -b / (2 * a)  # (-b + np.sqrt(b**2 - 4 * a * c)) / (2 * a)
    Q = lambda m, b: q(a=A(m, b), b=B(m, b), c=C(m, b))
    # solutions to quadratic equation:
    i_12x = Q(m_12, b_12)
    i_23x = Q(m_23, b_23)
    # intersection points of circle with lines 12 and 23:
    i_12y = l_12(i_12x)
    i_23y = l_23(i_23x)
    i_12 = np.array([i_12x, i_12y])
    i_23 = np.array([i_23x, i_23y])

    ###

    solutions_df = pd.DataFrame([[*i_12.T], [*i_23.T], [*c.T]]).T
    solutions_df.columns = ["i_12", "i_23", "c"]
    solutions_df.index.name = "solution_idx"

    for idx, solution in solutions_df.iterrows():
        solutions_df.loc[idx, "i_12_along_ray_21"] = _check_if_point_along_ray(
            ray_anchor_point=p2, ray_through_point=p1, other_point=solution.i_12
        )
        solutions_df.loc[idx, "i_23_along_ray_23"] = _check_if_point_along_ray(
            ray_anchor_point=p2, ray_through_point=p3, other_point=solution.i_23
        )

    solution = solutions_df[
        solutions_df["i_12_along_ray_21"] & solutions_df["i_23_along_ray_23"]
    ].iloc[0]
    i_12 = solution["i_12"]
    i_23 = solution["i_23"]
    c = solution["c"]

    angle_c1 = np.arctan2((i_12 - c)[1], (i_12 - c)[0])
    angle_c3 = np.arctan2((i_23 - c)[1], (i_23 - c)[0])

    arc_angles = np.linspace(angle_c1, angle_c3)

    arc_points = (
        c
        + R
        * np.c_[
            np.cos(arc_angles),
            np.sin(arc_angles),
        ]
    )

    if plot:
        plt.plot(*np.array([p1, p2, p3]).T, "o")
        plt.plot(*c, "o")
        plt.plot(*i_12, "o")
        plt.plot(*i_23, "o")
        plt.plot(*np.c_[p1, arc_points.T, p3])
        plt.show()

    return [*arc_points]


if __name__ == "__main__":
    ### inputs
    R = 2.3
    # points 1, 2, and 3:
    p1 = np.array([-4.66, 0.2])
    p2 = np.array([2.05, 3.48])
    p3 = np.array([9.07, -0.5])

    arc_points = generate_planar_curve_points(p1, p2, p3, R, plot=True)
