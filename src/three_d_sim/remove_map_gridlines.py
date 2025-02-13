# Example of how to run:
#     cd /home/keegan_green/Dropbox/Documents/Projects/green_airliner/ && python /home/keegan_green/Dropbox/Documents/Projects/green_airliner/src/three_d_sim/remove_map_gridlines.py

import cv2

map = cv2.imread("../green_airliner/local/map/Miller_projection_SW-tessellated-vert_distortion_removed-cropped_to_pm_200deg_around_jfk_lax_centroid-fixed.png")
gridlines_mask = cv2.imread("../green_airliner/local/map/remove_gridlines_mask.png")[:, :, 0]
map_without_gridlines = cv2.inpaint(map, gridlines_mask, 3, cv2.INPAINT_TELEA)
cv2.imwrite("../green_airliner/local/map/Miller_projection_SW-tessellated-vert_distortion_removed-cropped_to_pm_200deg_around_jfk_lax_centroid-fixed-gridlines_removed.png", map_without_gridlines)
