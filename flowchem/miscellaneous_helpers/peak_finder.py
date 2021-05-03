"""
Peak finder should take a csv file (pandas dataframe?) and identify peaks present. It should take peaks of specified Retention time,
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
import pandas
import matplotlib
from numpy import trapz

chromatogram = pandas.read_csv(r'C:\Users\jwolf\Documents\flowchem\flowchem\miscellaneous_helpers\anomericmixjbw17highconzSugar-c18_01-Mar-21 3_28_42 PM_012 - PDA-1- Channel 1.txt', header=17, delimiter="	", skip_blank_lines=False)

blank_chromatogram = pandas.read_csv(r'C:\Users\jwolf\Documents\flowchem\flowchem\miscellaneous_helpers\blankSugar-c18_01-Mar-21 3_06_55 PM_011 - PDA-1- Channel 1.txt', header=17, delimiter="	", skip_blank_lines=False)

ax=chromatogram.plot(x='[Min.]', y="[mAU]")

# subtracting a blank background would be better I think: shows to work kind of well.
# Only problem is if there is an offset in x-direction, this offset will create "phasing" so negativbe then positive or vice versa

chromatogram["[mAU]"] -= blank_chromatogram["[mAU]"]
chromatogram.fillna(inplace=True, value=0)
chromatogram.plot(ax=ax,x='[Min.]', y="[mAU]")


peaks=peakutils.peak.indexes(chromatogram['[mAU]'], thres=0.1, min_dist=30) # thres and dist are important
peakdata = chromatogram.iloc[peaks]
#
# # baseline calculation does not work I have the impression, deg3 and higher don't change anything...
# baseline = peakutils.baseline(chromatogram['[mAU]'])
# chrombase = chromatogram
# chrombase['[mAU]'] = baseline
# chrombase.plot(ax=ax, x='[Min.]', y="[mAU]")

# just get the area of interest anc calculate the trapezoidal area beneath the baseline and beneath the signal. The difference should correct for negative baseline, also
# use numpy.trapz it caan also just use specified values




# what is missing is determination of start and end of  the signal. the would be the intersection of baseline and signal curve.
# but this is not reliable. Should better be done by deviation within a certain window -> if five consecutive x-values have comparable y-values it is not in the peak. Ideally, large deviation
# possible would be assuming gaussian shape.
# big problem: start and end point. But try with window approach, if inside the window the deviation is high, go left/right

# triangulation method would come with the benefit of a better peak start and peak end point determination

peaks=peakutils.peak.indexes(chromatogram['[mAU]'], thres=0.1, min_dist=30) # thres and dist are important
peakdata = chromatogram.iloc[peaks]





