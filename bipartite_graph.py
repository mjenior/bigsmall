#!/usr/bin/env python
'''USAGE: bipartite_graph.py KO_expressionfile --name organism_name --min 0 --degree 0 --iters 1
The function of this script is to convert lists of genes to unweighted, 
directed graphs and compute importance of each compound to metabolism 
based on the expression of surrounding enzyme nodes.
'''

# Written by Matthew Jenior, University of Michigan, Schloss Laboratory, 2016

# Our equation for metabolite score is a variation of Eigenvector centrality and incorporates both 
# expression of local enzymes and degree of connectedness of each compound node in the calculation.  
# Relative importance of each surrounding compound node is then calculated by dividing the sum of 
# surrounding transcripts (the eigenvalue) by the number of edges connected to the node of interest.  
# This is repeated respective to incoming and outgoing edges.  Output scores are then subtracted 
# from input values then log2 transformed.  A simulated distribution of transcript abundance is 
# then created and repeatedly subsampled to generate confidence interval to compare the calculated 
# importances against and highlight compounds scoring outside a random interval.

# Dependencies:  
# The script itself needs to be run from from a directory containing the /support/ sub-directory
# The only argument is a 2 column matrix text file containing a column of KO codes with corresponding expression
# Example:
# K00045		0
# K03454		4492
# K10021		183
# ...
# Knnnnn 		n

# Generate files:  A new directory in ./ ending in ".bipartite.files" that contains all output including:
	# A 2 column directed, bipartite network file of compounds and enzymes
	# A text file containing reference errors thrown during the translation of KOs to chemical equations
	# A text file containing user defined parameters
	# List of unique compound nodes
	# List of unique enzymes nodes
	# A table containing importance values, node topology, and relationship to simulated means

#---------------------------------------------------------------------------------------#		

# Import python modules
import sys
import os
import pickle
import math
import argparse
import random
import numpy
import time

#---------------------------------------------------------------------------------------#		

# Start timer
start = time.time()

#---------------------------------------------------------------------------------------#		

# User defined arguments
parser = argparse.ArgumentParser(description='Generate bipartite metabolic models and calculates importance of substrate nodes based on gene expression.')
parser.add_argument('input_file')
parser.add_argument('--name', default='organism', help='Organism or other name for KO+expression file (default is organism)')
parser.add_argument('--iters', default=1, help='iterations for random distribution subsampling')
args = parser.parse_args()

# Assign variables
KO_input_file = str(args.input_file)
file_name = str(args.name)
iterations = int(args.iters)

#---------------------------------------------------------------------------------------#			

# Check if the user fucked it up
if KO_input_file == 'input_file':
	print 'No KO+expression file provided. Aborting.'
	sys.exit()
elif os.stat(KO_input_file).st_size == 0:
	print('Empty input file provided. Aborting.')
	sys.exit()
elif iterations < 1:
	print 'Invalid iteration value. Aborting.'
	sys.exit()
elif file_name == '':
	print 'You used the --name argument and then provided nothing. Not aborting.'
	file_name = 'you_forgot_to_name_your_flipping_files'
	
#---------------------------------------------------------------------------------------#			

# Define all the functions!

# Function to write lists to files	
def write_list(header, out_lst, file_name):

	with open(file_name, 'w') as out_file: 
		
		if not header == 'none': out_file.write(header)
			
		for index in out_lst:
			index = [str(x) for x in index]
			index[-1] = str(index[-1]) + '\n'
			out_file.write('\t'.join(index))

def write_list_short(header, out_lst, file_name):

	with open(file_name, 'w') as out_file: 
		
		if not header == 'none': out_file.write(header)
			
		for index in out_lst:
			index = [str(x) for x in index]
			index[-1] = str(index[-1]) + '\n'
			out_file.write(''.join(index))
			

# Function to write dictionaries to files	
def write_dictionary(header, out_dict, file_name):

	all_keys = out_dict.keys()
	
	with open(file_name, 'w') as out_file: 
		
		if not header == 'none': out_file.write(header)
			
		for index in all_keys:
			elements = out_dict[index]
			elements.insert(0, index)
			elements = [str(x) for x in elements]
			elements[-1] = elements[-1] + '\n'
			out_file.write('\t'.join(elements))

