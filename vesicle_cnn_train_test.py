"""

Tristan Bell
Chao Lab
Massachusetts General Hospital

vesicle_cnn_train_test.py

 - Load a user defined vesicle model
 - Load a corresponding set of micrographs
 - Downscale [USER]x
 - Assemble CNN architecture
 - Pass to the CNN
 - Train

"""


import sys
import json
import numpy as np
import mrcfile
#import tensorflow as tf
#from tensorflow import keras
#import matplotlib.pyplot as plt


def main(inModel, inMcgDir, downscaleFactor, length, width):
	# Load model
	with open(inModel, "r") as f:
		vesicle_model = json.load(f)

	# Filter the model to remove anything where the circle center is out of bounds
	x_min = 0
	y_min = 0
	x_max = length
	y_max = width
	filtered_dict = {}
	for item in vesicle_model:
		filtered_dict[item] = {}
		counter = 0
		for vesicle in vesicle_model[item]:
			if center_on_mcg_check(vesicle_model[item][vesicle]["center"], x_min, x_max, y_min, y_max) == True:
				counter += 1
				filtered_dict[item][vesicle] = vesicle_model[item][vesicle]
		if counter == 0:
			del filtered_dict[item]

	# k
	for item in filtered_dict:
		# Generate an output nparray for 


def center_on_mcg_check(coords, x_min, x_max, y_min, y_max):
	x = coords[0]
	y = coords[1]
	if x < x_min:
		return False
	elif x > x_max:
		return False
	elif y < y_min:
		return False
	elif y > y_max:
		return False
	else:
		return True


if __name__ == "__main__":
	if len(sys.argv) == 6:
		main(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]))
	else:
		print("Check usage: python foo.py inModel inMcgDir downscaleFactor mcgLength mcgWidth")
		exit()