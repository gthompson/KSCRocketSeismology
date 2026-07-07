# Library for converting Well data from CS to pickle files & MiniSEED
import numpy as np
from obspy import UTCDateTime, Stream, Trace
import os
import pandas as pd
import glob



# Define phase 2 lookup table & conversions
# From "2022-12-03_ Field Sheet for Deployment of Groundwater Equipment at NASA_Part_II.pdf" 
def get_transducers_dataframe(paths, keep=False):
    if os.path.isfile(paths['transducersCSVfile']) and keep==True:
        transducersDF = pd.read_csv(paths['transducersCSVfile'])
    else:
        
        phase2_startdate = UTCDateTime(2022,7,21,14,7,0)
        transducers = []

        # 20250107: adding tmean values determined from 04_compare_barometers. Depth dependent average temperatures

        # Shallow well (HOF-IW0006S)
        transducer1 = {'serial':'AirPressureShallow', 'Fs':100, 'sensor':'barometer','shielding':'none',
               'range_kPa_low':100,'range_kPa_high':100,'media':'air', 'type':'pressure', 
               'model':'Keller 0507.01401.051311.07','set_depth_ft':3.81, 'id':'6S.02374.88.HDH', 'well':'shallow', 'tmean':None
              } # serial 237488
        transducers.append(transducer1)
        transducer2 = {'serial':'1226420', 'Fs':100, 'sensor':'vibrating_wire','shielding':'none',
               'range_kPa_low':70,'range_kPa_high':170,'media':'air', 'type':'level', 
               'model':'Geokon 4500AL','set_depth_ft':4.46,
               'dig0':9751, 'gf':-0.006458, 'tt':21.6, 'tt0':21.3, 'tf':-0.008795, 
               'bp':14.504, 'bp0':14.298, 'id':'6S.12264.20.HDD', 'well':'shallow', 'tmean':30.68
              }
        transducers.append(transducer2)
        transducer3 = {'serial':'1226423', 'Fs':20, 'sensor':'vibrating_wire','shielding':'foam',
               'range_kPa_low':70,'range_kPa_high':170,'media':'water', 'type':'level', 
               'model':'Geokon 4500AL','set_depth_ft':-5.83,
               'dig0':9605, 'gf':-0.006347, 'tt':21.6, 'tt0':22.2, 'tf':-0.004197, 
               'bp':14.504, 'bp0':14.298, 'id':'6S.12264.23.BDD','well':'shallow', 'tmean':28.40
              }
        transducers.append(transducer3)
        transducer4 = {'serial':'1226419', 'Fs':100, 'sensor':'vibrating_wire','shielding':'foam',
               'range_kPa_low':70,'range_kPa_high':170,'media':'water', 'type':'level', 
               'model':'Geokon 4500AL','set_depth_ft':-6.71,
               'dig0':10040, 'gf':-0.006441, 'tt':21.6, 'tt0':21.1, 'tf':-0.010870, 
               'bp':14.504, 'bp0':14.298, 'id':'6S.12264.19.HDD','well':'shallow', 'tmean':27.57
              }
        transducers.append(transducer4)
        transducer5 = {'serial':'1226421', 'Fs':100, 'sensor':'vibrating_wire','shielding':'none',
               'range_kPa_low':70,'range_kPa_high':170,'media':'water', 'type':'level', 
               'model':'Geokon 4500AL','set_depth_ft':-7.71,
               'dig0':9787, 'gf':-0.006724, 'tt':21.6, 'tt0':21.3, 'tf':-0.001145, 
               'bp':14.504, 'bp0':14.298, 'id':'6S.12264.21.HDD','well':'shallow', 'tmean':27.60          
               }
        transducers.append(transducer5)

        # Intermediate well (HOF-IW00061)
        transducer6 = {'serial':'AirPressureIntermediate', 'Fs':100, 'sensor':'barometer','shielding':'none',
               'range_kPa_low':100,'range_kPa_high':100,'media':'air', 'type':'pressure', 
               'model':'Keller 0507.01401.051311.07','set_depth_ft':3.86, 'id':'6I.0XXXX.XX.HDH', 'well':'intermediate', 'tmean':None
              }
        transducers.append(transducer6)
        transducer7 = {'serial':'1226429', 'Fs':100, 'sensor':'vibrating_wire','shielding':'none',
               'range_kPa_low':70,'range_kPa_high':170,'media':'air', 'type':'level', 
               'model':'Geokon 4500AL','set_depth_ft':4.11,
               'dig0':9800, 'gf':-0.006428, 'tt':22.6, 'tt0':21.6, 'tf':-0.002384, 
               'bp':14.367, 'bp0':14.298, 'id':'6I.12264.29.HDD','well':'intermediate', 'tmean':30.60         
              }
        transducers.append(transducer7)
        transducer8 = {'serial':'2151692', 'Fs':20, 'sensor':'vibrating_wire','shielding':'foam',
               'range_kPa_low':70,'range_kPa_high':170,'media':'water', 'type':'level', 
               'model':'Geokon 4500AL','set_depth_ft':-9.14,
               'dig0':9459, 'gf':-0.008038, 'tt':22.8, 'tt0':21.8, 'tf':0.007666, 
               'bp':14.296, 'bp0':14.388, 'id':'6I.21516.92.BDD','well':'intermediate', 'tmean':25.88
              }
        transducers.append(transducer8)
        transducer9 = {'serial':'2151691', 'Fs':100, 'sensor':'vibrating_wire','shielding':'foam',
               'range_kPa_low':70,'range_kPa_high':170,'media':'water', 'type':'level', 
               'model':'Geokon 4500AL','set_depth_ft':-18.31,
               'dig0':9414, 'gf':-0.008142, 'tt':22.8, 'tt0':21.5, 'tf':0.008742, 
               'bp':14.296, 'bp0':14.388, 'id':'6I.21516.91.HDD','well':'intermediate', 'tmean':25.70
              }
        transducers.append(transducer9)
        transducer10 = {'serial':'2149882', 'Fs':100, 'sensor':'vibrating_wire','shielding':'none',
               'range_kPa_low':70,'range_kPa_high':170,'media':'water', 'type':'level', 
               'model':'Geokon 4500AL','set_depth_ft':-19.14,
               'dig0':9734, 'gf':-0.008075, 'tt':20.7, 'tt0':21.3, 'tf':0.0006752, 
               'bp':14.602, 'bp0':14.389, 'id':'6I.21498.82.HDD','well':'intermediate', 'tmean':25.96
               }
        transducers.append(transducer10)
        transducersDF = pd.DataFrame(transducers)
        transducersDF.to_csv(paths['transducersCSVfile'])
    return transducersDF

def list_cs_files(TOPDIR, ext='.csv'):
    import glob
    files = []
    uploaddirs = sorted(glob.glob(os.path.join(TOPDIR, '20??????')))
    for uploaddir in uploaddirs:
        #print(uploaddir)
        files_100Hz = sorted(glob.glob(os.path.join(uploaddir, '100hz/*%s' % ext)))
        #print(len(files_100Hz))
        files.extend(files_100Hz)
        files_baro = sorted(glob.glob(os.path.join(uploaddir,  'Baro/*%s' % ext)))
        #print(len(files_baro))
        files.extend(files_baro)
        files_20Hz = sorted(glob.glob(os.path.join(uploaddir,  '20hz/*%s' % ext)))
        #print(len(files_20Hz))
        files.extend(files_20Hz)
    return files    

# Generate complete list of TOB3 files (raw TOB3 files from CS dataloggers)
def list_loggernet_tob3_files(TOB3_DIR):
    return list_cs_files(TOB3_DIR, ext='.dat')

# Generate complete list of LoggerNet CSV files (converted from TOB3 files with LoggerNet)
def list_loggernet_csv_files(CSVDIR, ext='.csv'):
    return  list_cs_files(CSVDIR, ext=ext)


def cast_dataframe(dfcsv):
    dfcsv['TIMESTAMP'] = pd.to_datetime(dfcsv.TIMESTAMP)
    dfcsv['RECORD'] = dfcsv['RECORD'].astype(int)
    for col in dfcsv.columns[2:]:
        dfcsv[col] = dfcsv[col].astype(float)
    #return dfcsv

def read_LoggerNet_csv(csvfile):
    dfcsv = pd.read_csv(csvfile, 
                #dtype={'TOA5':str, '100hz_Sensors':int, 'CR6':float, '18084':float, 
                #        'CR6.Std.12.01':float, 'CPU:VWIRE305_100hz.CR6':float, '20853':float, 'DynamicFreq':float}, 
                parse_dates=['TOA5'])
    dfcsv.columns = dfcsv.iloc[0]
    dfcsv=dfcsv.iloc[3:]
    cast_dataframe(dfcsv)
    return dfcsv

