"""

vesicle_procedural_pick.py

Given:
 - A vesicle model input file
 - Box size
 - Pixel size
 - Distance from vesicle edge
 - Desired box overlap
 - input CS pick file to use as a template for output

Return:
 - Cryosparc-formatted set of particle picks filtered to remove problem edge cases

Hardcoded to assume all input micrographs are the same size.

"""


import sys
import os
import shutil
import json
import numpy as np 
from matplotlib import pyplot as plt
import math
from math import pi, sin, cos
from random import randint


def main(params):
	# Parse input parameters
	inModel, inCs, box_size_px, px_size, add_dist, set_overlap, set_internal_pick = parse_params(params)

	# Unit conversions
	add_dist_px = add_dist / px_size

	# Load vesicles from model
	with open(inModel, "r") as f:
		vesicle_model = json.load(f)

	# For every mcg, generate a set of particle picks for every vesicle
	print("Picking...")
	all_radii_px = []
	new_picks = {}
	particle_offset = 0
	counter = 1
	for mcg in vesicle_model:
		if counter % 100 == 0:
			print("\t"+str(counter)+" / "+str(len(vesicle_model.keys()))+" micrographs...")
		counter += 1
		for vesicle in vesicle_model[mcg]:
			all_radii_px.append(vesicle_model[mcg][vesicle]["radius"])
			# Generate a set of picks (and filter for edges)
			new_picks, particle_offset = autopick(new_picks, box_size_px, add_dist_px, vesicle_model[mcg][vesicle]["center"][0], vesicle_model[mcg][vesicle]["center"][1], vesicle_model[mcg][vesicle]["radius"], set_overlap, mcg, vesicle_model[mcg][vesicle]["mcg_w"], vesicle_model[mcg][vesicle]["mcg_h"], particle_offset, vesicle, set_internal_pick)
			mcg_h = vesicle_model[mcg][vesicle]["mcg_h"]
			mcg_w = vesicle_model[mcg][vesicle]["mcg_w"]

	
	# Convert the pick coordinates into crysparc format - 0-1 float fraction of length, width
	new_picks_cs = {}
	for mcg in new_picks:
		new_picks_cs[mcg] = []
		for pick in new_picks[mcg]:
			new_picks_cs[mcg].append(convert_to_cs(pick, mcg_w, mcg_h))

	
	# Now need to spoof a cs picking output - god help us this could be rough
	# Load the input file as a template
	# I need to find a specific template per-mcg to keep the other factors correct
	cs_template = np.load(inCs)
	cs_array, particle_vesicle_map_dict = spoofer(cs_template, new_picks_cs, mcg_h, mcg_w, box_size_px)

	# Write out new cs file
	np.save("_temp.npy", cs_array)
	shutil.copy2("_temp.npy", no_ext(inModel)+"_particlesOut.cs")
	os.remove("_temp.npy")
	print("\t"+str(len(cs_array))+" particles output to file.")

	# Write out the particle-vesicle mapping dictionary as a json
	if os.path.isdir("./Particle_data") == False:
		os.mkdir("./Particle_data")
	with open("./Particle_data/"+no_ext(last_slash(inModel))+"_particles.json", "w") as g:
		json.dump(particle_vesicle_map_dict, g)

	# Vesicle histogram block
	print("Outputting vesicle distribution plot...")
	all_radii_nm = []
	all_diam_nm = []
	for i in range(0, len(all_radii_px)):
		all_radii_nm.append(px_size * all_radii_px[i] / 10)
		all_diam_nm.append(2 * px_size * all_radii_px[i] / 10)
	n, bins, patches = plt.hist(all_diam_nm, 30)
	plt.xlabel("Vesicle diameter (nm)")
	plt.ylabel("frequency")
	plt.savefig(no_ext(inModel)+"_distribution.png")

	print("\t...done.")


