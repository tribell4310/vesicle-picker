"""

merge_cs.py


"""


import numpy as np
import sys
import shutil
import os


def main(inList):
	f = np.load(inList[0])
	g = np.load(inList[1])
	outList = np.concatenate((f, g))
	if len(inList) > 2:
		for i in range(2, len(inList)):
			f = np.load(inList[i])
			outList = np.concatenate((outList, f))

	np.save("_temp.npy", outList)
	shutil.copy2("_temp.npy", "merged_cs_out.cs")
	os.remove("_temp.npy")
	print(len(outList))


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
	if len(sys.argv) >= 2:
		main(sys.argv[1:])
	else:
		print("Check usage: python foo.py inCsFiles")
		exit()
