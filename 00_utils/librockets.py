import numpy as np
import obspy
import os
import sys
import matplotlib.pyplot as plt
import header
paths = header.setup_environment()
sys.path.append(os.path.join(paths['Developer'], 'SoufriereHillsVolcano', 'lib'))
import libseisGT
from flovopy.sds.sds_utils import sds2eventStream



def detectEvent(st):
    st2 = st.copy().filter('bandpass', freqmin=5, freqmax=16)
    return libseisGT.detect_network_event(st2, threshon=4, threshoff=1, sta=5, lta=100, pad=0.0, best_only=True)



# Function to print the directory-like structure
def print_tree(nslc_list):
    # Create a dictionary to store the structure
    tree = {}
    
    # Build the nested tree structure
    for network, station, location, channel in nslc_list:
        if network not in tree:
            tree[network] = {}
        if station not in tree[network]:
            tree[network][station] = {}
        if location not in tree[network][station]:
            tree[network][station][location] = []
        tree[network][station][location].append(channel)
    
    # Function to print the tree recursively
    def print_branch(branch, indent=""):
        for key, value in branch.items():
            if isinstance(value, dict):
                # It's a directory, print it and recurse
                print(f"{indent}{key}/")
                print_branch(value, indent + "    ")
            else:
                # It's a list of channels
                for channel in value:
                    print(f"{indent}{key}/{channel}")
    
    # Print the root of the tree
    print_branch(tree)



'''
def sds2eventStream(launchtime, sdsclient, thisSDSobj, pretrig=3600, posttrig=3600, networks=['*'], bandcodes=['GHDCESB'], show_available=True):  
moved to flovopy.sds.sds method
'''      
    

def try_different_waveform_loading_methods(sdsclient, thisSDSobj, startt, endt, network='*'):

    # ObsPy SDS archive reader
    st3 = sdsclient.get_waveforms(network, "*", "*", "[HDCES]*", startt, endt)

    # My SDS class that wraps ObsPy SDS reader
    thisSDSobj.read(startt, endt, speed=1)
    st4 = thisSDSobj.stream

    combine_streams(st3, st4)    
    
    return st3
    
def combine_streams(stB, stA):
    combined = stB + stA
    smart_merge(combined, strategy='both', allow_timeshift=True)

'''
def clean(st, taperseconds):
    for tr in st:
        trace_seconds = tr.stats.delta * tr.stats.npts
        libseisGT.clean_trace(tr, taperFraction=taperseconds/trace_seconds, filterType="highpass", freq=0.01, corners=2, zerophase=True, inv=None)
    


def apply_calibration_correction(st):
    # calibration correction

    for tr in st:
        if 'countsPerUnit' in tr.stats:
            continue
        else:
            tr.stats['countsPerUnit'] = 1
            if not 'units' in tr.stats:
                tr.stats['units'] = 'Counts'
            if tr.stats.station[0].isnumeric(): # well data
                if len(tr.stats.network)==0:
                    tr.stats.network = '6'
                if tr.stats.channel[2] == 'D':
                    tr.stats.countsPerUnit = 1/LLE.psi2inches(1) # counts (psi) per inch
                    tr.stats.units = 'inches'
                elif tr.stats.channel[2] == 'H':
                    tr.stats.countsPerUnit = 1/6894.76 # counts (psi) per Pa
                    tr.stats.units = 'Pa'
            elif tr.stats.channel[1]=='D':
                tr.stats.countsPerUnit = 720 # counts/Pa on 1 V FS setting
                if tr.id[:-1] == 'FL.BCHH3.10.HD':
                    if tr.stats.starttime < obspy.UTCDateTime(2022,5,26): # Chaparral M25. I had it set to 1 V FS. Should have used 40 V FS. 
                        if tr.id == 'FL.BCHH3.10.HDF':
                            tr.stats.countsPerUnit = 8e5 # counts/Pa
                        else:
                            tr.stats.countsPerUnit = 720 # counts/Pa 
                    else: # Chaparral switched to 40 V FS
                        if tr.id == 'FL.BCHH3.10.HDF':
                            tr.stats.countsPerUnit = 2e4 # counts/Pa
                        else:
                            tr.stats.countsPerUnit = 18 # counts/Pa 
                tr.stats.units = 'Pa'

            elif tr.stats.channel[1]=='H':
                tr.stats.countsPerUnit = 3e2 # counts/(um/s)
                tr.stats.units = 'um/s'
            tr.data = tr.data/tr.stats.countsPerUnit


def maxamp(tr):
    return np.max(np.abs(tr.data))

def add_snr(st, assoctime, threshold=1.5):
    nstime = max([st[0].stats.starttime, assoctime-240])
    netime = min([st[0].stats.endtime, assoctime-60])
    sstime = assoctime
    setime = min([st[0].stats.endtime, assoctime+120])    
    for tr in st:
        tr_noise = tr.copy().trim(starttime=nstime, endtime=netime)
        tr_signal = tr.copy().trim(starttime=sstime, endtime=setime)
        tr.stats['noise'] = np.nanmedian(np.abs(tr_noise.data))
        tr.stats['signal'] = np.nanmedian(np.abs(tr_signal.data))
        tr.stats['snr'] = tr.stats['signal']/tr.stats['noise']

def group_streams_for_plotting(st):
    groups = {}
    stationsWELL = ['6S', '6I']
    for station in stationsWELL:
        stationStream = st.select(network=station)
        #stationIDS = list(set([tr.id for tr in stationStream]))
        groups[station] = stationStream
    streamSA = st.select(network='FL')
    stationsSA = list(set([tr.stats.station for tr in streamSA]))
    for station in stationsSA:
        stationStream = streamSA.select(station=station)
        #stationIDS = list(set([tr.id for tr in stationStream]))
        groups[station] = stationStream
    #print(groups)
    return groups 

def despike_trace(trace):
    # Parameters for despiking
    window_size = 5  # Size of the sliding window
    threshold_factor = 3  # Threshold factor to define spikes

    # Loop over the data and apply despiking
    despiked_data = trace.data.copy()
    for i in range(window_size, len(trace.data) - window_size):
        # Define the window of data around each point
        window = trace.data[i - window_size:i + window_size + 1]
        
        # Calculate local median and standard deviation
        local_median = np.median(window)
        local_std = np.std(window)
        
        # Identify spikes: data point deviates too much from the local median
        if np.abs(trace.data[i] - local_median) > threshold_factor * local_std:
            despiked_data[i] = local_median  # Replace with the local median

    # Update the trace data with the despiked data
    trace.data = despiked_data
'''