def measureClockDrift(df): 
    passed = True
    starttime=df.iloc[0]['TIMESTAMP']
    endtime=df.iloc[-1]['TIMESTAMP']
    timediff = (endtime - starttime)
    nrows=len(df.index)
    numValidTimes = nrows
    secs = np.array([x.timestamp() for x in df['TIMESTAMP']])
    recs = df['RECORD'].to_numpy().astype('int')
    recsdiff = recs[1:-1]-recs[0:-2]
    #print(recsdiff)
    secsdiff = secs[1:-1]-secs[0:-2]   
    print(secsdiff)
    sample_interval = np.nanmedian(secsdiff)
    gps_records = []
    for i in range(0,len(secsdiff)):
        thisdiff = secsdiff[i]
        if thisdiff >= sample_interval*(recsdiff[i]+0.5) or thisdiff <= sample_interval*(recsdiff[i]-0.5):
            # recsdiff suggests consecutive samples, but thisdiff suggests a strange jump in sample time
            # we assume the GPS clock jumped in and reset. these are the times we save for interpolation
            gps_records.append(df.iloc[i]['RECORD'])
            gps_records.append(df.iloc[i+1]['RECORD'])
            try: # this might not always exist if at end of file
                gps_records.append(df.iloc[i+2]['RECORD']) 
            except:
                pass
    df2 = df[df['RECORD'].isin(gps_records)]    
    print('GPS timed samples')
    print(df2)
    return df2
    #input('Press ENTER to continue')


def compute_psi(dig, d):
    psi = np.zeros((len(dig),1))
    #if np.isnan(d['dig0']):
    #    return psi
    for i in range(len(dig)):
        psi[i] = ((dig[i]-d['dig0']) * d['gf'] + (d['tt']-d['tt0'])*d['tf']+(d['bp0']-d['bp']))
        
    #print(level)
    return psi

def reverse_compute_psi(psi, d):
    # inverse function of compute_psi
    digits = (psi - (d['tt'] - d['tt0']) * d['tf'] + (d['bp'] -  d['bp0'])) / d['gf'] + d['dig0']
    return digits

def uncalibrate_to_raw(transducersDF, df, outfile):
    print('- Reverse calibration equations')
    for col in df.columns:
        if col[0:2]=='12' or col[0:2]=='21':
            print(f'Converting column {col}')
            this_transducer = transducersDF[(transducersDF['serial']) == col]
            #print(this_transducer)
            if len(this_transducer.index)==1:
                this_transducer = this_transducer.iloc[0].to_dict()
                #print(this_transducer)
                print('Calling reverse_compute_psi')
                df[col] = reverse_compute_psi(df[col].to_numpy(), this_transducer)
            else:
                print('length not 1')
        else:
            print(f'column {col} not scheduled for conversion')
    print('- writing reverse corrected data to %s' % outfile)
    print(df.head())
    if outfile.endswith('.csv'):
        df.to_csv(outfile, index=False)
    elif outfile.endswith('.pkl'):
        df.to_pickle(outfile)
    print('\n\n\n')

def psi2pascals(psi):
    return psi * 6894.76

def psi2feet(psi):
    return 2.31 * psi

def psi2inches(psi):
    return 2.31 * psi * 12

def feet2meters(ft):
    return 0.3048 * ft

def localtime2utc(this_dt, hours): # call with hours=4. # kelly says time was always 4 hours behind UTC. no hour change on 11/6
    if not hours:
        hours = 4
        if this_dt>UTCDateTime(2022,11,6,2,0,0): 
            hours = 5
    localTimeCorrection = 3600 * hours
    return this_dt + localTimeCorrection
   
'''
def convert2units(st, transducersDF):
    for tr in st:
        if tr.stats.network=='FL':
            continue
        try:
            this_transducer = transducersDF[(transducersDF['id']) == tr.id] # not working
        except:
            for i,rows in transducersDF.iterrows():
                if row['id'] == tr.id:
                    this_transducer = row
        if this_transducer['type']=='level':
            tr.data = psi2depthmetres(tr.data)
        elif this_transducer['type']=='pressure':
            tr.data = psi2pascals(tr.data)
'''            
def correct_csvfiles(csvfiles, paths, converted_by_LoggerNet=True, MAXFILES=None, keep_existing=True):
    
    if not MAXFILES or MAXFILES>len(csvfiles):
        MAXFILES = len(csvfiles)
    
    transducersDF = get_transducers_dataframe(paths)

    lod = []
    for filenum, rawcsvfile in enumerate(csvfiles[0:MAXFILES]):
        csvbase = os.path.basename(rawcsvfile)
        print('File %d of %d: %s' % ((filenum+1), MAXFILES, csvbase))

        dirname = os.path.basename(os.path.dirname(rawcsvfile))
        uploaddir = os.path.basename(os.path.dirname(os.path.dirname(rawcsvfile)))
        correctedcsvfile = os.path.join("%s.%s.%s" % (os.path.basename(uploaddir), dirname, csvbase))
        if os.path.isfile(correctedcsvfile) & keep_existing:
            print('- Already DONE')
            df2 = pd.read_csv(correctedcsvfile)
            if converted_by_LoggerNet:
                cast_dataframe(df2) # probably not needed for .py_csv files & might even crash
        else:
            print('- Reading')
            try:
                if converted_by_LoggerNet:
                    df2 = read_LoggerNet_csv(rawcsvfile) # definitely not needed for .py_csv files
                else:
                    df2 = pd.read_csv(rawcsvfile)
            except:
                print('Failed to read %s' % rawcsvfile)
                os.rename(rawcsvfile, rawcsvfile + '.bad')
                continue

            print('- Applying calibration equations')
            for col in df2.columns:
                #print(col)
                if isinstance(col,str) and (col[0:2]=='12' or col[0:2]=='21'):
                    this_transducer = transducersDF[(transducersDF['serial']) == col]
                    #print(this_transducer)
                    if len(this_transducer.index)==1:
                        this_transducer = this_transducer.iloc[0].to_dict()
                        #print(this_transducer)
                        df2[col] = compute_psi(df2[col].to_numpy(), this_transducer)
            print('- writing corrected data to %s' % correctedcsvfile)       
            df2.to_csv(correctedcsvfile)

        # check start & end time 
        passed = True
        starttime=df2.iloc[0]['TIMESTAMP']
        endtime=df2.iloc[-1]['TIMESTAMP']
        timediff = (endtime - starttime)
        nrows=len(df2.index)
        numValidTimes = nrows
        secs = np.array([x.timestamp() for x in df2['TIMESTAMP']])
        secsdiff = secs[1:-1]-secs[0:-2]
        sample_interval = np.nanmedian(secsdiff)
        #sample_interval2 = timediff.seconds/(nrows-1)  
        if timediff.seconds>4*60*60: # files should be no more than 4 hours # SCAFFOLD: SHOULD MARK THESE FILES
            print('Problem likely with start time. Filter out all data more than 4 hours before end')
            df2 = df2[df2['TIMESTAMP']>endtime-pd.to_timedelta(4, unit='h')]
            df2 = df2[df2['TIMESTAMP']<=endtime]
            numValidTimes = len(df2.index)
            passed = False

        # check clock drift - this is what all the GPS CSV files are for
        if converted_by_LoggerNet:
            gpscsv = correctedcsvfile.replace('.csv','_gps.csv')
        else:
            gpscsv = correctedcsvfile.replace('.py_csv','_gps.py_csv')
        if not os.path.isfile(gpscsv):
            gpsdf = measureClockDrift(df2)
            if not gpsdf.empty:
                # write out
                gpsdf.to_csv(gpscsv, index=False)
                passed = False
        else:
            gpsdf = pd.read_csv(gpscsv)

        print('- DONE\n')
        
        # Constructing row of lookup table
        thisd = {}
        sourcefileparts = csvfile.split('\\')
        sourcefilerelpath = os.path.join(sourcefileparts[-3],sourcefileparts[-2],sourcefileparts[-1])
        thisd['sourcefile']=sourcefilerelpath
        thisd['outputfile']=convertedcsvfile
        thisd['starttime']=starttime.strftime('%Y/%m/%d %H:%M:%S')
        thisd['endtime']=endtime.strftime('%Y/%m/%d %H:%M:%S')
        thisd['hours']=np.round(timediff.seconds/3600.0,2)
        thisd['npts']=nrows
        thisd['nRECS']=df2.iloc[-1]['RECORD']-df2.iloc[0]['RECORD']+1
        thisd['Fs']=1/sample_interval
        if thisd['nRECS']!=nrows:
            passed=False
        if numValidTimes<nrows:
            passed=False
        thisd['numValidTimes']=numValidTimes
        thisd['numTimeSkips']=len(gpsdf.index)/3
        thisd['passed']=passed
        lod.append(thisd)
        lookuptableDF = pd.DataFrame(lod)
        #print(lookuptableDF)
        #if passed:
        #    print('- writing to SDS')
        #    convert2sds(df2, SDS_TOP)

    lookuptableDF.to_csv(paths['lookuptable'], index=False)   