def write_dictionary_short(header, out_dict, file_name):

	all_keys = out_dict.keys()
	
	with open(file_name, 'w') as out_file: 
		
		if not header == 'none': out_file.write(header)
			
		for index in all_keys:
<<<<<<< HEAD
			entry = index + '\t' + str(out_dict[index]) + '\n'
			out_file.write(entry)
=======
			element = str(out_dict[index]) + '\n'
			entry = [index, element]
			out_file.write('\t'.join(entry))
>>>>>>> master


# Create a dictionary for transcript value associated with its KO
def transcription_dictionary(KO_file):
	
	seq_total = 0  # Total number of reads
	seq_max = 0  # Highest single number of reads
	transcript_dict = {}  # Dictionary for transcription
	transcript_distribution_lst = []
	
	for line in KO_file:
		entry = line.split()
		
		ko = str(entry[0]).strip('ko:')
		expression = float(entry[1])
		
		seq_total += expression
		
		if not ko in transcript_dict.keys():
			transcript_dict[ko] = expression
			transcript_distribution_lst.append(expression)
		else:
			transcript_dict[ko] = transcript_dict[ko] + expression
			transcript_distribution_lst.append(transcript_dict[ko])
		
		if transcript_dict[ko] > seq_max: seq_max = transcript_dict[ko]
	
	return transcript_dict, seq_total, seq_max, transcript_distribution_lst


# Translates a list of KOs to the bipartite graph
def network_dictionaries(KOs, ko_dict, reaction_dict):

	# Set some starting points
	triedCountKO = 0
	excludedCountKO = 0
	triedCountReact = 0
	excludedCountReact = 0
	totalIncludedReact = 0
	
	network_list = []
	compound_lst = []
	
	ko_input_dict = {}
	ko_output_dict = {}

	# Nested loops to convert the KO list to a directed graph of input and output compounds
	# Outside loop finds the biochemical reactions corresponding the the given KO	
	print('Translating KEGG orthologs to bipartite enzyme-to-compound graph...\n')
	
	
	with open('key_error.log', 'w') as errorfile:
	
		for current_ko in KOs:
	
			triedCountKO += 1
			
			if not current_ko in ko_input_dict:
				ko_input_dict[current_ko] = []
				ko_output_dict[current_ko] = []
			
			try:
				reaction_number = ko_dict[current_ko]
			except KeyError:
				errorString = 'WARNING: ' + str(current_ko) + ' not found in KO-to-Reaction dictionary. Omitting.\n'
				errorfile.write(errorString)
				excludedCountKO += 1
				continue 
	
			# Inner loop translates the reaction codes to collections of input and output compounds
			for index in reaction_number:
				triedCountReact += 1
				try:
					reaction_collection = reaction_dict[index]
				except KeyError:
					errorString = 'WARNING: ' + str(index) + ' not found in Reaction-to-Compound dictionary. Omitting.\n'
					errorfile.write(errorString)
					excludedCountReact += 1
					continue
		
				# The innermost loop creates two columns of input and output compounds, incorporating reversibility information
				for x in reaction_collection:
				
					totalIncludedReact += 1
					
					# Split reaction input and output as well as the list of compounds with each
					reaction_info = x.split(':')
					input_compounds = reaction_info[0].split('|')
					output_compounds = reaction_info[2].split('|')
					rev = reaction_info[1].split('|')
						
					for input_index in input_compounds:
						network_list.append([str(input_index), str(current_ko)])
						ko_input_dict[current_ko].append(str(input_index))
						
						if rev == 'R':
							network_list.append([str(current_ko), str(input_index)])
							ko_output_dict[current_ko].append(str(input_index))	
							
						compound_lst.append(str(input_index))		
			
					for output_index in output_compounds:
						network_list.append([str(current_ko), str(output_index)])
						ko_output_dict[current_ko].append(str(output_index))
						
						if rev == 'R':
							network_list.append([str(output_index), str(current_ko)])
							ko_input_dict[current_ko].append(str(output_index))
							
						compound_lst.append(str(output_index))
								
		error_string = '''KOs successfully translated to Reactions: {KO_success}
KOs unsuccessfully translated to Reactions: {KO_failed}

Reactions successfully translated to Compounds: {Reaction_success}
Reactions unsuccessfully translated to Compounds: {Reaction_failed}
'''.format(KO_success = str(triedCountKO - excludedCountKO), KO_failed = str(excludedCountKO), Reaction_success = str(triedCountReact - excludedCountReact), Reaction_failed = str(excludedCountReact))
		errorfile.write(error_string)
	
	network_list = [list(x) for x in set(tuple(x) for x in network_list)]  # List of unique edges (KOs and compounds)
	compound_lst = list(set(compound_lst))
	
	print('Done.\n')
	
	return network_list, ko_input_dict, ko_output_dict, compound_lst


