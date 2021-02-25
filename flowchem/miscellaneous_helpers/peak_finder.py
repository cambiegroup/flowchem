"""
Peak finder should take a csv file and identify peaks present. It should take peaks of specified Retention time,
with some safety margin and detect the maximum.
Then it should calculate the area. For that, the baseline has to be
subtracted.
Then, either incrementally the area of rectangles is added up or the peak shape fitted with eg gauss
function.
This will be integrated against the baseline.
Before, the rough position of  alpha and beta needs to be know, maybe MS should be used for that? PProblem is that one
of the two needs to be assigned by isolated product
"""
import peakutils