def removed_unnamed_columns(df):
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    return df

def convert2sds(df, sdsobj, transducersDF, dryrun=False): # I think df here is supposed to be from a single picklefile
    #print('***')
    #print(df.columns)  
    #print('***')  
    local_startt = UTCDateTime(df.iloc[0]['TIMESTAMP'])
    nextt = UTCDateTime(df.iloc[1]['TIMESTAMP'])
    dt = nextt-local_startt
    utc_startt = localtime2utc(local_startt, hours=4)
    if utc_startt > UTCDateTime():
        return
    print('local ', local_startt, '-> UTC ', utc_startt)
    st = Stream()    
    #print('***')
    #print(df.columns)    
    for col in df.columns[2:]:
        #print('Processing column %s' % col)
        this_transducer = transducersDF[(transducersDF['serial']) == col]
        #print('***')
        #print(this_transducer)
        #print('***')
        if len(this_transducer.index)==1:
            this_transducer = this_transducer.iloc[0].to_dict()
            tr = Trace()
            tr.id = this_transducer['id']
            tr.stats.starttime = utc_startt
            tr.stats.delta = dt  
            tr.data = np.array(df[col])           
            print(f"sampling rate = {tr.stats.sampling_rate}")
            if int(tr.stats.sampling_rate)==20:
                if tr.stats.channel[0]=='H':
                    tr.stats.channel="B%s" % tr.stats.channel[1:]
            if int(tr.stats.sampling_rate)==1:
                if tr.stats.channel[0]=='H' or tr.stats.channel[0]=='B':
                    tr.stats.channel="L%s" % tr.stats.channel[1:]
            #print(tr)
            st.append(tr)
    print('Final Stream object to write')
    print(st)
    if dryrun:
        return False
    else:
        sdsobj.stream = st
        successful = sdsobj.write()
        if successful:
            print("Wrote whole Stream object to SDS")
        else: 
            print("Failed to write entire Stream object:")
            print(df)
        return successful

def remove_overlaps(a):
    c = np.where(np.diff(a) <= 0)[0]
    bad_i = []
    for d in c:
        bool_i = a[0:d] >= a[d+1]
        new_bad_i = list(np.where(bool_i)[0] ) 
        new_bad_i.append(d)
        bad_i = bad_i + new_bad_i
    return list(set(bad_i))


def convert2sds_badfile(df, sdsobj, transducersDF, dryrun=False): # I think df here is supposed to be from a single picklefile
    # NEED TO MODIFY THIS TO DEAL WITH TIME SKIPS
    # No time skip should be more than half a sample.
    # Backward slips are harder to deal with, since time will overlap. Overwrite previous samples when that happens.

    if dryrun:
        mseeddirname = os.path.join(sdsobj.topdir, 'well_mseed')
        if not os.path.isdir(mseeddirname):
            os.makedirs(mseeddirname)

    print('df original length: ', len(df))

    # get rid of anything not within 4 hours of last row
    d = pd.to_datetime(df['TIMESTAMP'])
    df2 = df[ d > d[d.size-1]-pd.Timedelta(hours=4) ]
    #good_i = [i for i in range(len(df2))]
    print('df2 original length: ', len(df2))
    
    # find correct dt using mode
    t = np.array( [UTCDateTime(df2.iloc[i]['TIMESTAMP']).timestamp for i in range(len(df2)) ])
    dt_array = np.diff(t)
    dt = np.median(dt_array)
    #dt_series = pd.Series(dt_array)
    #print(dt_series.describe())
    #dt = dt_series.mode()[0]

    # maybe we only care about times where t slipped backwards?
    # if it goes forward, do we care?
    # do we insert interpolate onto regular sampling?
    # so just generate a list of -ve diffs
    # then process each of those to discover overlaps

    # Now we have expected dt, we need to check ...
    #good_i = range(len(dt_list)+1) # last row always assumed good
    bad_i = remove_overlaps(t)     
    print('bad_i length: ', len(bad_i))
    df2 = df2.drop(df2.index[bad_i]) 
    print('df2 new length: ', len(df2))
    del t

    # now all times should be ascending. Resample.#
    if dt > 0.0099 and dt < 0.0101:
        resampleStr = '10ms'
    elif dt > 0.0499 and dt < 0.0501:
        resampleStr = '50ms'
    elif dt > 0.999 and dt < 1.001:
        resampleStr = '1s'
    else:
        print('delta_t not recognized: ', dt)
        

    df2['datetime'] = pd.to_datetime(df2['TIMESTAMP']) 
    df2.set_index('datetime', inplace=True)

 
    df2_resamp = df2.resample(resampleStr).asfreq()
    df2_resamp.reset_index(drop=True) # datetime index gone

    local_startt = UTCDateTime(df2_resamp.iloc[0]['TIMESTAMP'])
    utc_startt = localtime2utc(local_startt, hours=4)
    if utc_startt > UTCDateTime():
        return
    print('local ', local_startt, '-> UTC ', utc_startt) 
            
    st = Stream()      
    for col in df2_resamp.columns[2:]:
        #print('Processing column %s' % col)
        this_transducer = transducersDF[(transducersDF['serial']) == col]
        #print('***')
        #print(this_transducer)
        #print('***')
        if len(this_transducer.index)==1:
            this_transducer = this_transducer.iloc[0].to_dict()
            tr = Trace()
            tr.id = this_transducer['id']
            tr.stats.starttime = utc_startt
            tr.stats.delta = dt  
            tr.data = np.array(df[col])           
            #print(f"sampling rate = {tr.stats.sampling_rate}")
            if int(tr.stats.sampling_rate)==20:
                if tr.stats.channel[0]=='H':
                    tr.stats.channel="B%s" % tr.stats.channel[1:]
            if int(tr.stats.sampling_rate)==1:
                if tr.stats.channel[0]=='H' or tr.stats.channel[0]=='B':
                    tr.stats.channel="L%s" % tr.stats.channel[1:]
            #print(tr)
            st.append(tr)
    print('Final Stream object to write')
    print(st)
    
    if dryrun:
        print('dryrun')
        for tr in st:
            mseedfilename = os.path.join(mseeddirname, '%s.%s.%s.ms' % (tr.id, tr.stats.starttime.strftime('%Y%m%d_%H%M%S'), tr.stats.endtime.strftime('%H%M%S') ) )
            print('SCAFFOLD: writing ',mseedfilename)
            tr.write(mseedfilename, format='MSEED') #, encoding=5)
        return True
    else:
        sdsobj.stream = st
        successful = sdsobj.write()
        if successful:
            print("Wrote whole Stream object to SDS")
        else: 
            print("Failed to write entire Stream object:")
            print(df)
        return successful
    

def convert2mseed(df, MSEED_DIR, transducersDF): # I think df here is supposed to be from a single picklefile
    #print('***')
    #print(df.columns)  
    #print('***')
    mseeddirname = os.path.join(MSEED_DIR, 'good')
    if not os.path.isdir(mseeddirname):
        os.makedirs(mseeddirname)  
    local_startt = UTCDateTime(df.iloc[0]['TIMESTAMP'])
    nextt = UTCDateTime(df.iloc[1]['TIMESTAMP'])
    dt = nextt-local_startt
    utc_startt = localtime2utc(local_startt, hours=4)
    if utc_startt > UTCDateTime():
        return
    print('local ', local_startt, '-> UTC ', utc_startt)
    st = Stream()    
    #print('***')
    #print(df.columns)    
    for col in df.columns[2:]:
        #print('Processing column %s' % col)
        this_transducer = transducersDF[(transducersDF['serial']) == col]
        #print('***')
        #print(this_transducer)
        #print('***')
        if len(this_transducer.index)==1:
            this_transducer = this_transducer.iloc[0].to_dict()
            tr = Trace()
            tr.id = this_transducer['id']
            tr.stats.starttime = utc_startt
            tr.stats.delta = dt  
            tr.data = np.array(df[col])           
            print(f"sampling rate = {tr.stats.sampling_rate}")
            if int(tr.stats.sampling_rate)==20:
                if tr.stats.channel[0]=='H':
                    tr.stats.channel="B%s" % tr.stats.channel[1:]
            if int(tr.stats.sampling_rate)==1:
                if tr.stats.channel[0]=='H' or tr.stats.channel[0]=='B':
                    tr.stats.channel="L%s" % tr.stats.channel[1:]
            #print(tr)
            st.append(tr)
    print('Final Stream object to write')
    print(st)
    
    return stream2miniseed(st, mseeddirname)