# Compile surrounding input and output node transcripts into a dictionary, same for degree information
def compile_scores(transcript_dictionary, ko_input_dict, ko_output_dict, compound_lst, KO_lst):

	compound_transcript_dict = {}
	compound_degree_dict = {}
	for compound in compound_lst:
		compound_transcript_dict[compound] = [0, 0] # [input, output]
		compound_degree_dict[compound] = [0, 0] # [indegree, outdegree]
		
	for ko in KO_lst:
	
		transcription = transcript_dictionary[ko]
		
		input_compounds = ko_input_dict[ko]
		output_compounds = ko_output_dict[ko]
		
		for compound in input_compounds:
			compound_transcript_dict[compound][0] = compound_transcript_dict[compound][0] + transcription
			compound_degree_dict[compound][1] = compound_degree_dict[compound][1] + 1
		
		for compound in output_compounds:
			compound_transcript_dict[compound][1] = compound_transcript_dict[compound][1] + transcription
			compound_degree_dict[compound][0] = compound_degree_dict[compound][0] + 1
	
	return compound_transcript_dict, compound_degree_dict


# Calculate input and output scores and well as degree of each compound node
def calculate_score(compound_transcript_dict, compound_degree_dict, compound_name_dict, compound_lst):
	
	score_dict = {}
	degree_dict = {}
		
	# Calculate metabolite scores integrating input and output reactions weightings
	for compound in compound_lst:
	
		score_dict[compound] = []
		degree_dict[compound] = []
		
		compound_name = compound_name_dict[compound]
		indegree = compound_degree_dict[compound][0]
		outdegree = compound_degree_dict[compound][1]
		input_transcription = compound_transcript_dict[compound][0]
		output_transcription = compound_transcript_dict[compound][1]	
		
		if outdegree == 0.0:
			input_score = 0.0
		else:
			input_score = input_transcription / outdegree

		if indegree == 0.0:
			output_score = 0.0
		else:
			output_score = output_transcription / indegree
		
		score_difference = input_score - output_score

		if score_difference < 1 and score_difference > -1:
			final_score = 0.0
		elif score_difference <= -1:
			final_score = math.log(abs(score_difference), 2) * -1
		else:
			final_score = math.log(score_difference, 2)

		final_score = float("%.3f" % final_score)

		score_dict[compound].extend((compound_name, final_score))
		degree_dict[compound].extend((compound_name, indegree, outdegree))	
					
	return score_dict, degree_dict

	
