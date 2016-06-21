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
# This is repeated respective to incoming, outgoing, and combined edges.  A Negative Binomial
# distribution of simulated transcript abundance is then created and repeatedly subsampled from  
# to generate confidence interval for to compare the measured values against.

# Dependencies:  
# The script itself needs to be run from from a directory containing the /support/ sub-directory
# The only argument is a 2 column matrix text file containing a column of KO codes with corresponding expression
# Example:
# K00045		0
# K03454		4492
# K10021		183
# ...

# Generate files:  A new directory in ./ ending in ".bipartite.files" that contains all output including:
	# A 2 column directed, bipartite network file of compounds and enzymes
	# A text file containing reference errors thrown during the translation of KOs to chemical equations
	# A text file containing user defined parameters
	# List of unique compound nodes
	# List of unique enzymes nodes
	# 4 files with information derived from the network:
	#	1.  Input metabolite score (including confidence interval when applicable)
	#	2.  Output metabolite score (including confidence interval when applicable)
	#	3.  Description of network topology for each node (indegree and outdegree)

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

# Define arguments
parser = argparse.ArgumentParser(description='Generate bipartite metabolic models and calculates importance of substrate nodes based on gene expression.')
parser.add_argument('input_file')
parser.add_argument('--name', default='organism', help='Organism or other name for KO+expression file (default is organism)')
parser.add_argument('--min', default=0, help='minimum substrate importance value')
parser.add_argument('--indegree', default=0, help='minimum output connections for a substrate')
parser.add_argument('--outdegree', default=0, help='minimum input connections for a substrate')
parser.add_argument('--iters', default=1, help='iterations for random distribution subsampling')
args = parser.parse_args()

# Assign variables
KO_input_file = str(args.input_file)
file_name = str(args.name)
min_score = int(args.min)
min_indegree = int(args.indegree)
min_outdegree = int(args.outdegree)
iterations = int(args.iters)

#---------------------------------------------------------------------------------------#			

# Check if the user fucked it up
if KO_input_file == 'input_file':
	print 'No KO+expression file provided. Aborting.'
	sys.exit()
elif os.stat(KO_input_file).st_size == 0:
	print('Empty input file provided. Aborting.')
	sys.exit()
elif min_score < 0:
	print 'Invalid importance minimum. Aborting.'
	sys.exit()
elif min_indegree < 0:
	print 'Invalid degree minimum. Aborting.'
	sys.exit()
elif min_outdegree < 0:
	print 'Invalid degree minimum. Aborting.'
	sys.exit()
elif iterations < 1:
	print 'Invalid iteration value. Aborting.'
	sys.exit()
	
#---------------------------------------------------------------------------------------#			

# Define the functions. Protect the land.

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


# Create a dictionary for transcript value associated with its KO
def transcription_dictionary(KO_file):
	
	seq_total = 0  # Total number of reads
	seq_max = 0  # Highest single number of reads
	transcript_dict = {}  # Dictionary for transcription
	transcript_distribution_lst = []
	
	for line in KO_file:
		entry = line.split()
		
		ko = str(entry[0])
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
	
		for line in KOs:
	
			current_ko = line.strip('ko:')
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
def calculate_score(compound_transcript_dict, compound_degree_dict, compound_name_dict, min_score, min_indegree, min_outdegree, compound_lst):
	
	input_score_dict = {}
	output_score_dict = {}
	degree_dict = {}
		
	# Calculate cumulative scores for all compounds as inputs or outputs
	for compound in compound_lst:
	
		input_score_dict[compound] = []
		output_score_dict[compound] = []
		degree_dict[compound] = []
		
		compound_name = compound_name_dict[compound]
		indegree = compound_degree_dict[compound][0]
		outdegree = compound_degree_dict[compound][1]
		input_transcription = compound_transcript_dict[compound][0]
		output_transcription = compound_transcript_dict[compound][1]	
		
		if outdegree == 0.0:
			input_score = 0.0
			input_score = 0.0
		else:
			input_score = math.sqrt(input_transcription) / outdegree
		if indegree == 0.0:
			output_score = 0.0
		else:
			output_score = math.sqrt(output_transcription) / indegree
		
		input_score = float("%.3f" % input_score)
		output_score = float("%.3f" % output_score)
		
		if input_score >= min_score:
			input_score_dict[compound].extend((compound_name, input_score, indegree, outdegree))
		if output_score >= min_score:
			output_score_dict[compound].extend((compound_name, output_score, indegree, outdegree))
		
		if indegree >= min_indegree and outdegree >= min_outdegree:
			degree_dict[compound].extend((compound_name, indegree, outdegree))	
					
	return input_score_dict, output_score_dict, degree_dict

	