def remove_overlaps(a):
    c = np.where(np.diff(a) <= 0)[0]
    bad_i = []
    for d in c:
        bool_i = a[0:d] >= a[d+1]
        new_bad_i = list(np.where(bool_i)[0] ) 
        new_bad_i.append(d)
        bad_i = bad_i + new_bad_i
    return list(set(bad_i))


def convert2mseed_badfile(df, MSEED_DIR, transducersDF): # I think df here is supposed to be from a single picklefile
    # NEED TO MODIFY THIS TO DEAL WITH TIME SKIPS
    # No time skip should be more than half a sample.
    # Backward slips are harder to deal with, since time will overlap. Overwrite previous samples when that happens.

    mseeddirname = os.path.join(MSEED_DIR, 'bad')
    if not os.path.isdir(mseeddirname):
        os.makedirs(mseeddirname)

    print('df original length: ', len(df))

    # get rid of anything not within 4 hours of last row
    d = pd.to_datetime(df['TIMESTAMP'])
    df2 = df[ d > d[d.size-1]-pd.Timedelta(hours=4) ]
    #good_i = [i for i in range(len(df2))]
    print('df2 original length: ', len(df2))
    
    # find correct dt using mode
    t = np.array( [UTCDateTime(df2.iloc[i]['TIMESTAMP']).timestamp for i in range(len(df2)) ])
    dt_array = np.diff(t)
    dt = np.median(dt_array)
    #dt_series = pd.Series(dt_array)
    #print(dt_series.describe())
    #dt = dt_series.mode()[0]

    # maybe we only care about times where t slipped backwards?
    # if it goes forward, do we care?
    # do we insert interpolate onto regular sampling?
    # so just generate a list of -ve diffs
    # then process each of those to discover overlaps

    # Now we have expected dt, we need to check ...
    #good_i = range(len(dt_list)+1) # last row always assumed good
    bad_i = remove_overlaps(t)     
    print('bad_i length: ', len(bad_i))
    df2 = df2.drop(df2.index[bad_i]) 
    print('df2 new length: ', len(df2))
    del t

    # now all times should be ascending. Resample.#
    if dt > 0.0099 and dt < 0.0101:
        resampleStr = '10ms'
    elif dt > 0.0499 and dt < 0.0501:
        resampleStr = '50ms'
    elif dt > 0.999 and dt < 1.001:
        resampleStr = '1s'
    else:
        print('delta_t not recognized: ', dt)
        

    df2['datetime'] = pd.to_datetime(df2['TIMESTAMP']) 
    df2.set_index('datetime', inplace=True)

 
    df2_resamp = df2.resample(resampleStr).asfreq()
    df2_resamp.reset_index(drop=True) # datetime index gone

    local_startt = UTCDateTime(df2_resamp.iloc[0]['TIMESTAMP'])
    utc_startt = localtime2utc(local_startt, hours=4)
    if utc_startt > UTCDateTime():
        return
    print('local ', local_startt, '-> UTC ', utc_startt) 
            
    st = Stream()      
    for col in df2_resamp.columns[2:]:
        #print('Processing column %s' % col)
        this_transducer = transducersDF[(transducersDF['serial']) == col]
        #print('***')
        #print(this_transducer)
        #print('***')
        if len(this_transducer.index)==1:
            this_transducer = this_transducer.iloc[0].to_dict()
            tr = Trace()
            tr.id = this_transducer['id']
            tr.stats.starttime = utc_startt
            tr.stats.delta = dt  
            tr.data = np.array(df[col])           
            #print(f"sampling rate = {tr.stats.sampling_rate}")
            if int(tr.stats.sampling_rate)==20:
                if tr.stats.channel[0]=='H':
                    tr.stats.channel="B%s" % tr.stats.channel[1:]
            if int(tr.stats.sampling_rate)==1:
                if tr.stats.channel[0]=='H' or tr.stats.channel[0]=='B':
                    tr.stats.channel="L%s" % tr.stats.channel[1:]
            #print(tr)
            st.append(tr)
    print('Final Stream object to write')
    print(st)
    return stream2miniseed(st, mseeddirname)

def stream2miniseed(st, mseeddirname):
    successful = True
    for tr in st:
        mseedfilename = os.path.join(mseeddirname, '%s.%s.%s.ms' % (tr.id, tr.stats.starttime.strftime('%Y%m%d_%H%M%S'), tr.stats.endtime.strftime('%Y%m%d_%H%M%S') ) )
        if os.path.isfile(mseedfilename):
            continue
        print('SCAFFOLD: writing ',mseedfilename)
        try:
            tr.write(mseedfilename, format='MSEED') #, encoding=5)
        except:
            successful = False	
    return successful


##### From 2nd workflow - no SDS for well data. from 50_segment_event_files

# How we plot low res well data (1 minute). First method recomputes 60-s data. Second method loads precomputed 60-s data.
 
def plot_low_resolution_well_data(event_udt, assoc_udt, duration=600, pretrig=3600, posttrig=3600, new_interval=1):
    start_udt = assoc_udt - pretrig
    end_udt = assoc_udt + duration + posttrig

    # correct from UTCDateTime requested to local time that well data is in
    start_dt = utc2localtime(start_udt, hours=4)
    end_dt = utc2localtime(end_udt, hours=4)
    
    instrumentsList = ['Baro', 'Sensors', 'Sensors', 'Sensors']
    fsList = [100, 1, 20, 100]
    for instrumentIndex, instruments in enumerate(instrumentsList):
        fs = fsList[instrumentIndex]
        timestring = event_udt.strftime('%Y%m%dT%H%M%S')
        pngpath = os.path.join(PNG_DIR, f'{timestring}_{instruments}_{fs}Hz_long.png')               
        if os.path.isfile(pngpath):
            print(pngpath, ' exists')
            continue
        try:
            st = load_data_from_daily_pickle_files(start_dt, end_dt, instruments=instruments, fs=fs, \
                                               to_stream=True, resample=True, new_interval=new_interval)
        except:
            st = None
        if st:
            print('writing ',pngpath)
            st.plot(equal_scale=False, outfile=pngpath);

def plot_60s_well_data(event_udt, assoc_udt, duration=600, pretrig=3600, posttrig=3600):
    MSEED_DIR = os.path.join(paths['CORRECTED'], 'daily60s')
    instrumentsList = ['Baro', 'Sensors', 'Sensors', 'Sensors']
    fsList = [100, 1, 20, 100]
    new_interval = 60
    
    start_udt = assoc_udt - pretrig
    end_udt = assoc_udt + duration + posttrig

    # correct from UTCDateTime requested to local time that well data is in
    start_dt = utc2localtime(start_udt, hours=4)
    end_dt = utc2localtime(end_udt, hours=4)
    
    for instrumentIndex, instruments in enumerate(instrumentsList):
        fs = fsList[instrumentIndex]
        st_all = obspy.Stream()
        print('\n**********\n',instruments,fs,'\n')
        
        timestring = event_udt.strftime('%Y%m%dT%H%M%S')
        pngpath = os.path.join(PNG_DIR, f'{timestring}_{instruments}_{fs}Hz_long.png')   
        if os.path.isfile(pngpath):
            print(pngpath, ' exists')
            continue

        this_dt = start_dt
        while this_dt < end_dt:
            that_dt = this_dt + datetime.timedelta(days=1)
            mseedfile = f"{this_dt.strftime('%Y%m%d')}_{instruments}_{fs}Hz_to_{new_interval}s.mseed"
            mseedpath = os.path.join(MSEED_DIR, mseedfile)
            if os.path.isfile(mseedpath):
                #print('Reading ',mseedpath)
                st = obspy.read(mseedpath)
                st_all = st_all + st
                st_all.merge()
                #print(st_all)
            else:
                #print(mseedpath,' not found')
                pass
            this_dt = that_dt
        if len(st_all)>0:
            st_all.trim(starttime=obspy.UTCDateTime(start_dt), endtime=obspy.UTCDateTime(end_dt))
            for tr in st_all:
                if isinstance(tr.data, np.ma.masked_array):
                    #tr.data = tr.data.filled(fill_value=np.nanmedian(tr.data))
                    tr.data = tr.data.filled(fill_value=np.nan)
            print(st_all)
            print('writing ',pngpath)
            st_all.plot(equal_scale=False, outfile=pngpath)