# Perform iterative Monte Carlo simulation to create confidence interval for compound importance values
def monte_carlo_sim(ko_input_dict, ko_output_dict, degree_dict, kos, iterations, compound_name_dict, seq_total, seq_max, compound_lst, transcript_distribution_lst):
	
	gene_count = len(kos)
	
	# Generates a random negative binomial distribution to sample from, way too high for my expression values
	#probability = 1.0 / gene_count
	#transcript_distribution_lst = list(numpy.random.negative_binomial(1, probability, seq_total))  # Negative Binomial distribution
	#transcript_distribution_lst = [i for i in distribution if i < seq_max]  # screen for transcript mapping greater than largest value actually sequenced
	
	distribution_dict = {}
	for compound in compound_lst:
		distribution_dict[compound] = []
	
	increment = 100.0 / float(iterations + len(compound_lst))
	progress = 0.0
	sys.stdout.write('\rProgress: ' + str(progress) + '%')
	sys.stdout.flush()
	
	for current in range(0, iterations):
			
		sim_transcriptome = random.sample(transcript_distribution_lst, gene_count)
		
		sim_transcript_dict = {}
		for index in range(0, gene_count):
			sim_transcript_dict[kos[index]] = sim_transcriptome[index]
		
		substrate_dict, degree_dict = compile_scores(sim_transcript_dict, ko_input_dict, ko_output_dict, compound_lst, kos)
		score_dict, degree_dict = calculate_score(substrate_dict, degree_dict, compound_name_dict, compound_lst)
		
		# Make dictionaries of scores for each compound for each direction
		for compound in compound_lst:
			distribution_dict[compound].append(score_dict[compound][1])
		
		progress += increment
		progress = float("%.3f" % progress)
		sys.stdout.write('\rProgress: ' + str(progress) + '%')
		sys.stdout.flush()
			
	# Compile the scores for each compound and take the mean and standard deviation
	interval_lst = []
	for compound in compound_lst:

		current_mean = float("%.3f" % (numpy.mean(distribution_dict[compound])))
		current_std = float("%.3f" % (numpy.std(distribution_dict[compound])))

		interval_lst.append([compound, current_mean, current_std])

		progress += increment
		progress = float("%.3f" % progress)
		sys.stdout.write('\rProgress: ' + str(progress) + '%')
		sys.stdout.flush()
	
	sys.stdout.write('\rProgress: 100%               ')
	sys.stdout.flush()
	print('\n')
	
	return interval_lst


# Assesses measured values against confidence interval from Monte Carlo simulation 
def confidence_interval(score_dict, interval_lst, degree_dict):

	labeled_confidence = []

	for index in interval_lst:
		
		current_compound = index[0]
		current_name = score_dict[current_compound][0]
		current_indegree = degree_dict[current_compound][1]
		current_outdegree = degree_dict[current_compound][2]
		
		current_mean = index[1]
		current_std_dev = index[2]
		current_score = score_dict[current_compound][1]
		
		if current_score > current_mean:
		
			if current_score > (current_mean + current_std_dev):
			
				if current_score > (current_mean + (current_std_dev * 2)):
				
					if current_score > (current_mean + (current_std_dev * 3)):
						current_relation = 3	
					else:
						current_relation = 2
				else:
					current_relation = 1
			else:
				current_relation = 0
		
		elif current_score < current_mean:
		
			if current_score < (current_mean - current_std_dev):
			
				if current_score < (current_mean - (current_std_dev * 2)):
				
					if current_score < (current_mean - (current_std_dev * 3)):
						current_relation = 3	
					else:
						current_relation = 2
				else:
					current_relation = 1
			else:
				current_relation = 0
	
		else:
			current_relation = 0

		labeled_confidence.append([current_compound, current_name, current_score, current_mean, current_std_dev])	

	return labeled_confidence


##########################################################################################		
#																						 #
# 										 DO WORK										 #
#																						 #
##########################################################################################		


# Print organism name to screen to track progress in case of loop
if file_name != 'organism':
	print '\nImputing metabolism for ' + file_name + '\n'

# Read in and create dictionary for expression
with open(KO_input_file, 'r') as KO_file:
	transcript_dict, total, seq_max, transcript_distribution_lst = transcription_dictionary(KO_file)
KO_lst = transcript_dict.keys()

#---------------------------------------------------------------------------------------#		

# Determine starting directory
starting_directory = str(os.getcwd())
script_path = str(os.path.dirname(os.path.realpath(__file__)))

# Create and navigate to new output directory
directory = str(os.getcwd()) + '/' + file_name + '.bipartite.files'
if not os.path.exists(directory):	
	os.makedirs(directory)
os.chdir(directory)

#---------------------------------------------------------------------------------------#		

# Create a dictionary of KO expression scores and load KEGG dictionaries
print('\nReading in KEGG dictionaries...\n')

# Read in pickled KO to reaction dictionary
ko_reactionpkl_path = script_path + '/support/ko_reaction.pkl'
ko_dictionary = pickle.load(open(ko_reactionpkl_path, 'rb'))

