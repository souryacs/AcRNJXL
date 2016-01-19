#!/usr/bin/env python

"""
program for species tree estimation
computes four criteria - 
1) Level / branch count information
2) Accumulated Rank statistics 
"""

import dendropy
from optparse import OptionParser
import math
import time
import os
import numpy
import sys

# these variables store the respective parameters of input gene trees
COMPLETE_INPUT_TAXA_LIST = []

""" this dictionary defines the taxa pair relations
each entry is indexed by two nodes """
TaxaPair_Reln_Dict = dict()

# this is the debug level
# set for printing the necessary information
DEBUG_LEVEL = 0

# variables depicting the method employed for species tree construction
# first two methods use average statistics of the coalescence rank or the branch count
# last two methods employ the mode statistics

# accumulated coalescence rank with average statistics
AcRNJ = 1

## accumulated coalescence rank with mode based statistics
#AcRMNJ = 2

# product of accumulated coalescence rank and extra lineage statistics
ProdAcRNJXL = 2

# minimum of accumulated coalescence rank and excess gene count
RankAcRNJXL = 3

# product of coalescence rank and extra lineage statistics
ProdRNJXL = 4

# minimum of accumulated coalescence rank and excess gene count
RankRNJXL = 5

# variables used to denote whether we use traditional NJ method
# or use a variant of it, namely the agglomerative clustering
TRADITIONAL_NJ = 1
AGGLO_CLUST = 2

# add - sourya
MODE_PERCENT = 0.5

MODE_BIN_COUNT = 40

# this list corresponds to various rank merging algorithm
SIMPLE_SUM_RANK = 1
MEAN_RECIPROCAL_RANK = 2