# This is how we load high-res well data (1 Hz, 20 Hz, 100 Hz)

def load_data_from_daily_pickle_files(start_dt, end_dt, instruments='Sensors', fs=100, resample=True, new_interval=None, max_samples=1000, \
                 average='median', to_stream=True, plot_data=True, print_dataframe=True):
    start_date = start_dt.date()
    end_date = end_dt.date()    
    
    delta = datetime.timedelta(days=1)
    this_date = start_date
    combineddf = pd.DataFrame()
    while this_date <= end_date:
        #print(this_date.strftime("%Y-%m-%d"))
        combined_pklfile = f"{this_date}_{instruments}_{fs}Hz.pkl"
        combined_pklpath = os.path.join(COMBINED_DIR, combined_pklfile)
        #print(combined_pklpath)
        if os.path.isfile(combined_pklpath):
            print('Loading ',combined_pklpath)
            if len(combineddf)>0:
                df = pd.read_pickle(combined_pklpath)
                if print_dataframe:
                    print(f'DataFrame from {combined_pklfile}')
                    print(df)
                    df.to_csv(combined_pklpath.replace('.pkl','.csv'))
                combineddf = pd.concat([combineddf, df])
            else:
                combineddf = pd.read_pickle(combined_pklpath)
                if print_dataframe:
                    print(f'DataFrame from {combined_pklfile}')
                    print(combineddf)
                    combineddf.to_csv(combined_pklpath.replace('.pkl','.csv'))
        else:
            print('file not found: ', combined_pklpath)
        this_date += delta


    if len(combineddf)==0:
        return None

    if not 'datetime'  in combineddf.columns:
        combineddf['datetime'] = [obspy.UTCDateTime(ts).datetime for ts in combineddf['TIMESTAMP']]

    # apply time subset
    mask = (combineddf['datetime'] >= start_dt) & (combineddf['datetime'] < end_dt)
    combineddf = combineddf.loc[mask]

    combineddf.set_index('datetime', inplace=True)
    combineddf.drop(columns=['TIMESTAMP', 'date', 'RECORD'], inplace=True)

    if resample or new_interval:
        if not new_interval:
            seconds = [1, 5, 10, 60, 300, 600, 900, 1800, 3600]
            seconds_index = 0
            estimated_delta = len(combineddf)/(max_samples * fs)
            
            while seconds[seconds_index] <= estimated_delta:
                seconds_index += 1
        
            new_interval = seconds[seconds_index] 
    
        print(f'resampling to {new_interval}-s sampling interval, taking median of each timewindow')
        if average=='median':
            combineddf = combineddf.resample(f"{new_interval}s").median()
        else:
            combineddf = combineddf.resample(f"{new_interval}s").mean()

        if len(combineddf)==0:
            return None
    
    #combineddf.reset_index(inplace=True)
    if to_stream:
        st = obspy.Stream()
        for col in combineddf.columns:
            tr = obspy.Trace(data=combineddf[col].to_numpy())
            tr.stats.starttime = obspy.UTCDateTime(combineddf.index[0])
            tr.stats.delta = obspy.UTCDateTime(combineddf.index[1]) - obspy.UTCDateTime(combineddf.index[0])
            tr.stats.network = col[0:2]
            if len(col)>7:
                tr.stats.station = col[2:7]
                if len(col)>9:
                    tr.stats.location = col[7:9]
                    tr.stats.channel = col[9:]
                else:
                    tr.stats.location = col[7:]
            else:
                tr.stats.station = col[2:]
            st.append(tr)
        if plot_data:
            st.plot(equal_scale=False);
        return st
    else:
        if plot_data:
            combineddf.plot(y=combineddf.columns)
        return combineddf



def utc2localtime(this_udt, hours=None):
    if not hours: # Kelly says was always 4 hours behind. Didn't change to 5 hours at Nov 6th.
        hours = 4
        if this_udt>obspy.UTCDateTime(2022,11,6,2,0,0):
            hours = 5
    localTimeCorrection = 3600 * hours
    this_dt = this_udt - localTimeCorrection
    return this_dt.datetime

def plot_high_resolution_well_data(event_udt, assoc_udt, duration=600, pretrig=150, posttrig=150, ext='short', overwrite=False, print_dataframe=False):
    start_udt = assoc_udt - pretrig
    end_udt = assoc_udt + duration + posttrig

    # correct from UTCDateTime requested to local time that well data is in
    start_dt = utc2localtime(start_udt, hours=4)
    end_dt = utc2localtime(end_udt, hours=4)
    
    instrumentsList = ['Baro', 'Sensors', 'Sensors', 'Sensors']
    fsList = [100, 1, 20, 100]
    for instrumentIndex, instruments in enumerate(instrumentsList):
        fs = fsList[instrumentIndex]
        timestring = event_udt.strftime('%Y%m%dT%H%M%S')
        pngpath = os.path.join(PNG_DIR, f'{timestring}_{instruments}_{fs}Hz_{ext}.png') 
        if os.path.isfile(pngpath) and not overwrite:
            print(pngpath, ' exists')
            continue
        try:
            st = load_data_from_daily_pickle_files(start_dt, end_dt, instruments=instruments, fs=fs, \
                                               to_stream=True, resample=False, print_dataframe=print_dataframe)
        except:
            st = None
            
        if st:
            print('writing ',pngpath)
            st.plot(equal_scale=False, outfile=pngpath);


# Next few functions relate to plotting sampling intervals different than expected

def plot_timediff_well_data(COMBINED_DIR, start_dt=None, end_dt=None):

    # correct from UTCDateTime requested to local time that well data is in
    if not start_dt:
        start_dt = UTCDateTime(2022,7,21)
    if not end_dt:
        end_dt = UTCDateTime(2022,12,3)
    
    instrumentsList = ['Sensors', 'Sensors', 'Sensors', 'Baro']
    fsList = [1, 20, 100, 100]

    for instrumentIndex, instruments in enumerate(instrumentsList):
        fs = fsList[instrumentIndex]

        csvfile = os.path.join(COMBINED_DIR, f"timedf_masked_{start_dt}_{end_dt}_{instruments}_{fs}Hz.csv")
        if os.path.isfile(csvfile):
            print(f'Reading {csvfile}')
            timedf_masked = pd.read_csv(csvfile)
            if '0' in timedf_masked.columns:
                timedf_masked.rename(columns={"0": "datetime"}, inplace=True)
        else:
            timedf_masked = load_timeonly_from_daily_pickle_files(start_dt, end_dt, COMBINED_DIR, instruments=instruments, fs=fs)
            timedf_masked.to_csv(csvfile)

        print(timedf_masked.columns)
        print(timedf_masked)
        if len(timedf_masked)>0:
            title=f"{instruments}_{fs}"
            plot_timediff(timedf_masked, title=title, outfile=csvfile.replace('.csv', '.png') )
            plot_timediff(timedf_masked, title=title+' zoomed', outfile=csvfile.replace('.csv', '_zoomed.png'), maxsecs=10.0 )

