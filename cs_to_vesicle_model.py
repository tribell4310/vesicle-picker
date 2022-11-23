"""
Tristan Bell
Chao Lab
Massachusetts General Hospital

cs_to_vesicle_model.py

This script takes a cryosparc .cs file for particles or particle passthrough and exports the particle coordinates to a
csv file containing vesicle center (x,y) and vesicle radius.
Write out the model as  json with suffix "_vesicledata.json"

"""

import sys
import numpy as np
import json
import os
from os import listdir
from os.path import isfile, join
import math
import statistics


def main(csJobID, inCs):
	# Check for the Vesicle_data subdirectory
	if os.path.isdir("./Vesicle_data") == False:
		os.mkdir("./Vesicle_data")
	else:
		print("\nDetected a Vesicle_data folder in this directory.")
	onlyfiles = [f for f in listdir("./Vesicle_data/") if isfile(join("./Vesicle_data", f))]

	coord_dict = {}
	out_dict = {}

	# Read in the cs file as a np array
	f = np.load(inCs)

	# Get the starting index for the particle location info
	start_index = infer_index(f)

	# Get the corresponding micrograph name
	mcg_index = find_mcg_name(csJobID, f[0])
	
	# Load the particles into a dictionary.  Particles batched in groups of three defined by order clicked.
	for i in range(0, len(f)):
		if last_slash(str(f[i][mcg_index])).replace("'", "").replace('"', '') not in coord_dict:
			coord_dict[last_slash(str(f[i][mcg_index])).replace("'", "").replace('"', '')] = {}
		if int(i/3) not in coord_dict[last_slash(str(f[i][mcg_index])).replace("'", "").replace('"', '')]:
			coord_dict[last_slash(str(f[i][mcg_index])).replace("'", "").replace('"', '')][int(i/3)] = []
		
		# Calculate transformed x and y coords
		h = f[i][start_index+1][0]
		l = f[i][start_index+1][1]
		x_frac = f[i][start_index+2]
		y_frac = f[i][start_index+3]
		x_coord = round((l*x_frac), 0)
		y_coord = round((h*y_frac), 0)

		# Add to dictionary
		coord_dict[last_slash(str(f[i][mcg_index])).replace("'", "").replace('"', '')][int(i/3)].append((x_coord, y_coord))

		# To every coordinate set, add mcg_l, mcg_w, and box info
		if i % 3 == 2:
			# Grab parameters
			mcg_l, mcg_w, box = get_sizes(f[i])
			# Add to dictionary
			coord_dict[last_slash(str(f[i][mcg_index])).replace("'", "").replace('"', '')][int(i/3)].append(mcg_l)
			coord_dict[last_slash(str(f[i][mcg_index])).replace("'", "").replace('"', '')][int(i/3)].append(mcg_w)
			coord_dict[last_slash(str(f[i][mcg_index])).replace("'", "").replace('"', '')][int(i/3)].append(box)

	# Apply geometry to get circles
	for thing in coord_dict:
		if thing not in out_dict:
			out_dict[thing] = {}
		for item in coord_dict[thing]:
			if item not in out_dict[thing]:
				out_dict[thing][item] = {}
			center, radius = circle_three_points(coord_dict[thing][item][0], coord_dict[thing][item][1], coord_dict[thing][item][2])
			out_dict[thing][item]["center"] = center
			out_dict[thing][item]["radius"] = radius
			out_dict[thing][item]["mcg_h"] = coord_dict[thing][item][3]
			out_dict[thing][item]["mcg_w"] = coord_dict[thing][item][4]
			out_dict[thing][item]["box_size"] = coord_dict[thing][item][5]

	# Write out to json
	with open("./Vesicle_data/"+no_ext(inCs)+".json", "w") as g:
		json.dump(out_dict, g)

	# Exit
	print("\nProcessed "+str(int(len(f)/3))+" vesicles.")
	print("\nVesicle data output to ./Vesicle_data/"+no_ext(inCs)+".json")
	print("\n...done.")


def get_sizes(inCs):
	# Get the first two items that are numpy arrays
	array_counter = 0
	for i in range(0, len(inCs)):
		if isinstance(inCs[i], np.ndarray) == True:
			array_counter += 1
			if array_counter == 1:
				first_array = inCs[i]
			elif array_counter == 2:
				second_array = inCs[i]
		if array_counter == 2:
			break

	# Extract data and return
	mcg_h = int(second_array[0])
	mcg_w = int(second_array[1])
	box = int(first_array[0])
	return mcg_h, mcg_w, box


def circle_three_points(A, B, C):
	# Define the slopes and intercepts of the perpendicular bisectors of vectors AB and BC
	m_perpAB, b_perpAB = perp_bisect(A, B)
	m_perpBC, b_perpBC = perp_bisect(B, C)

	# Determine the intersection of the perpendicular bisectors, this is the *origin*
	origin = get_intersection(m_perpAB, b_perpAB, m_perpBC, b_perpBC)

	# Find the euclidian distance between the origin and A, this is the *radius* 
	radius = int(round(statistics.mean([get_euclidian_distance(A, origin), get_euclidian_distance(B, origin), get_euclidian_distance(C, origin)]), 0))

	return origin, radius


