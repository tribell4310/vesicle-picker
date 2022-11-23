"""

vesicle_pick_pusher.py

Given:
 + Input set of curated particle picks from cryosparc.
 + Vesicle model originally used to define the particles.
 + Particle-vesicle mapping dictionary.
 + User-specified parameters for the pushing operation.

Output:
 - New set of particle picks with external-topology picks adjusted per user specs.
 - New particle-vesicle mapping dict with the r_eff values adjusted.
 - New histogram showing vesicle diameters for the particles in the subset.

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
	# Parse parameters file
	inModel, inParticles, inCs, box_size_px, px_size, add_dist, set_overlap, push, csJobID = parse_params(params)

	# Unit conversions
	add_dist_px = add_dist / px_size

	# Load vesicles from model
	with open(inModel, "r") as f:
		vesicle_model = json.load(f)

	# Load particles from model
	with open(inParticles, "r") as f:
		particle_model = json.load(f)

	# Load cs file
	cs_file = np.load(inCs)

	# Cryosparc has changed all my particle id's...
	# Cross-correlate particle id's using pick X, Y, and Mcg designations
	particle_corr_dict = id_correlate(csJobID, cs_file, particle_model, vesicle_model)

	# Using correlations, load the associated info from the vesicle and particle models
	for i in range(0, len(cs_file)):
		pass
		# Gather necessary info r_eff and angle info from particle model
		# Do the trig to calculate the new pick coordinates
		# Dynamically output into a new numpy array
		# Write info out into a refreshed particle model

	# Using the new particle and vesicle models, ouput of histogram 
	# for what sized vesicles the particles are in


def id_correlate(csJobID, cs_file, particle_model, vesicle_model):
	""" CS is trying to drive me into an early grave.  I will not allow this. """
	# Define a dictionary that maps new dictionary keys to old dictionary keys.
	corr_dict = {}

	# Create an inverted vesicle model
	inv_ves_model = basic_invert_dict(vesicle_model)

	# Get the starting index for the particle location info
	start_index = infer_index(cs_file)
	print(start_index)

	# Get the corresponding micrograph name
	mcg_index = find_mcg_name(csJobID, cs_file[0])
	print(csJobID)

	# For every particle, pull in the mcg name from the inverted vesicle model
	for particle in particle_model:
		vesicle_id = particle_model[particle]["ves_id"]
		mcg = inv_ves_model[vesicle_id]
		particle_model[particle]["mcg"] = mcg
		particle_model[particle]["mcg_key"] = get_key(mcg)

	# Particle model is now equipped to perform the correlation
	counter = 0
	good_counter = 0
	for i in range(0, len(cs_file)):
		this_entry = cs_file[i]
		mcg_key = get_key(last_slash(this_entry[mcg_index].decode("ascii")))
		x = this_entry[start_index+2]
		y = this_entry[start_index+3]
		new_id = this_entry[start_index]
		
		match_entries = []
		for each_key in particle_model:
			if particle_model[each_key]["mcg_key"] == mcg_key:
				match_entries.append(each_key)
		if len(match_entries) == 0:
			counter += 1
			print(counter, "NO PARTICLE ENTRIES", mcg_key, x, y)
		else:
			good_counter += 1
			
	print("GOOD PARTICLE", good_counter)





	exit()


def get_key(inStr):
	work_str = last_slash(inStr)
	under_loc = work_str.find("_")
	return int(work_str[0:under_loc])


def basic_invert_dict(inDict):
	outDict = {}
	for each_item in inDict.keys():
		for sub_item in inDict[each_item].keys():
			if sub_item not in outDict:
				outDict[sub_item] = each_item

	return outDict


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
	inParticles = items[1][1].strip()
	inCs = items[2][1].strip()
	box_size_px = int(items[3][1].strip())
	if box_size_px < 0:
		print("Check parameters: Box size must be a positive value.")
		kill_flag = True
	px_size = float(items[4][1].strip())
	if px_size < 0:
		print("Check parameters: Pixel size must be a positive value.")
		kill_flag = True
	add_dist = float(items[5][1].strip())
	if add_dist >= 0:
		push = True
	else:
		push = False
	set_overlap = float(items[6][1].strip())
	if (set_overlap > 1.0) or (set_overlap < 0.0):
		print("Check parameters: Pick Box Overlap must be between 0 and 1.")
		kill_flag = True
	job_id = items[7][1].strip()

	# Make sure all params are actually populated
	length_list = []
	length_list.append(len(inModel))
	length_list.append(len(inParticles))
	length_list.append(len(inCs))
	length_list.append(len(str(box_size_px)))
	length_list.append(len(str(px_size)))
	length_list.append(len(str(add_dist)))
	length_list.append(len(str(set_overlap)))
	length_list.append(len(job_id))
	if min(length_list) == 0:
		print("At least one of the required parameters is blank!")
		kill_flag = True

	# Return or kill
	if kill_flag == True:
		print("Please fix the parameters file and try again: "+params)
		exit()
	else:
		return inModel, inParticles, inCs, box_size_px, px_size, add_dist, set_overlap, push, job_id


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