'''
def load_timeonly_from_daily_pickle_files(start_date, end_date, COMBINED_DIR, instruments='Sensors', fs=100, hours=4):
    # though similar to load_data_from_daily_picle_files, this function expects input local time dates that are UTCDateTime objects,
    # rather than datetime, and applies a 4 hour time shift by default, to correct from local to UTC.

    total_pklfile = f"{start_date}_{end_date}_{instruments}_{fs}Hz.pkl"
    total_pklpath = os.path.join(COMBINED_DIR, total_pklfile)
    success=False
    if os.path.isfile(total_pklpath):
        print(f'Loading {total_pklpath}')
        ts_series = pd.read_pickle(total_pklpath)
        print(ts_series)
        ts = ts_series.to_list()
        if len(ts)>0:

            success = True
    if success==False:
        this_date = start_date
        ts = []
        timedf_masked = pd.DataFrame()
        while this_date <= end_date:

            combined_pklfile = f"{this_date.strftime('%Y-%m-%d')}_{instruments}_{fs}Hz.pkl"
            combined_pklpath = os.path.join(COMBINED_DIR, combined_pklfile)

            if os.path.isfile(combined_pklpath):
                print('Loading ',combined_pklpath)
                
                if len(ts)>0:
                    df = pd.read_pickle(combined_pklpath)
                    ts.extend(df['TIMESTAMP'].to_list())

                else:
                    df = pd.read_pickle(combined_pklpath)
                    ts = df['TIMESTAMP'].to_list()
                    this_timedfmasked = timestamplist_to_timedataframeoutliers(ts, tolerance_pct=10)
                    timedf_masked = pd.concat([timedf_masked, this_timedfmasked])
            else:
                print('file not found: ', combined_pklpath)
            this_date += 86400

        ts_series = pd.Series(ts)
        ts_series.to_pickle(total_pklpath)
    
    if len(ts)==0:
        return None
'''
def load_timeonly_from_daily_pickle_files(start_date, end_date, COMBINED_DIR, instruments='Sensors', fs=100, hours=4):
    # though similar to load_data_from_daily_picle_files, this function expects input local time dates that are UTCDateTime objects,
    # rather than datetime, and applies a 4 hour time shift by default, to correct from local to UTC.


    this_date = start_date
    last_ts = None
    timedf_masked = pd.DataFrame()
    while this_date <= end_date:

        combined_pklfile = f"{this_date.strftime('%Y-%m-%d')}_{instruments}_{fs}Hz.pkl"
        combined_pklpath = os.path.join(COMBINED_DIR, combined_pklfile)

        if os.path.isfile(combined_pklpath):
            print('Loading ',combined_pklpath)
            df = pd.read_pickle(combined_pklpath)
            ts = df['TIMESTAMP'].to_list()
            if last_ts:
                ts.insert(0, last_ts)
            this_timedfmasked = timestamplist_to_timedataframeoutliers(ts, tolerance_pct=10)
            timedf_masked = pd.concat([timedf_masked, this_timedfmasked])
            last_ts = ts[-1]
        else:
            print('file not found: ', combined_pklpath)
        this_date += 86400

    timedf_masked
    print(timedf_masked)
    return timedf_masked

def timestamplist_to_timedataframe(ts):
    datetimeindex = pd.to_datetime(ts) #, format='%Y-%m-%d %H:%M:%S.%f')
    timedf = datetimeindex.to_frame()
    timedf['diff'] = datetimeindex.diff().total_seconds()
    timedf.rename(columns={"0": "datetime"})
    return timedf
    
def remove_good_sampling_intervals(timedf, tolerance_pct=10):
    tolerance_frac = (1.0+tolerance_pct/100)
    median_dt = timedf['diff'].median()
    max_dt = median_dt * tolerance_frac
    min_dt = median_dt / tolerance_frac
    mask = (timedf['diff'] > max_dt) | (timedf['diff'] < min_dt)
    timedf_masked = timedf[mask]
    return timedf_masked

def timestamplist_to_timedataframeoutliers(ts, tolerance_pct=10):
    timedf = timestamplist_to_timedataframe(ts)
    timedf_masked = remove_good_sampling_intervals(timedf, tolerance_pct=tolerance_pct)
    return timedf_masked

def plot_timediff(timedf_masked, title=None, outfile=None, ylim=None, maxsecs=None, xlim=None):
    #xlim=(timedf_masked.index[0], timedf_masked.index[-1])
    if maxsecs:
        mask = (timedf_masked['diff'] <= maxsecs) & (timedf_masked['diff'] >= -maxsecs)
        timedf_masked = timedf_masked[mask]
    ph = timedf_masked.plot(x='datetime', y='diff',  marker='.', linestyle='none', xlim=xlim, ylim=ylim, ylabel='Sampling interval (s)', title=title, rot=45)
    fh = ph.get_figure()
    if outfile:
        print(f'Saving plot to {outfile}')
        fh.savefig(outfile)
    else:
        fh.show()
    return fh, ph

##################################################
# FUNCTIONS FOR NEW WORKFLOW
##################################################


# set standard temperature and pressure
std_temperature = 20.0
std_passcals = 101325
pa2psi = 0.000145038
std_psi = std_passcals * pa2psi

# identify dataframe columns for transducers in air and water
aircolumns = ['AirPressureShallow', 'AirPressureIntermediate', '1226420', '1226429']
watercolumns = ['1226419', '1226421', '2151691', '2149882', '1226423', '2151692']
sensors = {'shallow':[watercolumns[i] for i in [0,1,4]], 'intermediate':[watercolumns[i] for i in [2,3,5]]}

def PaDiff1m(T=std_temperature):
    PaPerM = 12.67 - 0.041*T
    return PaPerM

def correctForHeightAboveWaterFt(heightFt=0, T=std_temperature):
    heightM = heightFt * 0.3048
    psi_shift = (PaDiff1m(T=T) * heightM) * pa2psi
    return psi_shift

def correctForDepthBelowWaterFt(depthFt=0, T=std_temperature):
    # correct up to 0m
    psi_shift = depthFt/2.31
    return psi_shift

def correctVibratingWireDigits(rawSeries, this_transducer, calibrationCorrect=True, temperatureSeries=None, airpressureSeries=None, depthCorrect=False):
    serialno = this_transducer['serial']
    # correct for gain
    if calibrationCorrect and rawSeries.mean()>8000:
        print(f'Applying calibration correction for {serialno}')
        cal = (rawSeries - this_transducer['dig0']) * this_transducer['gf']
        print(f'mean before: {rawSeries.mean()}, after: {cal.mean()}')
        print(f'min, max before: {rawSeries.min()}, {rawSeries.max()}')
        print(f'min, max after: {cal.min()}, {cal.max()}')
    else: # assume already calibrated
        cal = rawSeries
    tc = pd.Series()
    apc = pd.Series()
    psiShift = 0.0
    a = cal.copy()
    # correct for temperature
    if isinstance(temperatureSeries,pd.Series) or isinstance(temperatureSeries, float):
        print(f'Applying temperature correction for {serialno}')
        tc = (temperatureSeries - this_transducer['tt0']) * this_transducer['tf']
        #print('- temperature correction')
        #print(pd.Series(tc).describe())
        a += tc
    # correct for air pressure
    if isinstance(airpressureSeries,pd.Series) or isinstance(airpressureSeries,float):
        print(f'Applying air pressure correction for {serialno}')
        apc = (airpressureSeries - this_transducer['bp0'])
        #print('- air pressure correction')
        #print(pd.Series(apc).describe())
        a -= apc
    # correct for depth back to water surface
    if depthCorrect:
        print(f'Applying depth correction for {serialno}')
        psiShift = correctForDepthBelowWaterFt(depthFt=-this_transducer['set_depth_ft'])
        #print(f'- depth correction {psiShift}')
        a -= psiShift
    #print(f'T-correction={tc.mean()}, AP-correction={apc.mean()}, DCshift={-psiShift}')
    return cal, a   


def despike(df, cliplevel=0.5): # assume PSI
    for col in df.columns:
        if isinstance(col,str) and (col[0:2]=='12' or col[0:2]=='21'):
            m = df[col].median()
            df[col] = df[col].clip(m-cliplevel,m+cliplevel)

def get_transducer_metadata(serialnum, transducersDF):
    this_transducer = None
    subsetdf = transducersDF[(transducersDF['serial']) == serialnum]
    if len(subsetdf.index)==1:
        this_transducer = subsetdf.iloc[0].to_dict()    
    return this_transducer

def get_temperature_data(df, col, temperatureCorrect, this_transducer):
    # get temperature series, filling blanks beyond 2022-08-04 with average values
    tempcol = f'{col}_temp'
    temperatureSeries=None
    if temperatureCorrect:
        if tempcol in df.columns:
            temperatureSeries = df[tempcol].fillna(this_transducer['tmean']) # fill any nans
            df[tempcol]=temperatureSeries # this would insert temperature into output dataframe
        else:
            temperatureSeries = this_transducer['tmean'] # just use average temperature determined in 04_compare_barometers, which was for 07/21-08/03 period
    return temperatureSeries


def correctBarometricData(rawdf, barometricColumns, transducersDF, calibrationCorrect=True, temperatureCorrect=True, heightCorrect=True):
    # turn barometric columns from digits into PSI
    barometricDF = rawdf.copy()
    for colindex,col in enumerate(barometricColumns):
        if col in barometricDF:
            calcol = f'{col}_calibrated'
            corrcol = f'{col}_corrected'          
            this_transducer = get_transducer_metadata(col, transducersDF)
            if isinstance(col,str) and (col=='1226420' or col=='1226429'):
                   
                # get temperature series
                temperatureSeries = get_temperature_data(barometricDF, col, temperatureCorrect, this_transducer)

                # apply calibration equation
                barometricDF[calcol], barometricDF[corrcol] = correctVibratingWireDigits(barometricDF[col], this_transducer, \
                                                                calibrationCorrect=calibrationCorrect, \
                                                                temperatureSeries=temperatureSeries, \
                                                                airpressureSeries=0.0, \
                                                                depthCorrect=False)    
                
                barometricDF.rename(columns={col:f'{col}_digits'}, inplace=True)

            else: # analog barometer
                barometricDF.rename(columns={col:calcol}, inplace=True) # there is no _digits for analog barometers, so just rename to _calibrated
                barometricDF[corrcol] = barometricDF[calcol] # there are no vibrating wire corrections to apply, but we do this so we can height correct below

            # do height correction - we do this for analog barometers too
            if heightCorrect and corrcol in barometricDF.columns:
                print(f'Applying height correction for {col}')
                psiShift = correctForHeightAboveWaterFt(heightFt=this_transducer['set_depth_ft'])
                barometricDF[corrcol] += psiShift

    return barometricDF