from flovopy.core.preprocessing import clean_stream

def remove_response(seismic_st, inv, output='VEL', pre_filt=None, verbose=False):
    """
    Removes instrument response from a Stream using robust trace-wise handling.

    Parameters:
    -----------
    seismic_st : obspy.Stream
        Input stream to process.

    inv : obspy.Inventory
        Instrument response metadata.

    output : str
        Desired output physical units ('DISP', 'VEL', 'ACC', or 'DEF').

    pre_filt : tuple or None
        Pre-filter frequencies (f1, f2, f3, f4) in Hz. If None, inferred based on `output`.

    verbose : bool
        If True, print diagnostic messages.

    Returns:
    --------
    Stream
        Cleaned and calibrated stream with removed response. Traces that fail are skipped.
    """
    return clean_stream(
        stream_in=seismic_st,
        taperFraction=0.05,
        filterType='bandpass',
        freq=(1.0, 10.0),  # Can be overridden by user or dynamically set based on pre_filt
        corners=4,
        zerophase=True,
        inv=inv,
        outputType=output,
        verbose=verbose
    )


from sklearn.mixture import GaussianMixture
def detect_incorrect_p2p_voltage_setting(st, stationratio=20.0, allratio=200.0):
    # for a Centaur datalogger, this is designed to detect if p2p voltage should have been 1 rather than 40
    # we do this by checking for a bimodal distribution of the 95th percentile of the data in each trace

    amplitudes = np.array([np.nanpercentile(abs(tr.data), 95) for tr in st])
    m = np.nanmedian(amplitudes)
    for i, tr in enumerate(st):
        if amplitudes[i] > m * allratio or amplitudes[i] < m/allratio: # bad channel
            st.remove(tr) 


    stations = ['BCHH*', 'BHP*']

    for station in stations:
        #print(station)
        st_station = st.select(station=station)
        if len(st_station)>2:
            amplitudes = np.array([np.nanpercentile(abs(tr.data), 95) for tr in st_station])
            #print(amplitudes)

            # Fit a GMM to the data with correction factor 1
            gmm = GaussianMixture(n_components=2)
            gmm.fit(amplitudes.reshape(-1, 1))

            # Get the responsibilities (probabilities) of each data point for both components
            responsibilities = gmm.predict_proba(amplitudes.reshape(-1, 1))

            # Assign each data point to the component with the highest responsibility
            component_1_indices = np.where(responsibilities[:, 0] > responsibilities[:, 1])[0]
            component_2_indices = np.where(responsibilities[:, 1] > responsibilities[:, 0])[0]
            #print(component_1_indices, component_2_indices)
            #print(st)

            '''
            # Plot the seismogram and color-code by component
            plt.figure(figsize=(10, 6))
            plt.plot(amplitudes, label="Corrected Amplitude", color='gray', alpha=0.6)

            # Plot the data points for each component with different colors
            plt.scatter(component_1_indices, amplitudes[component_1_indices], color='blue', label="Component 1", s=10)
            plt.scatter(component_2_indices, amplitudes[component_2_indices], color='red', label="Component 2", s=10)

            plt.title("Amplitude Distribution with GMM Components")
            plt.xlabel("Sample Index")

            plt.show()
            '''

            if len(component_2_indices)>0:
                #print(gmm.means_)
                mratio = gmm.means_[1]/gmm.means_[0]
                if gmm.means_[0] > gmm.means_[1]:
                    for tr in [st[i] for i in component_1_indices]:
                        if mratio<1.0/stationratio:
                            st.remove(st.select(id=tr.id)[0])
                        else:
                            st.select(id=tr.id)[0].data = tr.data/40
                else:
                    for tr in [st[i] for i in component_2_indices]:
                        if mratio>stationratio:
                            st.remove(st.select(id=tr.id)[0])                        
                        else:  
                            st.select(id=tr.id)[0].data = tr.data/40
