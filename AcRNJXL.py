#!/usr/bin/env python

##---------------------------------------------
''' 
this program is used to generate a spcies tree from a set of gene trees
the gene trees generally associate conflicts among the constituent genes (representing individual taxa)
in terms of the topological relationships
species tree follows simple approach to produce species tree with high performance index

Author: Sourya Bhattacharyya
Dept of CSE, IIT Kharagpur
V1.0 - 12.01.2015 - basic code
V1.1 - 20.02.2015 - written to handle deep coalescence and level sum, and accumulated rank statistics information
V1.2 - 27.02.2015 - handles accumulated coalescence rank sum, and accumulated branch length count
V1.3 - 30.03.2015 - code clean and necessary comments
V1.4 - 10.04.2015 - frequency + mode based couplet feature
V1.5 - 11.04.2015 - couplet feature extraction - timing optimization
V1.6 - 19.06.2015 - added LCA rank and accumulated coalescence rank based feature for species tree estimation
V1.7 - 20.06.2015 - added mode of LCA rank and corresponding species tree estimation technique
V1.8 - 17.07.2015 - added mode of LCA rank and mode of accumulated branch count as a new species tree estimation technique
V2.0 - 24.07.2015 - removed all internode count based methods, and kept methods concerning on accumulated coalescence ranks only
V3.0 - 24.11.2015 - provided a new method using aggregated rank based excess gene leaf count with accumulated coalescence rank 
										for species tree generation
V4.0 - 22.01.2016 - Finalized a method incorporating the filtered average accumulated coalescence rank and excess gene leaf count 
										based species tree inference.
V5.0 - 01.05.2016 - Modified the code to incorporate filtered average AcR and XL measures for species tree construction.
										Corresponds to the release 3.0
V6.0 - 13.09.2016 - Used only accumulated coalescence rank with mode based filtered averaging, to infer the species tree
										Produced better results than AcRNJXL
										Also, recued running time for reading the input trees
''' 
## Copyright 2015, 2016 Sourya Bhattacharyya and Jayanta Mukherjee.
## All rights reserved.
##
## See "LICENSE.txt" for terms and conditions of usage.
##
##---------------------------------------------

import Header
from Header import *
import NJ_SpecTree
from NJ_SpecTree import *
import RankInfo
from RankInfo import *
import UtilFunc
from UtilFunc import *

##-----------------------------------------------------
# this function is useful to parse various options for input data processing
def parse_options():  
	parser = OptionParser()
		
	parser.add_option("-I", "--INPFILE", \
				type="string", \
				action="store", \
				dest="INP_FILENAME", \
				default="", \
				help="name of the input file containing gene trees")

	parser.add_option("-O", "--OUTFILE", \
				type="string", \
				action="store", \
				dest="OUT_FILENAME", \
				default="", \
				help="name of the output file to contain target species tree")  

	parser.add_option("-p", "--inpform", \
				type="int", \
				action="store", \
				dest="inp_file_format", \
				default=1, \
				help="1 - input file format is NEWICK (default) \
				2 - input file format is NEXUS")

	parser.add_option("-m", "--method", \
				type="int", \
				action="store", \
				dest="method_type", \
				default=1, \
				help="1 - Couplet based accumulated coalescence rank (AcRNJ) (Default Method) \
				2 - Couplet based Accumulated Coalescence Rank with Excess Gene Count (AcRNJXL)")
			
	#parser.add_option("-n", "--njrule", \
				#type="int", \
				#action="store", \
				#dest="NJ_type", \
				#default=1, \
				#help="1 - classical NJ method (Default) \
				#2 - Normalized couplet statistic for agglomeration")     

	#parser.add_option("-c", "--coalrankmat", \
				#type="int", \
				#action="store", \
				#dest="acc_rank_mat_type", \
				#default=7, \
				#help="1 - Average of AcR / Rank \
				#2 - median of AcR / Rank \
				#3 - mode of AcR / Rank \
				#4 - min(avg, median) of AcR / Rank \
				#5 - min(avg , median, mode) of AcR / Rank \
				#6 - min(median, mode) of AcR / Rank \
				#7 - avg(avg, mode) of AcR / Rank \
				#8 - min(avg, mode) of AcR / Rank")     

	#parser.add_option("-d", "--distmat", \
				#type="int", \
				#action="store", \
				#dest="dist_mat_type", \
				#default=7, \
				#help="1 - Average of XL \
				#2 - median of XL \
				#3 - mode of XL \
				#4 - min(avg, median) of XL \
				#5 - min(avg , median, mode) of XL \
				#6 - min(median, mode) of XL \
				#7 - avg(avg, mode) of XL \
				#8 - min(avg, mode) of XL")     
			
	parser.add_option("-r", "--ROOT", \
			type="string", \
			action="store", \
			dest="outgroup_taxon_name", \
			default="", \
			help="name of the taxon by which the tree can be rooted (outgroup based rooting)")
			
	opts, args = parser.parse_args()
	return opts, args
  