def rawdf2psidf(barometricdf, transducersDF, temperatureCorrect=True, airpressureColumn=None, depthCorrect=True):
    psidf = barometricdf.copy()
    #print('- Applying calibration equations')
    for col in psidf.columns:
        if isinstance(col,str) and (col[0:2]=='12' or col[0:2]=='21'):
            if isinstance(col,str) and (col=='1226420' or col=='1226429'):
                continue # we should already have corrected these to sea level PSI
            this_transducer = get_transducer_metadata(col, transducersDF)
            if this_transducer:

                # get temperature series
                temperatureSeries = get_temperature_data(psidf, col, temperatureCorrect, this_transducer)

                # get airpressure series
                airpressureSeries = None
                if airpressureColumn=='well':
                    if col in sensors['shallow']:
                        airpressureColumn = 'AirPressureShallow_corrected'
                    elif col in sensors['intermediate']:
                        airpressureColumn = 'AirPressureIntermediate_corrected'
                    
                if airpressureColumn:
                    airpressureSeries = psidf[airpressureColumn]

                # apply calibration equation
                calcol = f'{col}_calibrated'
                corrcol = f'{col}_corrected'
                psidf[calcol], psidf[corrcol] = correctVibratingWireDigits(psidf[col], this_transducer, \
                                                              temperatureSeries=temperatureSeries, \
                                                                airpressureSeries=airpressureSeries, \
                                                                    depthCorrect=depthCorrect)   
                psidf.rename(columns={col:f'{col}_digits'}, inplace=True) # rename original column to _digits
                
    return psidf
    
def apply_dcshifts(df, xcorrdf, dcshiftdf, force=False): # here could force AirPressureShallow
    if force:
        dcshifts = dcshiftdf.iloc[0].to_dict()
    else:
        best_xcorr_indexes = xcorrdf.iloc[:2, 2:].stack().idxmax()
        #print(best_xcorr_indexes)
        dcshifts = dcshiftdf[best_xcorr_indexes[0]].to_dict()
    dfshifted = df.copy()
    for k, v in dcshifts.items():
        print(f'Shifting {k} by {-v} PSI')
        dfshifted[k] -= v
    return dfshifted, dcshifts

def psidf2passcalsdf():
    # convert every PSI column to Pa
    pass

def round_datetime(df, freq='min', datetimecol='datetime', newcol=None):
    # Round the sample time to nearest hour or minute or second
    # Note this does not resample the data
    newcoldict = {'h':'nearesthour', 'min':'nearestminute', 's':'nearestsecond'}
    if not newcol:
        newcol=newcoldict[freq]
    if newcol:
        df[newcol]=df[datetimecol].dt.round(freq) # freq can also be like 5min, 10s etc.

def merge_and_drop(df1, df2, on='nearestminute', drop=True, how='inner'):
    if isinstance(df2, pd.DataFrame):
        dfmerged = pd.merge(df1 , df2, on=on, how=how)
    else:
        dfmerged = df1.copy()
    if drop:
        dfmerged = dfmerged.loc[:, ~dfmerged.columns.str.endswith('_x')]
        dfmerged = dfmerged.loc[:, ~dfmerged.columns.str.endswith('_y')]
        dfmerged = dfmerged.loc[:, ~dfmerged.columns.str.startswith('DynStdDev')] 
    return dfmerged

def xcorr_columns(df, columns):
    # cross-correlate each column pair, and display as a formatted table
    # also compute DC shifts required to align medians of each column
    xcorr = np.ndarray(shape=(4,4), dtype=float)
    dcshift = np.ndarray(shape=(4,4), dtype=float)
    for i1,col1 in enumerate(columns):
        for i2,col2 in enumerate(columns):
            xcorr[i1,i2] = pd.Series.corr(df[col1], df[col2])
            dcshift[i1,i2] = df[col1].median()-df[col2].median()
    xcorrdf = pd.DataFrame(xcorr, index=columns, columns=columns)
    xcorrdf_styled = xcorrdf.style.set_caption('Cross-correlation')
    dcshiftdf = pd.DataFrame(dcshift, index=columns, columns=columns)
    dcshiftdf_styled = dcshiftdf.style.set_caption('DC shifts')
    display(xcorrdf_styled)
    display(dcshiftdf_styled) 
    return xcorrdf, dcshiftdf

def psi2meters(df, watercolumns=None):
    metersPerPSI = 0.703070
    if isinstance(df, pd.Series):
        return df * metersPerPSI
    else:
    
        df2 = df.copy()
        for col in df.columns:
            if col in watercolumns:
                df2[col] = -df2[col] * metersPerPSI
        return df2


def relative_to_set_depth(df, transducersDF, watercolumns):
    df2 = df.copy()
    for col in df.columns:
        if col in watercolumns:    
            this_transducer = get_transducer_metadata(col, transducersDF)
            df2[col] = df2[col] - this_transducer['set_depth_ft']*0.3048
    return df2


def estimate_sensor_depths(df, watercolumns):
    commoncols = list(set(watercolumns) & set(df.columns))
    medians = pd.Series()
    if len(commoncols)>0:
        medians = df[commoncols].median() # expression chooses columns common to both, so it doesn't crash if any missing
        df2 = df.copy()
        for k,v in medians.items():
            print(f'the estimated set_depth for sensor {k} is {v:.2f} m or {v/0.3048:.2f} ft')
            df2[k] =  df[k] - v
    return df2, medians

def qc_dataframe(df, remove_duplicates=False, keep='last', sort_columns=False):
    '''
    Here we remove any Null rows
    We also remove any duplicate times - using the first entry
    This means if time is out of order and loops back, there could be some corruption in the data
    We could potentially alleviate bad times via resampling at 10ms/100hz
    ''' 
 
    if 'TIMESTAMP' in df.columns:
        df['datetime'] = pd.to_datetime(df['TIMESTAMP'])
        df.dropna(subset='datetime', inplace=True)
        df.drop(['TIMESTAMP', 'RECORD'], axis=1, inplace=True)
        
        if remove_duplicates:
            df.sort_values(by='datetime', inplace=True)
            df.drop_duplicates(subset=['datetime'], keep='last') 
        
    df.dropna(how='all', axis=1, inplace=True) # drop empty columns
    df.drop(df.columns[df.columns.str.contains('unnamed',case = False)],axis = 1, inplace = True) # drop unnamed columns

    # rename thermal columns
    thermcolumns = df.columns[df.columns.str.contains('Therm')]
    if len(thermcolumns)>0:
        if len(thermcolumns)==2:
            datacolumns = watercolumns[-2:]
        elif len(thermcolumns)==6:
            datacolumns = [watercolumns[0], watercolumns[1], aircolumns[2], watercolumns[2], watercolumns[3], aircolumns[3] ]
        for count, oldcol in enumerate(thermcolumns):
            newcol = datacolumns[count] + '_temp'
            df.rename(columns={oldcol:newcol, f'DynStdDev({count})':newcol.replace('_temp','_std')}, inplace=True)

    #if sort_columns:
    #    df.sort_index(axis=1, inplace=True)


def split_by_subdir(dfall2, verbose=False):
    all_dataframes = {}
    for subdir in ['Baro', '20hz', '100hz']:
        print(subdir)
        dfsub = dfall2.copy()[dfall2['subdir']==subdir]
        if verbose:
            print('**********\nDisplaying ',subdir)
            display(dfsub)
        qc_dataframe(dfsub)
        all_dataframes[subdir] = dfsub.copy()
        del dfsub
    return all_dataframes

def trim(df, starttime, endtime):
    return df.query(f"datetime > {starttime.strftime('%Y%m%d%H%M%S')} & datetime < {endtime.strftime('%Y%m%d%H%M%S')}")

