#!/usr/bin/env python
# coding: utf-8

import os
import sys
import platform

def mkdir(thisdir):
    if not os.path.isdir(thisdir):
        os.mkdir(thisdir)

def setup_environment():
    paths = dict()
    paths['HOME'] = os.path.expanduser('~')

    paths['Developer'] = os.path.join(paths['HOME'], 'Developer')
    paths['repodir'] = os.path.join(paths['Developer'], 'KSCRocketSeismoHydrology', 'Python', 'new_workflow')

    # Path to oldest code
    #paths['src'] = os.path.join(paths['Developer'], 'kitchensinkGT', 'PROJECTS', 'ROCKETSEIS', 'launchpad_erosion')

    paths['work'] = os.path.join(paths['HOME'], 'work')
    paths['local_outdir'] = os.path.join(paths['work'], 'PROJECTS', 'KSC_EROSION')    
    
    OS = platform.system()
    if OS == 'Windows':
        paths['DROPBOX_TOP'] = 'D:/Dropbox' 
    else:
        paths['DROPBOX_TOP'] = os.path.join(paths['HOME'], 'Dropbox')
        if OS=='Darwin':
            paths['new_data']=os.path.join(paths['HOME'], 'data', 'KSCwell')
        else:
            paths['new_data']='/data/KSC/EROSION/fromdropboxinventory'

    print(platform.system())

    if os.path.isdir(paths['DROPBOX_TOP']):
        # For Well data conversion from Campbell Scientific datalogger format to Pickle Files, and eventually SDS
        #paths['DROPBOX_DATA_TOP'] = os.path.join(paths['DROPBOX_TOP'], 'DATA', 'KSC', 'KSC_Well_Seismoacoustic_Data', 'WellData')
        paths['DROPBOX_DATA_TOP'] = os.path.join(paths['DROPBOX_TOP'], 'PROFESSIONAL', 'RESEARCH', '3_Project_Documents', 'NASAprojects', '201602_Rocket_Seismology', 'DATA', '2022_DATA')
        paths['dropbox_outdir'] = os.path.join(paths['DROPBOX_DATA_TOP'], 'new_workflow')
        paths['WELLDATA_TOP'] = os.path.join(paths['DROPBOX_TOP'], 'PROFESSIONAL', 'RESEARCH', '3_Project_Documents', 'NASAprojects', '201602_Rocket_Seismology', 'DATA', '2022_DATA', 'WellData')
        paths['TOB3_DIR'] = os.path.join(paths['WELLDATA_TOP'], 'Uploads')

    #paths['lookuptable'] = os.path.join(paths['repodir'],'lookuptable.csv') # old workflow
    #paths['transducersCSVfile'] = os.path.join(paths['repodir'], 'transducer_metadata_old.csv') # does not exist need to get from linux
    paths['transducersCSVfile'] = os.path.join(paths['repodir'], 'transducer_metadata_new.csv') 
    

    return paths

def setup_iceweb(paths):

    ''' ICEWEB RELATED STUFF - need to tailor this to remove duplicates '''

    # get the following libraries from tremorExplorer/lib or from kitchenSinkGT/lib ?
    # but probably pointless since cannot actually import to functions that need them from here
    #paths['tremor_explorer_lib'] = os.path.join(paths['Developer'], 'tremorExplorer', 'lib')
    #sys.path.append(paths['tremor_explorer_lib'])  
    #import FDSNtools
    #import wrappers
    #import SDS    

    # read general iceweb config
    paths['CONFIGDIR'] = os.path.join(paths['Developer'], 'tremorExplorer', 'config')
    if not 'PRODUCTS_TOP' in locals():
        PRODUCTS_TOP=None
    configDict = wrappers.read_config(configdir=paths['CONFIGDIR'], PRODUCTS_TOP=PRODUCTS_TOP)
    paths['SDS_TOP'] = configDict['general']['SDS_TOP']
    paths['RSAM_DIR'] = configDict['general']['RSAM_TOP']
    '''
    paths['SDS_TOP'] = os.path.join(paths['local_outdir'], 'SDS')
    paths['DB_DIR'] = os.path.join(paths['local_outdir'], 'db')
    paths['RSAM_DIR'] = os.path.join(paths['local_outdir'], 'RSAM')

    '''
    subnet = 'KSC'
    paths['CONFIGDIR'] = os.path.join(paths['src'], 'iceweb_config')
    configDict = wrappers.read_config(configdir=paths['CONFIGDIR'], leader=subnet)
    paths['SDS_TOP'] = configDict['general']['SDS_TOP']
    paths['RSAM_DIR'] = os.path.join(configDict['general']['PRODUCTS_TOP'], 'RSAM')   

    return paths

if __name__ == "__main__":
    paths = setup_environment()
    print(paths)
    print("sys.path\n",sys.path)
    print('Testing imports')
    sys.path.append(os.path.join(paths['repodir'], 'campbell'))
    import read_cs_files as campbell    
    import libWellData as LLE    

    # These are imports to make within calling code
    #import os
    #import sys
    #import glob
    #import numpy as np
    #import pandas as pd
    #from obspy.core import read, Stream, UTCDateTime

