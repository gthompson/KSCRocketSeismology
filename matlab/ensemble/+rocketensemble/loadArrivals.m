function arrivalobj = loadArrivals(dbpath)
%LOADARRIVALS Retrieve arrivals from an Antelope/CSS database.

arrivalobj = Arrival.retrieve('antelope', dbpath);
if isempty(arrivalobj)
    error('No arrivals loaded from %s', dbpath);
end
end