#-----------------------------------------------------
# main function
def main():  
	opts, args = parse_options()

	ROOTED_TREE = True	#False 
	PRESERVE_UNDERSCORE = True
	if (opts.inp_file_format == 1):
		INPUT_FILE_FORMAT = 'newick'
	else:
		INPUT_FILE_FORMAT = 'nexus'
	INPUT_FILENAME = opts.INP_FILENAME
	OUTPUT_FILENAME = opts.OUT_FILENAME
	
	#----------------------------------
	"""
	employing the various species tree estimation methods along with parameter variations
	"""
	METHOD_USED = opts.method_type
	NJ_RULE_USED = TRADITIONAL_NJ	#opts.NJ_type
	OUTGROUP_TAXON_NAME = opts.outgroup_taxon_name
	FRACT_ACC_RANK = 1
	XL_DIST_MAT_TYPE = 7	#opts.dist_mat_type		#7 #1
	ACC_RANK_DIST_MAT_TYPE = 7	#opts.acc_rank_mat_type	#7	#5
	
	if (INPUT_FILENAME == ""):
		print '******** THERE IS NO INPUT FILE (CONTAINING GENE TREE LIST) SPECIFIED - RETURN **********'
		return
	else:
		print 'input filename: ', INPUT_FILENAME

	"""
	convert the input filename to an absolute path of the filename
	"""
	INPUT_FILENAME = os.path.abspath(INPUT_FILENAME)
	print '*** INPUT_FILENAME: ', INPUT_FILENAME

	"""
	according to the location of input filename
	adjust the locations of the output files as well
	"""
	k = INPUT_FILENAME.rfind("/")
	if (k == -1):
		dir_of_inp_file = './'
	else:
		dir_of_inp_file = INPUT_FILENAME[:(k+1)]
	inp_filename = INPUT_FILENAME[(k+1):]
	if (DEBUG_LEVEL > 2):
		print 'dir_of_inp_file: ', dir_of_inp_file  

	if (OUTPUT_FILENAME == ""):
		"""
		derive the output directory and the output text file which will contain different output text results
		"""
		if (METHOD_USED == AcRNJ):
			dir_of_curr_exec = dir_of_inp_file + 'AcRNJ'
		else:
			dir_of_curr_exec = dir_of_inp_file + 'AcRNJXL'

		if (os.path.isdir(dir_of_curr_exec) == False):
			mkdr_cmd = 'mkdir ' + dir_of_curr_exec
			os.system(mkdr_cmd)

		Output_Text_File = dir_of_curr_exec + '/' + 'Complete_Desription.txt'
		print 'Output_Text_File: ', Output_Text_File      
	
	else:
		"""
		here we have already specified the output species file name (and its corresponding directory)
		"""
		k1 = OUTPUT_FILENAME.rfind("/")
		if (k1 == -1):
			dir_of_curr_exec = './'
		else:
			dir_of_curr_exec = OUTPUT_FILENAME[:(k1+1)]
		Output_Text_File = OUTPUT_FILENAME + '_complete_text_description'   
		print 'Output_Text_File: ', Output_Text_File
		if (os.path.isdir(dir_of_curr_exec) == False):
			mkdr_cmd = 'mkdir ' + dir_of_curr_exec
			os.system(mkdr_cmd)               

	# note the program beginning time 
	start_timestamp = time.time()

	#-------------------------------------------------------------
	""" 
	read the collection of source trees 
	and store it in a treelist structure
	"""
	Gene_TreeList = Read_Input_Treelist(ROOTED_TREE, PRESERVE_UNDERSCORE, INPUT_FILE_FORMAT, INPUT_FILENAME)
	#-------------------------------------------------------------
	"""
	find the taxa set covered in the source trees
	"""
	for tr_idx in range(len(Gene_TreeList)):
		taxa_labels_curr_tree = Gene_TreeList[tr_idx].infer_taxa().labels()
		for i in range(len(taxa_labels_curr_tree)):
			if taxa_labels_curr_tree[i] not in COMPLETE_INPUT_TAXA_LIST:
				COMPLETE_INPUT_TAXA_LIST.append(taxa_labels_curr_tree[i])
	#---------------------------------------------
	"""
	from input trees, compute couplet based features - 1) accumulated coalescence rank, 2) excess gene leaf count
	"""
	for tr_idx in range(len(Gene_TreeList)):
		DeriveCoupletRelations(Gene_TreeList[tr_idx], METHOD_USED, FRACT_ACC_RANK)

	# note the time
	end_timestamp = time.time() 

	# note the time taken for reading the dataset
	time_read_dataset = (end_timestamp - start_timestamp)

	fp = open(Output_Text_File, 'w')    
	fp.write('\n  total no of taxa: ' + str(len(COMPLETE_INPUT_TAXA_LIST)))
	fp.write('\n \n ===============>>>>>>>>>>>>>>> TIME TAKEN FOR READING THE INPUT GENE TREES ' + str(time_read_dataset))
	fp.close()
	
	"""
	print individual couplet information
	"""
	if (DEBUG_LEVEL >= 2):
		for coup in TaxaPair_Reln_Dict:
			TaxaPair_Reln_Dict[coup]._PrintTaxaPairRelnInfo(coup, Output_Text_File, METHOD_USED)
	
	#---------------------------
	# add - sourya
	#if (RANK_WRITE_DEBUG == 1):
		#-------------------------------------
		## comment - sourya
		
		#if 0:
			#"""
			#plotting the coalescence rank information
			#"""
			#fig1 = plt.figure()
			#n1, bins1, patches1 = plt.hist(Coal_Rank_Complete_List, len(COMPLETE_INPUT_TAXA_LIST), normed=0, facecolor='blue', alpha=0.75)
			#xlabel_str = 'Coalescence Rank'
			#plt.xlabel(xlabel_str, fontsize=24)
			#plt.ylabel('Frequency', fontsize=24)
			#title_str = 'Distribution of Coalescence rank for couplets'
			#plt.title(title_str, fontsize=24)
			#plt.grid(True)
			##plt.tight_layout()
			#fig1.set_size_inches(10, 6)
			#plt.savefig(Coal_Rank_Filename)
		
			#"""
			#plotting the accumulated coalescence rank information
			#"""
			#fig1 = plt.figure()
			#n1, bins1, patches1 = plt.hist(AcR_Complete_List, (len(COMPLETE_INPUT_TAXA_LIST) * len(COMPLETE_INPUT_TAXA_LIST)), \
				#normed=0, facecolor='blue', alpha=0.75)
			#xlabel_str = 'Accumulated Coalescence Rank'
			#plt.xlabel(xlabel_str, fontsize=24)
			#plt.ylabel('Frequency', fontsize=24)
			#title_str = 'Distribution of Accumulated Coalescence rank for couplets'
			#plt.title(title_str, fontsize=24)
			#plt.grid(True)
			##plt.tight_layout()
			#fig1.set_size_inches(10, 6)
			#plt.savefig(AcR_Filename)
		
		## end comment - sourya
			
		#Entropy_Coal_Rank = Compute_Entropy(numpy.array(Coal_Rank_Complete_List), Output_Text_File)
		
		#if 1:	#(DEBUG_LEVEL >= 2):
			#fp = open(Output_Text_File, 'a')
			#fp.write('\n\n *** Computed entropy for the Coalescence rank information :  ' + str(Entropy_Coal_Rank) + '\n\n')
			#fp.close()
		
		#Entropy_AcR = Compute_Entropy(numpy.array(AcR_Complete_List), Output_Text_File)
		
		#if 1:	#(DEBUG_LEVEL >= 2):
			#fp = open(Output_Text_File, 'a')
			#fp.write('\n\n *** Computed entropy for the Accumulated Coalescence rank information :  ' + str(Entropy_AcR) + '\n\n')
			#fp.close()
		
		#fp = open(Output_Text_File, 'a')
		#fp.write('\n\n *** Information gain :  ' + str(Entropy_AcR / Entropy_Coal_Rank) + '\n\n')
		#fp.close()
		
		#-------------------------------------
	# end add - sourya
	#---------------------------
	
	"""
	initially generate the output species tree as a star
	covering all the taxa covered in the input gene trees
	"""
	star_net_str = ""
	for i in range(len(COMPLETE_INPUT_TAXA_LIST)):
		star_net_str = star_net_str + str(COMPLETE_INPUT_TAXA_LIST[i])
		if (i < (len(COMPLETE_INPUT_TAXA_LIST) - 1)):
			star_net_str = star_net_str + ","
	star_net_str = "(" + star_net_str + ")"

	"""
	this tree denotes the initial star configuration (rooted at the central hub)
	"""
	Output_Tree = dendropy.Tree.get_from_string(star_net_str, schema="newick", \
								preserve_underscores=PRESERVE_UNDERSCORE, \
								default_as_rooted=True)          

	if 0:
		fp = open(Output_Text_File, 'a')    
		fp.write('\n star_net_str: ' + str(star_net_str))
		fp.write('\n from tree ---: ' + Output_Tree.as_newick_string())
		fp.close()

	"""
	This is the main function which will convert the star tree into the final binary species tree
	using a NJ based agglomeration technique
	with the features accumulated coalescence rank and excess gene leaf count
	"""
	Form_Species_Tree_NJ_Cluster(Output_Tree, COMPLETE_INPUT_TAXA_LIST, METHOD_USED, \
		NJ_RULE_USED, Output_Text_File, XL_DIST_MAT_TYPE, ACC_RANK_DIST_MAT_TYPE)

	# note the time
	end_timestamp = time.time()      

	fp = open(Output_Text_File, 'a')
	fp.write('\n --- output species tree (in newick format): ' + Output_Tree.as_newick_string())    
	fp.close()

	out_treefilename = dir_of_curr_exec + '/' + 'outtree_Newick.tre'

	"""
	write the species tree in the specified output file
	"""
	outfile = open(out_treefilename, 'w')
	outfile.write(Output_Tree.as_newick_string())	
	outfile.close()

	#-----------------------------------
	# add  -sourya
	"""
	if user specifies one outgroup taxon name for rooting the tree, 
	we should reroot the tree and save it
	"""
	if (OUTGROUP_TAXON_NAME != ""):
		# first we root the tree using the specified outgroup node
		outgroup_node = Output_Tree.find_node_with_taxon_label(OUTGROUP_TAXON_NAME)
		if (outgroup_node is not None):
			Output_Tree.to_outgroup_position(outgroup_node, update_splits=False)
		
		out_treefilename = dir_of_curr_exec + '/' + 'outtree_Newick.tre.rooted'

		# we write the unweighted supertree
		outfile = open(out_treefilename, 'w')
		outfile.write(Output_Tree.as_newick_string())	
		outfile.close()
	# end add  -sourya
	#-----------------------------------

	# we write the time associated with the execution of this method
	fp = open(Output_Text_File, 'a')
	fp.write('\n \n\n ===============>>>>>>>>>>>>>>> TIME COMPLEXITY OF THE METHOD (in seconds) ')
	fp.write('\n \n Total time taken (in seconds) : ' + str(end_timestamp - start_timestamp))
	fp.close()

	# clear the storage  variables
	TaxaPair_Reln_Dict.clear()
	if (len(COMPLETE_INPUT_TAXA_LIST) > 0):
		COMPLETE_INPUT_TAXA_LIST[:] = []
  
#-----------------------------------------------------
if __name__ == "__main__":
	main() 