def perp_bisect(A, B):
	# If the y-vals are the same, we get meaningless values.  Have to add a pseudocount.
	if A[1] == B[1]:
		B = (B[0], (B[1]+0.0001))
	if A[0] == B[0]:
		B = ((B[0]+0.0001), B[1])

	# Define slope and intercept for vector AB
	m = (B[1] - A[1]) / (B[0] - A[0])
	b = A[1] - (m * A[0])

	# Slope of perpendicular is inverse reciprocal
	m_perp = -1 / m

	# Find the midpoint of AB
	midpoint_x = (A[0] + B[0]) / 2
	midpoint_y = (A[1] + B[1]) / 2

	# Find the intercept that fulfills the midpoint and the known slope
	b_perp = midpoint_y - (m_perp * midpoint_x)

	return m_perp, b_perp


def get_intersection(m1, b1, m2, b2):
	x_int = (b2 - b1) / (m1 - m2)
	y_int = (m1 * x_int) + b1
	return (int(round(x_int, 0)), int(round(y_int, 0)))


def get_euclidian_distance(A, B):
	y1 = A[1]
	y2 = B[1]
	x1 = A[0]
	x2 = B[0]
	return math.sqrt((y2-y1)**2 + (x2-x1)**2)


def parse_star(inMcgs):
	# Open file
	f = open(inMcgs, "r")
	lines = f.readlines()

	# Find the position of "_rlnMicrographName" in the star file loop definition
	for i in range(0, len(lines)):
		if "loop_" in lines[i]:
			loop_start = i
			for j in range(i+1, len(lines)):
				if "_rlnMicrographName" in lines[j]:
					parse_pos = int(lines[j][lines[j].find("#")+1:])-1
					break

	# Isolate the micrograph name from each line of the star file
	mcgs = []
	for i in range(loop_start+1, len(lines)):
		if lines[i][0] != "_":
			mcgs.append(last_slash(lines[i].split(" ")[parse_pos]))
	return mcgs


def mcg_find_suffix(full_list, start_ind):
	# Take the substring from the start of mcg name to end of the full cryosparc name
	names_list = []
	for i in range(0, len(full_list)):
		names_list.append(full_list[i][start_ind:])
	
	# Leftpad all names to the same length
	max_len = 0
	for i in range(0, len(names_list)):
		if len(names_list[i]) > max_len:
			max_len = len(names_list[i])
	same_len_names = []
	for i in range(0, len(names_list)):
		temp_str = names_list[i]
		if len(names_list[i]) < max_len:
			while len(temp_str) < max_len:
				temp_str = " "+temp_str
		same_len_names.append(temp_str)

	# Make an invariance matrix
	const_matrix = get_constant_matrix(same_len_names)

	# Working backwards, find the first True-False transition
	for i in range(1, len(const_matrix)):
		if const_matrix[-i] == True:
			if const_matrix[-(i+1)] == False:
				end_index = -i
				break

	return same_len_names[0][end_index:]


def get_constant_matrix(mcg_names):
	constant_container = []
	for i in range(0, len(mcg_names[0])):
		is_constant = True
		for j in range(1, len(mcg_names)):
			try:
				if len(mcg_names[j][i]) == len(mcg_names[0][i]):
					if len(mcg_names[j-1][i]) == len(mcg_names[0][i]):
						if mcg_names[j][i] != mcg_names[j-1][i]:
							is_constant = False
							break
			except:
				pass
		constant_container.append(is_constant)
	
	return constant_container


def infer_index(np_array):
	# Defined pattern is binary string, list of two ints >1000, float <= 1, float <=1
	for i in range(0, len(np_array[1])):
		try:
			np_array[1][i].decode("utf-8")
			try:
				a = len(np_array[1][i+1])
				if np_array[1][i+2] < 1:
					if np_array[1][i+3] < 1:
						startInd = i
						break
			except:
				pass
		except:
			pass
	return startInd


def find_mcg_name(query, np_array):
	""" Return index of cs numpy array that contains the micrograph info"""
	for i in range(0, len(np_array)):
		try:
			if query in str(np_array[i]):
				return i
		except:
			pass


def line_writer(x, y):
	# Process x and y
	padded_x = leftpad(x, 12)
	padded_y = leftpad(y, 12)
	remainder = "     0.080000            0     0.000000 \n"
	return (padded_x + " " + padded_y + remainder)


def leftpad(inStr, final_len):
	while len(inStr) < final_len:
		inStr = " "+inStr
	return inStr


def no_dot(inStr):
	"""
	Relion converts "." in cryoparc names to "_" - this function takes a script and performs this
	conversion prior to name-matching.
	"""
	return inStr.replace(".", "_")


def no_ext(inStr):
	"""
	Takes an input filename and returns a string with the file extension removed.
	"""
	prevPos = 0
	currentPos = 0
	while currentPos != -1:
		prevPos = currentPos
		currentPos = inStr.find(".", prevPos+1)
	return inStr[0:prevPos]


def last_slash(inStr):
	"""
	Returns the component of a string past the last forward slash character.
	"""
	prevPos = 0
	currentPos = 0
	while currentPos != -1:
		prevPos = currentPos
		currentPos = inStr.find("/", prevPos+1)
	return inStr[prevPos+1:]


def clean_large_numbers(inInt):
	"""
	Takes an integer and re-formats to string with human-readable comma-spaced numbers.
	"""
	inStr = str(inInt)
	outStr = ""
	
	if len(inStr) > 3:
		for i in range(1, len(inStr)+1):
			outStr = inStr[-i] + outStr
			if i % 3 == 0:
				outStr = "," + outStr
	else:
		outStr = inStr

	if outStr[0] == ",":
		return outStr[1:]
	else:
		return outStr


if __name__ == "__main__":
	if len(sys.argv) == 3:
		main(sys.argv[1], sys.argv[2])
	else:
		print("Check usage: python foo.py csparcJobID /path/to/your/cryosparc/particles/file.cs")
		exit()