def parse_params(params):
	# Load and read csv input
	kill_flag = False
	with open(params, "r") as f:
		lines = f.readlines()
		items = []
		for i in range(0, len(lines)):
			items.append(lines[i].split(","))
	
	# Item definitions
	inModel = items[0][1].strip()
	inCs = items[1][1].strip()
	box_size_px = int(items[2][1].strip())
	if box_size_px < 0:
		print("Check parameters: Box size must be a positive value.")
		kill_flag = True
	px_size = float(items[3][1].strip())
	if px_size < 0:
		print("Check parameters: Pixel size must be a positive value.")
		kill_flag = True
	add_dist = float(items[4][1].strip())
	set_overlap = float(items[5][1].strip())
	if (set_overlap > 1.0) or (set_overlap < 0.0):
		print("Check parameters: Pick Box Overlap must be between 0 and 1.")
		kill_flag = True
	if items[6][1].strip() in ["Y", "y"]:
		set_internal_pick = True
	else:
		set_internal_pick = False

	# Make sure all params are actually populated
	length_list = []
	length_list.append(len(inModel))
	length_list.append(len(inCs))
	length_list.append(len(str(box_size_px)))
	length_list.append(len(str(px_size)))
	length_list.append(len(str(add_dist)))
	length_list.append(len(str(set_overlap)))
	if min(length_list) == 0:
		print("At least one of the required parameters is blank!")
		kill_flag = True

	# Return or kill
	if kill_flag == True:
		print("Please fix the parameters file and try again: "+params)
		exit()
	else:
		return inModel, inCs, box_size_px, px_size, add_dist, set_overlap, set_internal_pick


def spoofer(template, pick_dict, mcg_h, mcg_w, box):
	"""
	Needs to adjust the following indeces from template:
	   0  Particle identifier - 19-digit random int, starting with a 9
	*  1  Particle picking job - as ascii-encoded bytestring
	   3  Box size - user-specified, 2x1 ndarray
	*  4  Pixel size - user-specified, float
	*  7  Source mcg key - integer
	*  9  Source micrograph from motion correction - ascii-encoded bytestring
	* 10  Mcg size - 2x1 ndarray [mcg_h mch_w]
	  11  Pick location in y - float
	  12  Pick location in x - float

	* Features that can pass through directly from an appropriate template

	"""
	print("Converting to cs coords...")
	# Create a dict to map the micrographs to their first index in template array
	map_dict = {}
	for i in range(0, len(template)):
		this_key = template[i][7]
		if this_key not in map_dict:
			map_dict[this_key] = i

	# Create a dictionary to correlate particles with vesicles and picking data
	particle_vesicle_map_dict = {}
	for mcg in pick_dict:
		for each_pick in pick_dict[mcg]:
			particle_vesicle_map_dict[each_pick[2]] = {}
			particle_vesicle_map_dict[each_pick[2]]["x"] = each_pick[0]
			particle_vesicle_map_dict[each_pick[2]]["y"] = each_pick[1]
			particle_vesicle_map_dict[each_pick[2]]["ves_id"] = each_pick[3]
			particle_vesicle_map_dict[each_pick[2]]["angle"] = each_pick[4]
			particle_vesicle_map_dict[each_pick[2]]["r_eff"] = each_pick[5]
			particle_vesicle_map_dict[each_pick[2]]["topology"] = each_pick[6]

	# Get total number of picks
	all_picks = 0
	for mcg in pick_dict:
		for pick in pick_dict[mcg]:
			all_picks += 1

	# Iteration cycle - generate a cs item for every pick
	spoof_arrays = []
	for mcg in pick_dict:
		# Grab the appropriate template
		specific_template = template[map_dict[get_key(mcg)]]
		# Mod for each pick
		for pick in pick_dict[mcg]:
			cs_pick = specific_template.copy()

			# Index 0 - 19-digit particle ID
			cs_pick[0] = pick[2]

			# Index 1 - Particle Name
			#particle_name = cs_pick[1].decode("ascii")
			#slash_loc = last_slash_loc(particle_name)
			#prefix = particle_name[0:last_slash_loc+1]

			# Index 3 - Box size
			cs_pick[3] = np.asarray([box, box])

			# Index 11 and 12 - pick locations in y and x, respectively
			cs_pick[11] = pick[0]
			cs_pick[12] = pick[1]

			# Load onto list
			spoof_arrays.append(cs_pick)

	# Convert list to numpy array
	spoof_array = np.array(spoof_arrays)

	return spoof_array, particle_vesicle_map_dict


def get_key(inStr):
	work_str = last_slash(inStr)
	under_loc = work_str.find("_")
	return int(work_str[0:under_loc])


