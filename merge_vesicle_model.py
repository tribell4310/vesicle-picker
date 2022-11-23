"""

Tristan Bell
Chao Lab
Massachusetts General Hospital

merge_vesicle_model.py

Looks for a directory called "Vesicle_data" and merges all the models there into a 
single model json file.  Outputs to ./Vesicle_data/vesicle_model_merged.json


"""


import sys
import os
from os import listdir
from os.path import isfile, join
import numpy as np
import json


def main():
	# Check for the Vesicle_data subdirectory and delete any contents
	if os.path.isdir("./Vesicle_data") == False:
		print("No Vesicle_data directory detected.  Exiting...")
		exit()

	# Get the existing model files
	onlyfiles = [f for f in listdir("./Vesicle_data/") if (isfile(join("./Vesicle_data", f)) and f.endswith(".json"))]

	# Load and merge them one by one
	new_dict = {}
	for each_file in onlyfiles:
		print(each_file)
		with open("./Vesicle_data/"+each_file, "r") as f:
			this_dict = json.load(f)
			new_dict.update(this_dict)

	# Dump new_dict
	with open("./Vesicle_data/vesicle_model_merged.json", "w") as g:
		json.dump(new_dict, g)


if __name__ == "__main__":
	if len(sys.argv) == 1:
		main()
	else:
		print("Check usage: python foo.py")
		exit()