##-----------------------------------------------------
""" 
this class defines the connectivity relationship between a pair of taxa
initially the information are obtained from the input source trees
"""
class Reln_TaxaPair(object):  
	def __init__(self):
		# this is the count of trees for which the couplet is supported
		self.tree_support_count = 0        
		# this list contains the accumulated sum of ranks of the internal nodes
		# present between individual couplets, for all the gene trees
		# corresponds to AcRNJ or AcRMNJ
		self.accumulated_rank_list = []
		# this is the extra lineage count list for this couplet
		self.XL_val_list = []            
		"""
		this is a variable containing the binned average of the XL values
		of very high frequency
		initially the value is set as -1, to signify that the computation is not done
		once the computation (for a couplet) is done, the value is subsequently used and returned
		"""
		self.binned_avg_XL = -1
		
		self.avg_XL = -1
		self.median_XL = -1
		
		"""
		this is a variable containing the binned average of the accumulated rank values
		of very high frequency
		initially the value is set as -1, to signify that the computation is not done
		once the computation (for a couplet) is done, the value is subsequently used and returned
		"""
		self.binned_avg_AcR = -1
		
	# this function adds the count of tree according to the support of 
	# corresponding couplet in the input tree
	def _IncrSupportTreeCount(self):
		self.tree_support_count = self.tree_support_count + 1
					
	# this function returns the number of trees supporting the couplet
	def _GetSupportTreeCount(self):
		return self.tree_support_count        
				
	def _AddXLVal(self, val):
		self.XL_val_list.append(val)

	def _GetAvgXLVal(self):
		if (self.avg_XL == -1):
			self.avg_XL = (sum(self.XL_val_list) * 1.0) / self.tree_support_count
		return self.avg_XL
				
	def _MedianXLVal(self):
		if (self.median_XL == -1):
			self.median_XL = numpy.median(numpy.array(self.XL_val_list))
		return self.median_XL
				
	#def _GetMultiModeXLVal(self):
		#candidate_score_sum = 0
		#candidate_freq_sum = 0
		#curr_arr = numpy.array(self.XL_val_list)
		## returns the counts of individual elements
		## array size: max_elem + 1
		#counts = numpy.bincount(curr_arr)
		## remove the zero values 
		#values = numpy.nonzero(counts)[0]
		## mode value and corresponding frequency
		#mode_val = numpy.argmax(counts)
		#mode_count = numpy.max(counts)
		## check for the values having frequency at least half of the maximum frequency
		#for v in values:
			#if (counts[v] >= 0.25 * mode_count):
				#candidate_score_sum = candidate_score_sum + (v * counts[v])
				#candidate_freq_sum = candidate_freq_sum + counts[v]
		#return (candidate_score_sum * 1.0) / candidate_freq_sum                

	#def _GetMultiModeXLVal(self):
		#candidate_score_sum = 0
		#candidate_freq_sum = 0
		#curr_arr = numpy.array(self.XL_val_list)
		#uniqw, inverse = numpy.unique(curr_arr, return_inverse=True)
		#counts = numpy.bincount(inverse)
		## remove the zero values 
		#values = numpy.nonzero(counts)[0]
		## mode value and corresponding frequency
		#mode_count = numpy.max(counts)
		
		##print '*****************'
		##print 'curr_arr: ', curr_arr
		##print 'uniqw: ', uniqw
		##print 'inverse: ', inverse
		##print 'counts: ', counts
		##print 'values: ', values
		##print 'mode_count: ', mode_count
		
		## check for the values having frequency at least half of the maximum frequency
		#for v in values:
			#if (counts[v] >= MODE_PERCENT * mode_count):
				##candidate_score_sum = candidate_score_sum + (v * counts[v])	# comment - sourya
				#candidate_score_sum = candidate_score_sum + (uniqw[v] * counts[v])	# add - sourya
				#candidate_freq_sum = candidate_freq_sum + counts[v]
		#return (candidate_score_sum * 1.0) / candidate_freq_sum        

	#-----------------------------------------------
	def _GetMultiModeXLVal(self, Output_Text_File=None):
		if (self.binned_avg_XL == -1):
			
			Bin_Width = ((max(1.0, max(self.XL_val_list)) * 1.0) / MODE_BIN_COUNT)
			len_list = [0] * MODE_BIN_COUNT
			
			if Output_Text_File is not None:
				fp = open(Output_Text_File, 'a') 
			
			# sort the XL list
			self.XL_val_list.sort()
			
			for j in range(len(self.XL_val_list)):
				curr_xl_val = self.XL_val_list[j]
				bin_idx = int(curr_xl_val / Bin_Width)
				#print 'XL-----bin idx: ', bin_idx
				if (bin_idx == MODE_BIN_COUNT):
					bin_idx = bin_idx - 1
				len_list[bin_idx] = len_list[bin_idx] + 1
			
			if Output_Text_File is not None:
				for i in range(MODE_BIN_COUNT):
					fp.write('\n bin idx: ' + str(i) + ' len:  ' + str(len_list[i]))
			
			# this is the maximum length of a particular bin
			# corresponding to max frequency
			max_freq = max(len_list)
			
			if Output_Text_File is not None:
				fp.write('\n Max freq: ' + str(max_freq))
			
			num = 0
			denom = 0
			for i in range(MODE_BIN_COUNT):
				if (len_list[i] >= (MODE_PERCENT * max_freq)):
					list_start_idx = sum(len_list[:i])
					list_end_idx = list_start_idx + len_list[i] - 1
					value_sum = sum(self.XL_val_list[list_start_idx:(list_end_idx+1)])
					num = num + value_sum
					denom = denom + len_list[i]
					if Output_Text_File is not None:
						fp.write('\n Included bin idx: ' + str(i) + ' starting point: ' + str(list_start_idx) \
							+ 'ending point: ' + str(list_end_idx) + ' sum: ' + str(value_sum))
			
			self.binned_avg_XL = (num / denom)
			
			if Output_Text_File is not None:
				fp.write('\n Final binned average XL: ' + str(self.binned_avg_XL))
				fp.close()
			
		return self.binned_avg_XL
	#-----------------------------------------------

	def _AddAccumulatedRank(self, val):
		self.accumulated_rank_list.append(val)
		
	def _GetAvgAccumulatedRank(self):
		return (sum(self.accumulated_rank_list) * 1.0) / self.tree_support_count
							
	def _GetMedianAccumulatedRank(self):
		return numpy.median(numpy.array(self.accumulated_rank_list))
							
	#def _GetMultiModeAccumulatedRank(self):
		#candidate_score_sum = 0
		#candidate_freq_sum = 0
		#curr_arr = numpy.array(self.accumulated_rank_list)
		## returns the counts of individual elements
		## array size: max_elem + 1
		#counts = numpy.bincount(curr_arr)
		## remove the zero values 
		#values = numpy.nonzero(counts)[0]
		## mode value and corresponding frequency
		#mode_val = numpy.argmax(counts)
		#mode_count = numpy.max(counts)
		## check for the values having frequency at least half of the maximum frequency
		#for v in values:
			#if (counts[v] >= 0.25 * mode_count):
				#candidate_score_sum = candidate_score_sum + (v * counts[v])
				#candidate_freq_sum = candidate_freq_sum + counts[v]
		#return (candidate_score_sum * 1.0) / candidate_freq_sum

	#def _GetMultiModeAccumulatedRank(self):
		#candidate_score_sum = 0
		#candidate_freq_sum = 0
		#curr_arr = numpy.array(self.accumulated_rank_list)
		#uniqw, inverse = numpy.unique(curr_arr, return_inverse=True)
		#counts = numpy.bincount(inverse)
		## remove the zero values 
		#values = numpy.nonzero(counts)[0]
		## mode value and corresponding frequency
		#mode_count = numpy.max(counts)
		
		##print '*****************'
		##print 'curr_arr: ', curr_arr
		##print 'uniqw: ', uniqw
		##print 'inverse: ', inverse
		##print 'counts: ', counts
		##print 'values: ', values
		##print 'mode_count: ', mode_count
		
		## check for the values having frequency at least half of the maximum frequency
		#for v in values:
			#if (counts[v] >= MODE_PERCENT * mode_count):
				##candidate_score_sum = candidate_score_sum + (v * counts[v])	# comment - sourya
				#candidate_score_sum = candidate_score_sum + (uniqw[v] * counts[v])	# add - sourya
				#candidate_freq_sum = candidate_freq_sum + counts[v]
		#return (candidate_score_sum * 1.0) / candidate_freq_sum        

	#-----------------------------------------------

	def _GetMultiModeAccumulatedRank(self, Output_Text_File=None):
		if (self.binned_avg_AcR == -1):
			
			Bin_Width = ((max(self.accumulated_rank_list) * 1.0) / MODE_BIN_COUNT)
			len_list = [0] * MODE_BIN_COUNT
			
			if Output_Text_File is not None:
				fp = open(Output_Text_File, 'a') 
			
			# sort the AcR list
			self.accumulated_rank_list.sort()
			
			for j in range(len(self.accumulated_rank_list)):
				curr_AcR_val = self.accumulated_rank_list[j]
				bin_idx = int(curr_AcR_val / Bin_Width)
				#print 'AcR-----bin idx: ', bin_idx
				if (bin_idx == MODE_BIN_COUNT):
					bin_idx = bin_idx - 1
				len_list[bin_idx] = len_list[bin_idx] + 1
			
			if Output_Text_File is not None:
				for i in range(MODE_BIN_COUNT):
					fp.write('\n bin idx: ' + str(i) + ' len:  ' + str(len_list[i]))
			
			# this is the maximum length of a particular bin
			# corresponding to max frequency
			max_freq = max(len_list)
			
			if Output_Text_File is not None:
				fp.write('\n Max freq: ' + str(max_freq))
			
			num = 0
			denom = 0
			for i in range(MODE_BIN_COUNT):
				if (len_list[i] >= (MODE_PERCENT * max_freq)):
					list_start_idx = sum(len_list[:i])
					list_end_idx = list_start_idx + len_list[i] - 1
					value_sum = sum(self.accumulated_rank_list[list_start_idx:(list_end_idx+1)])
					num = num + value_sum
					denom = denom + len_list[i]
					if Output_Text_File is not None:
						fp.write('\n Included bin idx: ' + str(i) + ' starting point: ' + str(list_start_idx) \
							+ 'ending point: ' + str(list_end_idx) + ' sum: ' + str(value_sum))
			
			self.binned_avg_AcR = (num / denom)
			
			if Output_Text_File is not None:
				fp.write('\n Final binned average AcR: ' + str(self.binned_avg_AcR))
				fp.close()
			
		return self.binned_avg_AcR

	#-----------------------------------------------
	# this function prints information for the current couplet
	def _PrintTaxaPairRelnInfo(self, key, out_text_file, METHOD_USED):
		fp = open(out_text_file, 'a')    
		fp.write('\n taxa pair key: ' + str(key))
		fp.write('\n supporting number of trees: ' + str(self._GetSupportTreeCount()))
		if (METHOD_USED == AcRNJ):
			#fp.write('\n *** Accumulated rank list: ' + str(sorted(self.accumulated_rank_list)))
			fp.write('\n *** average accumulated rank : ' + str(self._GetAvgAccumulatedRank()))   
			fp.write('\n *** median accumulated rank  : ' + str(self._GetMedianAccumulatedRank()))   
			fp.write('\n *** mode accumulated rank  : ' + str(self._GetMultiModeAccumulatedRank()))   
		elif (METHOD_USED == ProdAcRNJXL) or (METHOD_USED == RankAcRNJXL):
			fp.write('\n *** average accumulated rank  : ' + str(self._GetAvgAccumulatedRank()))   
			fp.write('\n *** median accumulated rank  : ' + str(self._GetMedianAccumulatedRank()))   
			fp.write('\n *** mode accumulated rank  : ' + str(self._GetMultiModeAccumulatedRank()))   
			fp.write('\n *** average XL val : ' + str(self._GetAvgXLVal()))   
			fp.write('\n *** median XL val : ' + str(self._MedianXLVal()))   
			fp.write('\n *** mode XL val : ' + str(self._GetMultiModeXLVal()))   
		elif (METHOD_USED == ProdRNJXL) or (METHOD_USED == RankRNJXL):
			fp.write('\n *** average  coalescence rank : ' + str(self._GetAvgAccumulatedRank()))   
			fp.write('\n *** median coalescence rank  : ' + str(self._GetMedianAccumulatedRank()))   
			fp.write('\n *** mode coalescence rank  : ' + str(self._GetMultiModeAccumulatedRank()))   
			fp.write('\n *** average XL val : ' + str(self._GetAvgXLVal()))   
			fp.write('\n *** median XL val : ' + str(self._MedianXLVal()))   
			fp.write('\n *** mode XL val : ' + str(self._GetMultiModeXLVal()))   
		fp.close()
    
      