# Perform iterative Monte Carlo simulation to create confidence interval for compound importance values
def monte_carlo_sim(ko_input_dict, ko_output_dict, degree_dict, kos, iterations, compound_name_dict, min_score, min_indegree, min_outdegree, seq_total, seq_max, compound_lst, transcript_distribution_lst):
	
	gene_count = len(kos)
	probability = 1.0 / gene_count
	
	# Generates a random negative binomial distribution to sample from, way too high for my expression values
	#distribution = list(numpy.random.negative_binomial(1, probability, seq_total))  # Negative Binomial distribution
	#distribution = [i for i in distribution if i < seq_max]  # screen for transcript mapping greater than largest value actually sequenced
	
	input_distribution_dict = {}
	output_distribution_dict = {}
	for compound in compound_lst:
		input_distribution_dict[compound] = []
		output_distribution_dict[compound] = []
	
	increment = 100.0 / float(iterations + len(compound_lst))
	progress = 0.0
	sys.stdout.write('\rProgress: ' + str(progress) + '%')
	sys.stdout.flush()
	
	for current in range(0, iterations):
			
		#sim_transcriptome = random.sample(distribution, gene_count)
		sim_transcriptome = random.sample(transcript_distribution_lst, gene_count)
		
		sim_transcript_dict = {}
		for index in range(0, gene_count):
			sim_transcript_dict[kos[index]] = sim_transcriptome[index]
		
		substrate_dict, degree_dict = compile_scores(sim_transcript_dict, ko_input_dict, ko_output_dict, compound_lst, kos)
		input_score_dict, output_score_dict, degree_dict = calculate_score(substrate_dict, degree_dict, compound_name_dict, min_score, min_indegree, min_outdegree, compound_lst)
		
		# Make dictionaries of scores for each compound for each direction
		for compound in compound_lst:
			input_distribution_dict[compound].append(input_score_dict[compound][1])
			output_distribution_dict[compound].append(output_score_dict[compound][1])
		
		progress += increment
		progress = float("%.3f" % progress)
		sys.stdout.write('\rProgress: ' + str(progress) + '%')
		sys.stdout.flush()
			
	# Compile the scores for each compound and take the mean and standard deviation
	interval_lst = []
	for compound in compound_lst:

		input_current_mean = float("%.3f" % (numpy.mean(input_distribution_dict[compound])))
		input_current_std = float("%.3f" % (numpy.std(input_distribution_dict[compound])))
		output_current_mean = float("%.3f" % (numpy.mean(output_distribution_dict[compound])))
		output_current_std = float("%.3f" % (numpy.std(output_distribution_dict[compound])))

		interval_lst.append([compound, input_current_mean, input_current_std, output_current_mean, output_current_std])

		progress += increment
		progress = float("%.3f" % progress)
		sys.stdout.write('\rProgress: ' + str(progress) + '%')
		sys.stdout.flush()
	
	sys.stdout.write('\rProgress: 100%               ')
	sys.stdout.flush()
	print('\n')
	
	return interval_lst


