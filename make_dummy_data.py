"""

make_dummy_data.py

This creates fake noise micrographs in mrc formt as dummy data to validate that the cnn script
is handling data correctly.

Native images are 4092x5760.
Fill MRCs with random noise between -20 and 20 (signed floats)


"""


import sys
import numpy as np
import json
import os
from os import listdir
from os.path import isfile, join
import random
import mrcfile


def main(inModel):
	# Make a fake data directory
	if os.path.isdir("./Fake_data") == False:
		os.mkdir("./Fake_data")
	else:
		print("\nDetected a Fake_data folder in this directory.")

	# Load the model as json
	with open(inModel, "r") as f:
		model_dict = json.load(f)

	# Generate a fake image for each and save it
	total_items = len(model_dict)
	counter = 1
	for item in model_dict:
		if counter % 10 == 0:
			print(str(counter)+" / "+str(total_items))
		gen_fake_image(4092, 5760, 25, item)
		counter += 1


def gen_fake_image(l, w, max, name):
	# Generate randomized np array from -max to +max
	seed = random.randint(0, 99999)
	fake_array = np.random.default_rng(seed).random((l, w))
	scaled_fake_array = ((fake_array - 0.5 ) * max * 2).astype("float32")

	# Write out
	with mrcfile.new(join("Fake_data", name), overwrite=True) as mrc:
		mrc.set_data(scaled_fake_array)


if __name__ == "__main__":
	if len(sys.argv) == 2:
		main(sys.argv[1])
	else:
		print("Check usage: python foo.py inModel")
		exit()