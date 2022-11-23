"""

qc_cs_picks.py

Take a pdf event log report from cryosparc manual picking and identify images where cryosparc deleted one or
more of my picks because it was too close to an edge.

Also take in the cryosparc picking data for that manual pick job.

Output two items:

First, a text list of images where particles were deleted (or problem detected) for my use later.

Second, a version of the picking data that keeps everything in the same order, but excludes any particles 
from the problem images.


"""

import os
import sys
import pdfplumber
import numpy as np


def main(inPdf, inCs, csJobID):
	# Load the pdf file and extract text
	pdf = pdfplumber.open(inPdf)
	pages = pdf.pages[:]
	collate_str = ""
	print("loading pdf page by page")
	counter = 1
	for page in pages:
		if counter % 10 == 0:
			print(str(counter)+" / "+str(len(pages)))
		counter += 1
		text = page.extract_text()
		collate_str += text

	#with open("blah.txt", "w") as g:
	#	g.write(collate_str)

	#with open("blah.txt", "r") as f:
	#	print("Skipping pdf read, loading from cache. Remove this before publishing!")
	#	collate_str = f.read()

	# Split the text into a list of lines
	raw_lines = collate_str.split(">")
	lines = []
	for i in range(0, len(raw_lines)):
		lines.append(raw_lines[i].replace("\n", ""))

	# Find the reference to every micrograph ("Extracting from") and run QC
	problems = []
	for i in range(0, len(lines)):
		if "Extracting from" in lines[i]:
			#print(lines[i])
			result = qc_pdf_line(lines[i]) #True/False for good/bad
			if result == False:
				part_string = last_slash(lines[i])
				problems.append(part_string[0:part_string.find(" : ")].strip())

	# Write out the list in order
	corr_dict = {}
	for i in range(0, len(problems)):
		under_loc = problems[i].find("_")
		corr_dict[int(problems[i][0:under_loc])] = problems[i]
	raw_keys = list(corr_dict.keys())
	all_keys = sorted(raw_keys)
	with open(no_ext(inPdf)+"_problems.txt", "w") as g:
		for i in range(0, len(all_keys)):
			g.write(corr_dict[all_keys[i]]+"\n")

	# Everything is working to this point
	# Next, need to go through the cryosparc array and remove particles for those images.
	# Read in the cs file as a np array
	f = np.load(inCs)

	# Get the starting index for the particle location info
	start_index = infer_index(f)

	# Get the corresponding micrograph name
	mcg_index = find_mcg_name(csJobID, f[0])

	# Nested for loop (O(mn)...) to eliminate bad items
	clean_particle_catcher = []

	for i in range(0, len(f)): #THIS IS WHERE THE LOGIC IS FAILING, EVERYTHING ELSE WORKS STRUCTURALLY
		is_problem = False
		# Get the key value for comparison
		working_name = last_slash(f[i][start_index].decode("ascii"))[0:last_slash(f[i][start_index].decode("ascii")).find("_")]
		key_val = int(working_name)
		if key_val in all_keys:
			clean_particle_catcher.append(0)
		else:
			clean_particle_catcher.append(1)
	
	# Regenerate a new array using just the "keep" particles
	mask = np.asarray(clean_particle_catcher)
	clean_particles = f[mask.astype(bool)]

	# Write out
	np.save("_temp.npy", clean_particles)
	os.rename("_temp.npy", no_ext(inCs)+"_particleSubset.cs")
	print("...done.  Wrote out bad problem micrographs and a subset particle file.")
	

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


def qc_pdf_line(inLine):
	#print(inLine)
	# Find the relevant portion
	colon_loc = last_colon(inLine)

	# Parse this to get the number of particles and rejects
	particles_loc = inLine.find(" particles", colon_loc)
	#print(colon_loc)
	#print(particles_loc)
	particles_accepted = int(inLine[colon_loc+2:particles_loc])
	paren_loc = inLine.find("(", particles_loc)
	reject_loc = inLine.find(" rejected", paren_loc)
	particles_rejected = int(inLine[paren_loc+1:reject_loc])

	# Logic to tell if there's a problem
	if particles_rejected != 0:
		#print(inLine)
		return False
	elif particles_accepted % 3 != 0:
		#print(inLine)
		return False
	else:
		return True


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


def last_colon(inStr):
	""" Returns index of last colon in a str """
	prevPos = 0
	currentPos = 0
	while currentPos != -1:
		prevPos = currentPos
		currentPos = inStr.find(":", prevPos+1)
	return prevPos


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
	if len(sys.argv) == 4:
		main(sys.argv[1], sys.argv[2], sys.argv[3])
	else:
		print("Check usage: python foo.py inPdf inCs csJobID")
		exit()