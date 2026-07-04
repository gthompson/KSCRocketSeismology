function catalogobj = associateArrivals(arrivalobj, association_window_seconds)
%ASSOCIATEARRIVALS Associate arrivals into catalog events.

catalogobj = arrivalobj.associate(association_window_seconds);
end