# Read in pickled reaction to reaction_mapformula dictionary
#reaction_mapformulapkl_path = script_path + '/support/reaction_mapformula.pkl'
reaction_mapformulapkl_path = script_path + '/support/reaction_mapformula_nonrev.pkl'
reaction_dictionary = pickle.load(open(reaction_mapformulapkl_path, 'rb'))

# Read in pickled compound name dictionary
compoundpkl_path = script_path + '/support/compound.pkl'
compound_name_dictionary = pickle.load(open(compoundpkl_path, 'rb'))
print('Done.\n')

#---------------------------------------------------------------------------------------#	

# Call translate function and separate output lists
reaction_graph, ko_input_dict, ko_output_dict, compound_lst = network_dictionaries(KO_lst, ko_dictionary, reaction_dictionary)

#---------------------------------------------------------------------------------------#	

# Write compounds and enzymes to files
write_list_short('none', compound_lst, 'compound.lst')
write_list_short('none', KO_lst, 'enzyme.lst')

# Write network to a two column matrix for use in Neo4j or R
write_list('none', reaction_graph, 'bipartite_graph.txt')

#---------------------------------------------------------------------------------------#		

# Define calculation selection with a string
if iterations == 1:
	iter_str = 'none'
else:
	iter_str = str(iterations)

# Write parameters to a file
with open('parameters.txt', 'w') as parameter_file:
	outputString = '''User Defined Parameters
KO expression file: {ko}
Graph name: {name}
KEGG ortholog nodes: {kos}
Substrate nodes: {substrate}
Monte Carlo simulation iterations: {iter}
'''.format(ko=str(KO_input_file), name=str(file_name), iter=iter_str, kos=str(len(KO_lst)), substrate=str(len(compound_lst)))
	parameter_file.write(outputString)

#---------------------------------------------------------------------------------------#	

# Calculate actual importance scores for each compound in the network
print 'Calculating compound node connectedness and metabolite scores...\n'
compound_transcript_dict, compound_degree_dict = compile_scores(transcript_dict, ko_input_dict, ko_output_dict, compound_lst, KO_lst)
score_dict, degree_dict = calculate_score(compound_transcript_dict, compound_degree_dict, compound_name_dictionary, compound_lst)
print 'Done.\n'

#---------------------------------------------------------------------------------------#		

# Calculate simulated importance values if specified
if iterations > 1:
	print 'Comparing to simulated transcript distribution...\n'	
	interval_lst = monte_carlo_sim(ko_input_dict, ko_output_dict, degree_dict, KO_lst, iterations, compound_name_dictionary, total, seq_max, compound_lst, transcript_distribution_lst)
	final_data = confidence_interval(score_dict, interval_lst, degree_dict)
	print 'Done.\n'
	
	# Write all the calculated data to files
	print 'Writing score data with Monte Carlo simulation to a file...\n'
	outname = file_name + '.monte_carlo.score.txt'
	write_list('Compound_code\tCompound_name\tMetabolite_score\tSim_Mean\tSim_StD\n', final_data, outname)


# If Monte Carlo simulation not performed, write only scores calculated from measured expression to files	
else:
	print 'Writing score data to a file...\n' 
	outname = file_name + '.score.txt'
	write_dictionary_short('Compound_code\tCompound_name\tMetabolite_score\n', score_dict, outname)
	print 'Done.\n'

print 'Writing network topology and original transcipt counts to files...\n'
outname = file_name + '.topology.txt'
write_dictionary('Compound_code\tCompound_name\tIndegree\tOutdegree\n', degree_dict, outname)
<<<<<<< HEAD
outname = file_name + '.original_mapping.txt'
=======
outname = file_name + '.mapping.txt'
>>>>>>> master
write_dictionary_short('KO_code\tTranscripts\n', transcript_dict, outname)
print 'Done.\n'

#---------------------------------------------------------------------------------------#		

# Wrap everything up

# Return to the directory the script was called to
os.chdir(starting_directory)	

# Report time if iterations are performed
end = time.time()
if iterations > 10:
	duration = str(int(end - start))
	print '\nCompleted in ' + duration + ' seconds.\n'
else :
	print '\n'
	
print 'Output files located in: ' + directory + '\n\n'

# Enjoy the data, ya filthy animal!