# Assesses measured values against confidence interval from Monte Carlo simulation 
def confidence_interval(input_score_dict, output_score_dict, interval_lst, degree_dict):

	labeled_confidence = []

	for index in interval_lst:
		
		current_compound = index[0]
		current_name = input_score_dict[current_compound][0]
		current_indegree = degree_dict[current_compound][1]
		current_outdegree = degree_dict[current_compound][2]
		
		input_std_dev = index[1]
		input_mean = index[2]
		input_score = input_score_dict[current_compound][1]
		final_input_score = str(float(input_score) - float(input_mean))
		
		if input_score > input_mean:
		
			if input_score > (input_mean + input_std_dev):
			
				if input_score > (input_mean + (input_std_dev * 2)):
				
					if input_score > (input_mean + (input_std_dev * 3)):
						input_relation = '***'	
					else:
						input_relation = '**'
				else:
					input_relation = '*'
			else:
				input_relation = 'n.s.'
		
		elif input_score < input_mean:
		
			if input_score < (input_mean - input_std_dev):
			
				if input_score < (input_mean - (input_std_dev * 2)):
				
					if input_score < (input_mean - (input_std_dev * 3)):
						input_relation = '***'	
					else:
						input_relation = '**'
				else:
					input_relation = '*'
			else:
				input_relation = 'n.s.'
	
		else:
			input_relation = 'n.s.'

		output_std_dev = index[3]
		output_mean = index[4]
		output_score = output_score_dict[current_compound][1]
		final_output_score = str(float(output_score) - float(output_mean))
		
		if output_score > output_mean:
		
			if output_score > (output_mean + output_std_dev):
			
				if output_score > (output_mean + (output_std_dev * 2)):
				
					if output_score > (output_mean + (output_std_dev * 3)):
						output_relation = '***'	
					else:
						output_relation = '**'
				else:
					output_relation = '*'
			else:
				output_relation = 'n.s.'
		
		elif output_score < output_mean:
		
			if output_score < (output_mean - output_std_dev):
			
				if output_score < (output_mean - (output_std_dev * 2)):
				
					if output_score < (output_mean - (output_std_dev * 3)):
						output_relation = '***'	
					else:
						output_relation = '**'
				else:
					output_relation = '*'
			else:
				output_relation = 'n.s.'
		else:
			output_relation = 'n.s.'

		labeled_confidence.append([current_compound, current_name, final_input_score, current_outdegree, input_relation, final_output_score, current_indegree, output_relation])	

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
	transcript_dict, total, max, transcript_distribution_lst = transcription_dictionary(KO_file)
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
Minimum compound importance: {imp}
Minimum input edges per node: {outdeg}
Minimum output edges per node: {indeg}
KEGG ortholog nodes: {kos}
Substrate nodes: {substrate}
Monte Carlo simulation iterations: {iter}
'''.format(ko=str(KO_input_file), name=str(file_name), imp=str(min_score), outdeg=str(min_outdegree), indeg=str(min_indegree), iter=iter_str, kos=str(len(KO_lst)), substrate=str(len(compound_lst)))
	parameter_file.write(outputString)
#---------------------------------------------------------------------------------------#	

# Calculate actual importance scores for each compound in the network
print 'Calculating compound node connectedness and metabolite scores...\n'
compound_transcript_dict, compound_degree_dict = compile_scores(transcript_dict, ko_input_dict, ko_output_dict, compound_lst, KO_lst)
input_score_dict, output_score_dict, degree_dict = calculate_score(compound_transcript_dict, compound_degree_dict, compound_name_dictionary, min_score, min_indegree, min_outdegree, compound_lst)
print 'Done.\n'

#---------------------------------------------------------------------------------------#		

# Calculate simulated importance values if specified
if iterations > 1:

	print 'Comparing to simulated transcript distribution...\n'	
	interval_lst = monte_carlo_sim(ko_input_dict, ko_output_dict, degree_dict, KO_lst, iterations, compound_name_dictionary, min_score, min_indegree, min_outdegree, total, max, compound_lst, transcript_distribution_lst)
	final_data = confidence_interval(input_score_dict, output_score_dict, interval_lst, degree_dict)
	print 'Done.\n'
	
	# Write all the calculated data to files
	print 'Writing score data with Monte Carlo simulation to files...\n'
	outname = file_name + '.monte_carlo.score.txt'
	write_list('Compound_code	Compound_name	Input_metabolite_score	Outdegree	Input_Significance	Output_metabolite_score	Indegree	Output_Significance\n', final_data, outname)
	

# If Monte Carlo simulation not performed, write only scores calculated from measured expression to files	
else:
	print 'Writing score data to files...\n' 
	outname = file_name + '.input_score.txt'
	write_dictionary('Compound_code	Compound_name	Input_metabolite_score	Outdegree\n', input_score_dict, outname)

	outname = file_name + '.output_score.txt'
	write_dictionary('Compound_code	Compound_name	Output_metabolite_score	Indegrees\n', output_score_dict, outname)
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

# Enjoy the data!