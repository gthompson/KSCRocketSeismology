#!/usr/bin/env python
# coding: utf-8

import os
import glob
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
import datetime
import obspy
import matplotlib.pyplot as plt
plt.rcParams['axes.formatter.useoffset'] = False # do not allow relative y-labels

def find_all(a_str, sub):
    start = 0
    while True:
        start = a_str.find(sub, start)
        if start == -1: return
        yield start
        start += len(sub) # use start += 1 to find overlapping matches

def read_rt130_1_file(rt130file):
    #print('Processing %s' % rt130file, end="\r", flush=True)
    all_lats = [] 
    londeg = None
    latdeg = None
    output = os.popen('strings %s' % rt130file).read()
    if output: 

        lines = output.split('\n')

        lineindex = 1
        latindex = lines[lineindex].find('YABBBBBC        N ')
        if latindex == -1:
            for i, line in enumerate(lines):
                latindex = line.find('YABBBBBC        N ')
                if latindex > -1:
                    lineindex = i
                    break
                else:
                    latindex = line.find(' N ')
                    if latindex > -1:
                        lineindex = i
                        latindex -= 15
        if latindex > -1:
            latindex += 15
            try:
                lonindex = list(find_all(lines[lineindex][latindex:latindex+20], 'W'))[0]+latindex
                latdeg = float(lines[lineindex][latindex+3:latindex+5])
                latmin = float(lines[lineindex][latindex+5:latindex+11])
                latdeg = latdeg + latmin/60
                londeg = float(lines[lineindex][lonindex+1:lonindex+4])
                lonmin = float(lines[lineindex][lonindex+4:lonindex+10])
                londeg = -(londeg + lonmin/60)    
            except:
                print(lineindex, latindex, lines[lineindex]) 

        all_indexes = list(find_all(output, 'POSITION'))

        for each_index in all_indexes:
            
            Ndeg = output[each_index+11:each_index+13]
            Nmin = output[each_index+14:each_index+16]
            Nsec = output[each_index+17:each_index+22]
            Ndecdeg = float(Ndeg) + float(Nmin)/60 + float(Nsec)/3600
            if Ndecdeg > 28.0 and Ndecdeg < 29.0:
                all_lats.append(Ndecdeg)

        STATIONS = ['BHP', 'TANK', 'FIRE', 'BCHH', 'DVEL', 'RBLAB']
        stationcodes = []
        for station in STATIONS:
            stationindex = output.find(station)
            if stationindex > -1:
                stationcodes.append( output[stationindex:stationindex+4].strip() )   

    return latdeg, londeg, all_lats, list(set(stationcodes))

def create_summary1file(SVCDIR, RAWDIR):
    """ Parse RT130 1/* files to reconstruct digitizer-GPS_Position history
    This generates a DataFrame/CSV file like:
    

    """
        
    positionDF = pd.DataFrame(columns = ['Digitizer', 'DateTime', 'Station', 'Latitude', 'Longitude', 'Latitude2', 'Latitude2std'])
    digitizerList = list()
    filetimeList = list()
    stationList = list()
    latitudeList = list()
    longitudeList = list()
    latitudeList2 = list()
    latitudeSTDList2 = list()
    lod = []
    lastlenlod = 0

    summary1file = os.path.join(SVCDIR, 'summary1file.csv')
    if os.path.exists(summary1file):
        os.remove(summary1file)
    
    cfdirs = sorted(glob.glob('%s/*.cf' % RAWDIR))
    for cfdir in cfdirs:
        dayfullpaths = sorted(glob.glob(os.path.join(cfdir, '20?????')))
        count = 0
        for thisdayfullpath in dayfullpaths:
            count = count + 1
            print(f'{cfdir}: Processing {thisdayfullpath}')
            thisdaydir = os.path.basename(thisdayfullpath) # a directory like 2018365
            digitizerpaths = sorted(glob.glob('%s/????' % thisdayfullpath))
            for digitizerpath in digitizerpaths:
                thisDigitizer = os.path.basename(digitizerpath)
                rt130files = sorted(glob.glob('%s/1/*' % digitizerpath))
                if rt130files:  
                    for rt130file in rt130files:
                        filetime = os.path.basename(rt130file)[0:6]
                        thistime = obspy.UTCDateTime.strptime(thisdaydir + filetime, '%Y%j%H%M%S')
                        latdeg, londeg, all_lats, stationcodes = read_rt130_1_file(rt130file)
                        thisDict = {'Digitizer':thisDigitizer, 'DateTime':thistime.datetime, 'Station':stationcodes, 'Latitude':latdeg, 'Longitude':londeg, 'Latitude2':np.nanmedian(all_lats), 'Latitude2std':np.nanstd(all_lats)}
                        lod.append(thisDict)
                        """
                        filetimeList.append(thistime.datetime)
                        digitizerList.append(thisDigitizer)
                        if latdeg:
                            latitudeList.append(latdeg)
                        else:
                            latitudeList.append(0.0)
                        if londeg:
                            longitudeList.append(londeg)
                        else:
                            longitudeList.append(0.0)
                        if len(stationcodes)==1:
                            stationList.append(stationcodes[0])
                        else:
                            stationList.append('DUMM')
                        if all_lats:
                            latitudeList2.append(np.nanmedian(all_lats))
                            latitudeSTDList2.append(np.nanstd(all_lats))
                        else:
                            latitudeList2.append(0.0)
                            latitudeSTDList2.append(0.0) 
                        """
                        
            """   
            positionDF['Digitizer'] = digitizerList
            positionDF['DateTime'] = filetimeList
            positionDF['Station'] = stationList
            positionDF['Latitude'] = latitudeList
            positionDF['Longitude'] = longitudeList
            positionDF['Latitude2'] = latitudeList2
            positionDF['Latitude2std'] = latitudeSTDList2
            """
            if len(lod)>lastlenlod:
                positionDF = pd.DataFrame(lod)
                positionDF['DateTime'] = pd.to_datetime(positionDF['DateTime'])
                positionDF = positionDF.astype({'Digitizer': 'str', 'Station': 'str'})
                positionDF = positionDF.round(decimals=5)
                display(positionDF)
                positionDF.to_csv(summary1file, index=False)
                lastlenlod = len(lod)

    return summary1file, positionDF


