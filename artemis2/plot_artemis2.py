from obspy import UTCDateTime, read
import gemlog

## read the st
st = read('mseed/2026-04-01T00_00_00..*..HDF.mseed')
print(st)

## combine traces so that each station has one trace
st.merge()
print(st)

## deconvolve the instrument response
## if you used a config file to set the Gem's gain to low, change the gain setting below
st = gemlog.deconvolve_gem_response(st, gain='high') 

## filter st above 1 Hz (lower frequencies are often wind noise)
#st.filter("highpass", freq=1.0)
st.filter("highpass", freq=0.5)

## trim the st around a known event
launchtime = UTCDateTime(2026,4,1,22,35,12)
pretrigger=72
posttrigger=pretrigger
duration=120
t1 = launchtime - pretrigger
t2 = t1 + duration + posttrigger

## plot the results
st.plot(starttime=t1, endtime=t2)
