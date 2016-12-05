#!/usr/bin/env python
'''USAGE: python python interact_bipartite.py --seedfiles1 organism_1.files --seedfiles2 organism_2.files --name1 organism_1 --name2 organism_2 --stdev 0

'''

# Initialize all modules, functions, and compound dictionary
import sys
import math
import os
import pickle
import argparse


#---------------------------------------------------------------------------------------#


# Find the directory where interaction.py is being run from
script_path = str(os.path.dirname(os.path.realpath(__file__)))

# Create a string with the name of the initial directory you start running the script from
starting_directory = str(os.getcwd())

#---------------------------------------------------------------------------------------#

# Define some functions

# Function to get the organism name from the bigSMALL parameters file
def read_parameters(parameters):

	for line in parameters:

		line = line.split()

		if line[0] == 'KO expression file:':
			file_name = str(line[1])

		elif line[0] == 'Graph name:':
			graph_name = str(line[1])

	if graph_name != 'organism':
		name = graph_name
	else:
		name = file_name

	return name


# Reads importance files, converts to catagories, and generates a dictionary
def convert_scores(importance_scores, p_cutoff):

	score_list = []
	entry_list = []

	for line in compound_scores:
		
		line = line.split()
		if line[0] == 'Compound_code': continue
		
		score_list.append(float(line[2]))

		p_value = line[3]
		if line[3] == '<0.01':
			p_value = 0.01
		elif line[3] == '<0.05':
			p_value = 0.05
		else:
			p_value = 1

		entry_list.append([line[0],line[1],line[2],p_value])
		
	min_level = min(score_list) / 3
	output_hi = [min(score_list), (min(score_list) - min_level - 0.001)]
	output_med = [(min(score_list) - min_level), (min(score_list) - ( 2 * min_level) - 0.001)]
	output_lo = [(min(score_list) - ( 2 * min_level)),  -0.001]

	max_level = max(score_list) / 3
	input_hi = [max(score_list), (max(score_list) - min_level + 0.001)]
	input_med = [(max(score_list) - max_level), (max(score_list) - ( 2 * max_level) + 0.001)]
	input_lo = [(max(score_list) - ( 2 * max_level)),  0.001]

	score_dictionary = {}
	for index in entry_list:

		if index[3] > p_cutoff: continue

		if index[2] > 0.0:

			if input_hi[1] <= index[2] >= input_hi[0]:
				score_dictionary[index[0]] = [index[1], 3.0]
			elif input_hi[1] <= index[2] >= input_hi[0]:
				score_dictionary[index[0]] = [index[1], 2.0]
			elif input_hi[1] <= index[2] >= input_hi[0]:
				score_dictionary[index[0]] = [index[1], 1.0]

		elif index[2] < 0.0:

			if output_hi[1] >= index[2] <= output_hi[0]:
				score_dictionary[index[0]] = [index[1], -3.0]
			elif output_hi[1] >= index[2] <= output_hi[0]:
				score_dictionary[index[0]] = [index[1], -2.0]
			elif output_hi[1] >= index[2] <= output_hi[0]:
				score_dictionary[index[0]] = [index[1], -1.0]

		else:
			score_dictionary[index[0]] = [index[1], 0.0]


	return score_dictionary


# Function for calculating likely metabolic interaction
def interaction(score_dict1, score_dict2):
	
	all_compounds = list(set(score_dict1.keys() + score_dict2.keys()))
	
	interaction_list = []

	for index in all_compounds:
		
		name1 = 'place_holder'
		name2 = 'place_holder'

		try:
			name1 = score_dict1[index][0]
			score1 = float(score_dict1[index][1])
		except keyError:
			score1 = 0.0
			
		try:
			name2 = score_dict2[index][0]
			score2 = float(score_dict2[index][1])
		except keyError:
			score2 = 0.0

		if name1 == 'place_holder':
			name = name2
		else:
			name = name1

		interaction_score = str(score1 + score2)
	
		entry = [index, name, interaction_score]
		interaction_list.append(entry)

	return interaction_list


# Function to write data to output file
def write_output(header, out_data, p_cutoff, file_name):

	with open(file_name, 'w') as outfile: 
		
		p_value = str(p_cutoff) + '\n'
		outfile.write(header)
			
		for index in out_data:
			index = index.append(p_value)
			outfile.write('\t'.join(index))	
	
#---------------------------------------------------------------------------------------#

# Set up arguments
parser = argparse.ArgumentParser(description='Calculate metabolic interaction of two species from the output of bigSMALL.')
parser.add_argument('--species_1', default='none', help='Directory of SCC network output for first (meta)organism')
parser.add_argument('--species_2', default='none', help='Directory of SCC network output for second (meta)organism')
parser.add_argument('--p_value', default='n.s.', help='Minimum confidence values for seeds and sinks to be considered in calculations')

args = parser.parse_args()
species_1 = args.species_1
species_2 = args.species_2
p_value = float(args.p_value)

if species_1 ==  'none' or species_2 ==  'none': sys.exit('WARNING: Missing input file(s), quitting')
if os.path.exists(species_1) == False or os.path.exists(species_2) == False: sys.exit('WARNING: Missing input file(s), quitting')
if p_value != 'n.s.' and p_value < 0.0: sys.exit('WARNING: p-value cutoff is less than 0, quitting')

#---------------------------------------------------------------------------------------#

# Retrieve and read in the necessary files
print('\nReading in importance files.\n')
os.chdir(species_1)
name_1 = read_parameters(open('parameters.txt','r'))
scores_1 = convert_scores(open('importances.tsv','r'), p_value)
os.chdir(starting_directory)
os.chdir(species_2)
name_2 = read_parameters(open('parameters.txt','r'))
scores_2 = convert_scores(open('importances.tsv','r'), p_value)
os.chdir(starting_directory)

# Calculate putative metabolic interactions and parse the output
print('Calculating putative interaction of ' + name_1 + ' and ' + name_2 + '.\n')
crosstalk = interaction(scores_1, scores_2)

#---------------------------------------------------------------------------------------#

# Write output tables and summary to files
head = 'Compound_code\tCompound_name\tInteraction_score\tp_value\n'
file = name_1 + 'AND' + name_2 + '.interaction.tsv'
write_output(head, crosstalk, p_value, file)

print('Done.\n')