def convert_to_cs(pick, w, h):
	x = pick[0]
	y = pick[1]
	new_x = x / w
	new_y = y / h
	return(new_x, new_y, pick[2], pick[3], pick[4], pick[5], pick[6])


def autopick(pick_dict, box_size_px, add_dist, x, y, r, user_overlap, in_mcg, mcg_w, mcg_h, particle_offset, vesicle, set_internal_pick):
	""" Given the effective radius, box_size, and overlap, figure out how to acheive the necessary overlap """
	
	# Distance from center of circle to center of pick, pre-calculations
	r_eff = r + add_dist
	box_area_px = box_size_px ** 2

	# Given the desired radius, place three boxes, then increase the number until the overlap
	# is where the user wants it
	div = 2
	calc_overlap = float(0)
	while calc_overlap < user_overlap:
		div += 1
		picks = []

		# At this div setting, define coords for every box at this position as tuples -> picks list
		alpha = 2 * pi / div
		for i in range(0, div):	
			angle = i * alpha
			l_T = r_eff * cos(angle)
			h_T = -1 * r_eff * sin(angle)
			pick_x = x + l_T# - box_size_px/2
			pick_y = y + h_T# - box_size_px/2
			# Pass forward as (x, y, partID, vesID, angle, r_eff, topology)
			picks.append((pick_x, pick_y, 9000000000000000000+particle_offset, vesicle, angle, r_eff, "external"))
			particle_offset += 1

		# Calculate overlap between the first two boxes in the pick list
		calc_overlap = get_overlap(int(picks[0][0]), int(picks[0][1]), int(picks[1][0]), int(picks[1][1]), box_size_px, box_area_px)

	# picks now contains the coords of new picks.
	filtered_picks = filter_picks(picks, box_size_px, mcg_w, mcg_h)

	# Add filtered output to the pick dictionary and send back
	if in_mcg not in pick_dict:
		pick_dict[in_mcg] = []
	for pick in filtered_picks:
		pick_dict[in_mcg].append(pick)

	# Recursion loop for internal templated picking
	if set_internal_pick == True:
		recursion_flag = False
		if div > 3:
			new_radius = r - (box_size_px * (1 - user_overlap))
			new_picks, particle_offset = autopick(pick_dict, box_size_px, add_dist, x, y, new_radius, user_overlap, in_mcg, mcg_w, mcg_h, particle_offset, vesicle, set_internal_pick)

	return pick_dict, particle_offset


def get_overlap(x1, y1, x2, y2, box_size, box_area):
	# Define pick square edges
	x1_1 = x1 - (box_size/2)
	x1_2 = x1 + (box_size/2)
	y1_1 = y1 - (box_size/2)
	y1_2 = y1 + (box_size/2)
	x2_1 = x2 - (box_size/2)
	x2_2 = x2 + (box_size/2)
	y2_1 = y2 - (box_size/2)
	y2_2 = y2 + (box_size/2)

	# Exit if there is no overlap
	if (x1_2 <= x2_1) or (y1_2 <= y2_1):
		return float(0)
	else: # Calculate if we know we have overlap
		overlap_area = (x1_2 - x2_1) * (y1_2 - y2_1)
		return ((2*box_area) - overlap_area) / box_area


def filter_picks(picks, box_size, mcg_w, mcg_h):
	# Define upper and lower bounds in x and y for picks
	min_x = 0
	min_y = 0
	max_x = mcg_w - box_size
	max_y = mcg_h - box_size
	
	# Filter!
	out_picks = []
	for pick in picks:
		if (pick[0] > min_x):
			if (pick[0] < max_x):
				if (pick[1] > min_y):
					if (pick[1] < max_y):
						out_picks.append(pick)

	return out_picks


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


def last_slash_loc(inStr):
	"""
	Returns the location of the last forward slash character.
	"""
	prevPos = 0
	currentPos = 0
	while currentPos != -1:
		prevPos = currentPos
		currentPos = inStr.find("/", prevPos+1)
	return currentPos


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


if __name__ == "__main__":
	if len(sys.argv) == 2:
		main(sys.argv[1])
	else:
		print("Check usage: python foo.py params.csv")
		exit()
