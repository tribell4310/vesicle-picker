"""

Tristan Bell
Chao Lab
Massachusetts General Hospital

vesicle_template_match.py


"""


import sys
import json
import numpy as np
import mrcfile
import os
from os import listdir
from os.path import isfile, join
import cv2
from matplotlib import pyplot as plt



def main(inMcgDir, px_size):
	# Load files (start by only doing one)
	if os.path.isdir(inMcgDir) == False:
		print("Can't find specified subdirectory. Exiting...")
		exit()
	onlyfiles = [f for f in listdir(inMcgDir) if (isfile(join(inMcgDir, f)) and f.endswith(".mrc"))]
	
	# Prepare a set of circular mask templates
	masks = []
	for i in range(20, 251):
		if i % 5 == 0:
			masks.append(make_circular_mask(i*5, 2, 200, 200, px_size))
	#cv2.imshow("Blah", masks[10])
	#cv2.waitKey(0)


	counter = 1
	for each_file in onlyfiles:
		# Index-1 counting reporter
		if counter > 1:
			print("Temporary block kills process after one cycle. Goodbye...")
			exit()
		if counter % 10 == 0:
			print(str(counter)+" / "+str(len(onlyfiles)))
		counter += 1

		# Load and invert the template image
		print(each_file)
		all_best_fits = []
		with mrcfile.open(join(inMcgDir, each_file)) as f:
			mask_counter = 0
			for mask in masks:
				active_image = np.asarray(f.data[:] * -1)
				w, h = mask.shape[::-1]

				this_image = active_image.copy()
				method = eval("cv2.TM_CCOEFF")
				res = cv2.matchTemplate(this_image, mask, method)
				min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
				all_best_fits.append(max_val)
				if mask_counter == 23:
					top_left = max_loc
					bottom_right = (top_left[0] + w, top_left[1] + h)
					cv2.rectangle(this_image, top_left, bottom_right, 255, 2)

					plt.subplot(121),plt.imshow(res,cmap = 'gray')
					plt.title('Matching Result'), plt.xticks([]), plt.yticks([])
					plt.subplot(122),plt.imshow(this_image,cmap = 'gray')
					plt.title('Detected Point'), plt.xticks([]), plt.yticks([])
					plt.suptitle("cv2.TM_CCOEFF")
					plt.show()
					#print(min_val)
					#print(min_loc)

				if max_val > 1800000:
					print(mask_counter)
					print(max_val)
					print(max_loc)
					print(" ")
				mask_counter += 1

		# Plot histogram
		#n, bins, patches = plt.hist(all_best_fits, 30)
		#plt.xlabel("max_val")
		#plt.ylabel("frequency")
		#plt.show()



def make_circular_mask(diameter, stroke, mcg_length, mcg_width, px_size):
	# Figure out diameter in pixels
	px_diameter = diameter / px_size
	buffer_size = int(0.75 * px_diameter)
	px_radius = int(px_diameter/2)
	pure_white = (255, 255, 255)

	# Create a scoring catcher
	x_size = mcg_length+(2*buffer_size)
	y_size = mcg_width+(2*buffer_size)
	cc_scores = np.zeros((x_size, y_size))

	# Generate the base mask
	base_mask = np.zeros(((2*px_radius)+(4*int(stroke/2)), (2*px_radius)+(4*int(stroke/2))))
	mask = cv2.circle(base_mask, (px_radius+3, px_radius+3), px_radius, pure_white, stroke)
	mask = cv2.circle(mask, (px_radius+3, px_radius+3), px_radius-5, pure_white, stroke)

	return mask.astype("float32")

	# Move the circle across the map and generate a score.
	# My brute-force strategy here is slow as shit, probably need to algorithmically downsample then targeted fit
	#for i in range(0, x_size):
	#	if i % 20 == 0:
	#		print("\t"+str(i))
	#	for j in range(0, y_size):
	#		mask = cv2.circle(base_mask, (px_radius+i, px_radius+j), px_radius, pure_white, stroke)
	#		cropped_mask = mask[buffer_size:mcg_length+buffer_size, buffer_size:mcg_width+buffer_size]
	#		cc_scores[i, j] = cv2.TM_CCOEFF
	#print(cc_scores)

	

	# Display
	#cv2.imshow("Blah", base_mask)
	#cv2.waitKey(0)





	


if __name__ == "__main__":
	if len(sys.argv) == 3:
		main(sys.argv[1], float(sys.argv[2]))
	else:
		print("Check usage: python foo.py inMcgDir pxSize")
		exit()