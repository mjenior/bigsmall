BiGSMAll or BacterIal Genome-Scale Metabolic models for AppLied reverse ecoLogy
============

Python scripts and workflow by Matthew Jenior, University of Michigan, 2014 - 2016

---------------------------------------------------------------------------

The function of this package is to observe putative metabolic requirements, interaction, and activity of bacteria with the intention of inferring ecological interaction

KEGG reference files and reference creation script can be found in the support directory

Examples of input files for each program can be found in the examples directory

---------------------------------------------------------------------------

# Index:

**Section 1:**  Generating bipartite metabolic models used in conjunction with transcriptomics

**Section 2:**  Generating SCC networks of compounds only to derive source and sink lists

**Section 3:**  Comparing source and sink compounds to infer ecological interaction

**Section 4:**  Appendix describing example files for each script

---------------------------------------------------------------------------

# Section 1 - bipartite_graph.py
Calculates relative importance of a given metabolite based on the expression of surrounding enzymes in a metabolic network

# Basic usage:
python bipartite_graph.py ko_expression.list

# Additional Options:
*Positional, required argument:**

input_file

**Optional arguments:**

-h, --help		show this help message and exit

--name NAME		Organism or other name for KO+expression file (default is organism)

--min MIN		minimum importance value to report

--degree DEGREE		minimum degree value to report

--iters ITERS		iterations for random distribution subsampling
  
---------------------------------------------------------------------------

# Section 2 - scc_graph.py
Purpose is to calculate seeds compounds to genome-scale metabolic networks according to KEGG annotation
SCC algorithm from Borenstein E. et al. (2008). Large-scale reconstruction and phylogenetic analysis of metabolic environments.

# Basic usage:
python scc_graph.py ko.list

# Additional Options:
**Positional, required argument:**

input_file

**Optional arguments:**

-h, --help	show this help message and exit

--giant GIANT	Only focus on the largest component or not

--component COMPONENT	Minimum threshold for SCC size to be included

--confidence CONFIDENCE		Minimum confidence value allowed for seeds

---------------------------------------------------------------------------

# Section 3 - interact_scc.py

Calculating the interaction indices between seed files of 2 organisms
This refers to the directories of files generated by scc_graph.py
Interaction metrics from Levy R., & Borenstein E. (2013). Metabolic modeling of species 
interaction in the human microbiome elucidates community-level assembly rules.

# Basic usage:
python interact_scc.py --seedfiles1 organism_1.seedfiles --seedfiles2 organism_2.seedfiles

# Additional Options:
**Required arguments:**

--seedfiles1 SEEDFILES1		 Directory of SCC network output for first (meta)organism

--seedfiles2 SEEDFILES2		Directory of SCC network output for second (meta)organism

**Optional arguments:**

-h, --help		show this help message and exit

--name1 NAME1		Name of first (meta)organism

--name2 NAME2		Name of second (meta)organism

--confidence CONFIDENCE		Minimum confidence values for seeds and sinks to be considered in calculations

--quiet QUIET		Turns on verbose output mode

#----------------------------------------------------------------------------------------------------------#

# Section 4 - Appendix

Sample files to be used for practice with each of the respective scripts

ko_expression.list - list of KO codes and corresponding expression values for Clostridium difficile strain 630   
ko.list - list of KEGG gene codes and corresponding KO codes for the genome of Clostridium difficile strain 630   
organism_1.seedfiles and organism_2.seedfiles - Output of calc_seeds.py for Clostridium difficile 630 and Eubacterium rectale ATCC 33656   