def create_summary9file(SVCDIR, RAWDIR, positionDF):
    # Parse RT130 9/* files to reconstruct digitizer-station history
    summary9file = os.path.join(SVCDIR, 'summary9file.csv')
    lod = []
    
    STATIONS = ['BHP', 'TANK', 'FIRE', 'BCHH', 'DVEL', 'RBLAB']
    dayfullpaths = sorted(glob.glob('%s/20?????' % RAWDIR))
    if os.path.exists(summary9file):
        os.remove(summary9file)
    count = 0
    
    for thisdayfullpath in dayfullpaths:
        count = count + 1
        print('Processing %s (%d of %d)' % (thisdayfullpath, count, len(dayfullpaths) ))#, end="\r", flush=True)
        thisdaydir = os.path.basename(thisdayfullpath) # a directory like 2018365
        rt130files = sorted(glob.glob('%s/????/9/*' % thisdayfullpath))
        
        if rt130files:
            
            for rt130file in rt130files:
                output = os.popen('strings %s' % rt130file).read()
                if output: 
                    for station in STATIONS:
                        firstindex = output.find(station)
                        if firstindex > -1:
                            break
                        
                    if firstindex != -1:
                        pathparts = rt130file.split('/')
                        rt130 = pathparts[-3]
                        lod.append({'Digitizer':rt130, 'yyyyjjj':thisdaydir, 'Station':output[firstindex:firstindex+4].strip()})

    if lod:
        stationDF = pd.DataFrame(lod)
        stationDF = stationDF.astype({'Digitizer': 'str', 'yyyyjjj': 'str'})
        combinedDF = pd.merge(positionDF, stationDF, on=['Digitizer', 'yyyyjjj'], how="left")
        combinedDF.to_csv(summary9file, index=False)
        return summary9file, combinedDF
    else:
        return '', pd.DataFrame()

def commandExists(command):
    # commandExists checks if PASSOFT/DMC commands are installed before we try to use them
    output = os.popen('which %s' % command).read()
    if output:
        return True
    else:
        print('Command %s not found.' % command)
        print('Make sure the PASSOFT tools are installed on this computer, and available on the $PATH')
        return False

def getpaths(SVCDIR):
    paths={}
    paths['RAWDIR'] = os.path.join(SVCDIR, 'RAW') 
    paths['LOGSDIR'] =  os.path.join(SVCDIR, 'LOGS')
    paths['CONFIGDIR'] = os.path.join(SVCDIR, 'CONFIG')
    paths['MSEEDDIR'] = os.path.join(SVCDIR, 'MSEED')
    paths['DAYSDIR'] = os.path.join(SVCDIR, 'DAYS')   
    return paths

def dirsmake(topdir, dirlist):
    print(topdir, dirlist)
    if not os.path.isdir(topdir):
        try:
            print(f'Attempting to make {topdir}')
            os.makedirs(topdir)
        except:
            print("%s does not exist. Exiting" % topdir)
            raise SystemExit("Killed!") 

    for thissubdir in dirlist:
        if not os.path.exists(thissubdir):
            print('Need to make %s' % thissubdir)
            os.mkdir(thissubdir)
            if not os.path.isdir(thissubdir):
                print("%s does not exist & could not be created. Exiting" % thissubdir)
                raise SystemExit("Killed!")         

def getAllDigitizers(rawdir):
    allDigitizers = []
    yyyyjjjdirs = glob.glob(os.path.join(rawdir, '20?????'))
    for yyyyjjjdir in yyyyjjjdirs:
        dataloggerdirs = glob.glob(os.path.join(yyyyjjjdir, '????'))
        for dataloggerdir in dataloggerdirs:
            if os.path.isdir(dataloggerdir):
                allDigitizers.append(os.path.basename(dataloggerdir))
    allDigitizers = sorted(list(set(allDigitizers)))
    return allDigitizers

def createCFdirs(paths, newpaths, allDigitizers):
    for datalogger in allDigitizers:
        dayfullpaths = sorted(glob.glob('%s/20?????' % paths['RAWDIR']))
        CFDIR = os.path.join(newpaths['RAWDIR'], f'RT130-{datalogger}-1.cf')
        if not os.path.isdir(CFDIR):
            os.makedirs(CFDIR)
        
        for thisdayfullpath in dayfullpaths:
            print('Processing %s' % thisdayfullpath)
            thisdaydir = os.path.basename(thisdayfullpath) # a directory like 2018365
            dataloggerdir = os.path.join(thisdayfullpath, datalogger)
            outputdir = os.path.join(CFDIR, thisdaydir)
            print(dataloggerdir, '\t->\t',outputdir)
            if os.path.isdir(dataloggerdir):
                if not os.path.isdir(outputdir):
                    os.makedirs(outputdir)
                
                os.system(f"cp -rn {dataloggerdir} {outputdir}") 