def get_raw_data(dfall, starttime, endtime, INPUTDIR, save=True):
    startt = starttime.strftime('%Y-%m-%d')
    dfdata = {}
    allpklfiles = glob.glob('raw_'+startt+'*.pkl')
    if len(allpklfiles)>0:
        print('existing day pickle files found - loading these is faster')
        for pklfile in allpklfiles:
            k = pklfile.split(f'{startt}_')[1].replace('.pkl','')
            print(f'reading {pklfile} into dfdata[{k}]')
            dfdata[k] = pd.read_pickle(pklfile)
    else:
            
        dfday = trim(dfall, starttime=starttime, endtime=endtime)
        
        # load and plot all these files
        for index, row in dfday.iterrows():
            subdir = row['subdir'].lower()
            fullpath = os.path.join(INPUTDIR, str(row['uploaddate']), row['subdir'], row['basename'])
            if not subdir in dfdata:
                dfdata[subdir] = pd.DataFrame()
            print(fullpath)
            if os.path.isfile(fullpath):
                print('- loading')
                thisdf = pd.read_csv(fullpath)
                qc_dataframe(thisdf)
                dfdata[subdir] = pd.concat([dfdata[subdir], thisdf])
                #display(dfdata[subdir])
            else:
                print('- not found')

        if save:
            for k in dfdata.keys():
                pklfile = f'raw_{startt}_{k}.pkl'
                print(f'saving to {pklfile}')
                dfdata[k].to_pickle(pklfile)

    return dfdata


def process_day(dfsummary, starttime, INPUTDIR, transducersDF, apcol='well', temperatureCorrect=True):

    ############### 0. Set up #####################
    # set default outputs
    dcshifts = dict()
    sensor_depths = pd.Series()

    # set endtime 24 hours after starttime
    endtime = starttime + pd.Timedelta(hours=24)

    ############### Processing #####################
    # 1. Load data from starttime to endtime
    dfday = get_raw_data(dfsummary, starttime, endtime, INPUTDIR) # a dict with 3 dataframes corresponding to 'baro', '20hz', and '100hz'

    # 2. Merge the 100hz and baro data, which are both at 100hz
    if '100hz' in dfday:
        if 'baro' in dfday:
            dfmerged = merge_and_drop(dfday['100hz'], dfday['baro'], on='datetime', drop=True, how='outer')
        else:
            print('no baro')
            dfmerged = merge_and_drop(dfday['100hz'], None, on='datetime', drop=True)
    elif 'baro' in dfday:
        print('no 100hz')
        dfmerged = merge_and_drop(dfday['baro'], None, on='datetime', drop=True)
        if 'AirPressureDeep' in dfmerged.columns:
            dfmerged.rename(columns={'AirPressureDeep':'AirPressureIntermediate'}, inplace=True)
    else:
        print('No 100hz, no baro')
        return None #, dcshifts, sensor_depths

    # Choose air pressure column
    """
    if apcol:
        if not apcol in dfmerged.columns:
            return None, dcshifts, sensor_depths
    # Removing following so that if we have apcol=None, the data will get processed without air pressure correction
    else:
        for col in aircolumns:
            if col=='1226420':
                continue
            if col in dfmerged.columns:
                apcol = col
                break
        print(f'Choosing {apcol} as air pressure column')
    """


    # 3. merge the 20hz data via linear interpolation
    if '20hz' in dfday:
        df = dfday['20hz'].set_index('datetime')
        #df = df.asfreq(freq='10ms', method='ffill') # fills with most recent value
        try:
            df = df.resample('10ms').interpolate()
        except: # duplicates in index, but should not need this now because incorporated into qc_dataframe
            df = df[~df.index.duplicated(keep='first')]  
            df = df.resample('10ms').interpolate()
        df.reset_index(inplace=True)
        dfmerged = merge_and_drop(dfmerged, df, on='datetime', drop=True, how='outer')
    else:
        print('no 20hz')

    ############## this is the place to save raw data for this time period, if at all ########################
    #print('Columns in dfmerged: \n', dfmerged.columns)

    # 4. Correct analog and digital air column transducers for calibration, elevation above water
    # NOTE: Although temperature correction works, we only have temperature data from 07/21-08/03
    dfheightcorrected = correctBarometricData(dfmerged, aircolumns, transducersDF, temperatureCorrect=temperatureCorrect, heightCorrect=True)
    #print('- height corrected')
    #display(dfheightcorrected)
    """
    if '100hz' in dfday: 
        # 5. (Correlate and) compare medians to find best DC shifts
        xcorrdf, dcshiftdf = xcorr_columns(dfheightcorrected, aircolumns)

        # 6. Apply these DC shifts to digital barometer columns only
        dfshifted, dcshifts = apply_dcshifts(dfheightcorrected, xcorrdf, dcshiftdf, force=True)

        # 7. Correct digital water column transducers for calibration and barometric pressure
        correctedAllSensorsPSI = rawdf2psidf(dfshifted, transducersDF, temperatureCorrect=temperatureCorrect, airpressureColumn=apcol, depthCorrect=False)        

    elif '20hz' in dfday: # no analog or digital barometers available, so no shifting 
        # 7. Correct digital water column transducers for calibration and barometric pressure
        correctedAllSensorsPSI = rawdf2psidf(dfheightcorrected, transducersDF, temperatureCorrect=temperatureCorrect, airpressureColumn=apcol, depthCorrect=False)

    """
    if '100hz' in dfday or '20hz' in dfday:
        correctedAllSensorsPSI = rawdf2psidf(dfheightcorrected, transducersDF, temperatureCorrect=temperatureCorrect, airpressureColumn=apcol, depthCorrect=True)
        print('- all corrected')
        #display(correctedAllSensorsPSI)
    else:
        print('- 100hz, 20hz not found in dfday')
        return dfheightcorrected #, dcshifts, sensor_depths # height corrected analog barometers only


    # 8: convert to water levels in meters
    #correctedAllSensorsMeters = psi2meters(correctedAllSensorsPSI, watercolumns)

    # 9: convert to water levels in meters relative to the set depth measured by Steve Krupa
    #relativeAllSensorsMeters = relative_to_set_depth(correctedAllSensorsMeters, transducersDF, watercolumns)

    # 10: estimate correct set depths from median of each, and shift by this amount
    #estimatedAllSensorsMeters, sensor_depths = estimate_sensor_depths(correctedAllSensorsMeters, watercolumns)  

    # Step 11 is arguably to go back to step 7 and correct for estimated sensor depths

    return correctedAllSensorsPSI #, dcshifts, sensor_depths

def load_summary_csv(summarycsvfile, split=True, remerge=True, temperatureData=False):

    # Load in the summary of all files - raw 4 hourly data 
    dfsummary = pd.read_csv(summarycsvfile)

    if split: # we also get the 1Sec data if we do not remerge

        # Split in baro, 20Hz, 100Hz
        summary_dataframes = {}
        for subdir in ['Baro', '20hz', '100hz']:
            dfsub = dfsummary.copy()[dfsummary['subdir']==subdir]
            if temperatureData:
                # split out any rows that have 1Sec in basename
                dfsub = dfsub[dfsub['basename'].str.contains('1Sec')]
            else:
                dfsub = dfsub[~dfsub['basename'].str.contains('1Sec')]   
            if len(dfsub)>0:       
                qc_dataframe(dfsub)
                summary_dataframes[subdir.lower()] = dfsub.copy()
            del dfsub
        
        if remerge: # how to merge the 20hz data?
            for k,v in summary_dataframes.items():
                round_datetime(summary_dataframes[k], freq='min' )
            if temperatureData:
                df = merge_and_drop(summary_dataframes['20hz'], summary_dataframes['100hz'], on='nearestminute', how='outer')
            else:
                df = merge_and_drop(summary_dataframes['100hz'], summary_dataframes['baro'], on='nearestminute', how='outer')
                df = merge_and_drop(df, summary_dataframes['20hz'], on='nearestminute', how='outer')
            qc_dataframe(df, sort_columns=True)
            return df # cleaned up and merged dataframes into a single dataframe
        
        else:
            return summary_dataframes # cleaned up dict of dataframes
    else:
        return dfsummary # just the raw dataframe
    
def median_despike(data, window_size, threshold=None):
    """Despike a pandas Series using a moving window median filter."""
    m = data.median()
    data = data - m
    #print(f'median={m}, data={data.describe()}')
    rolling_median = data.rolling(window_size, center=True, min_periods=1).median()
    difference = np.abs(data - rolling_median)
    if not threshold:
        mad = difference.rolling(window_size, center=True, min_periods=1).median()
        threshold = 3 * mad  # Adjust threshold as needed
    #print(f'threshold={threshold}, rolling_median={rolling_median.describe()}')
    despiked_data = np.where(difference > threshold, rolling_median, data)
    #return pd.Series(despiked_data, index=data.index) + m
    return pd.Series(despiked_data) + m