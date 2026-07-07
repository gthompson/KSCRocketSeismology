#!/usr/bin/env python
# coding: utf-8
import header
paths = header.setup_environment()
import os
#import sys
#import glob
#import numpy as np
import pandas as pd
#from obspy.core import read, Stream, UTCDateTime
#import FDSNtools
#import wrappers
import SDS
import Python.libWellData_wrong as LLE

# Parse lookuptable
lookuptableDF = LLE.removed_unnamed_columns(pd.read_csv(paths['lookuptable']))
lookuptableDF.to_csv('lookuptable_backup.csv')
lookuptableDF = lookuptableDF.sort_values(by=['starttime'])
lookuptableDF['miniseed'] = False
print(paths)

transducersDF = LLE.removed_unnamed_columns(pd.read_csv(paths['transducersCSVfile']))
MSEED_DIR = os.path.join(paths['outdir'], 'miniseed')
#os.system(f"rm -rf {MSEED_DIR}/*")
for index, row in lookuptableDF.iterrows():
    print(f"{index}, {row['sourcefile']}, {row['passed']}")    
    df = LLE.removed_unnamed_columns(pd.read_csv(os.path.join(paths['CORRECTED'],row['outputfile'])))
    df['datetime'] = [UTCDateTime(ts).datetime for ts in df['TIMESTAMP']]
    df.plot(x='datetime')
    print(df.columns)
    #successful = LLE.convert2mseed(df2, MSEED_DIR, transducersDF)


