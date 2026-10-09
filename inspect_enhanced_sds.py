#!/usr/bin/env python3
"""Inspect EnhancedSDSClient discovery, availability, and waveform APIs.

Example:
 python inspect_enhanced_sds.py /Volumes/classdata/remastered/SDS_KSC --start 2016-09-01T13:06:45 --end 2016-09-01T13:11:15 --station BCHH
"""
import argparse
import inspect
from fnmatch import fnmatchcase
from obspy import UTCDateTime
from flovopy.enhanced.sdsclient import EnhancedSDSClient


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('sds_root')
    p.add_argument('--start', default='2016-09-01T13:06:45')
    p.add_argument('--end', default='2016-09-01T13:11:15')
    p.add_argument('--station', default='BCHH', help='Station pattern, e.g. BCHH or *')
    p.add_argument('--max-channels', type=int, default=12)
    args = p.parse_args()
    start, end = UTCDateTime(args.start), UTCDateTime(args.end)
    if end <= start:
        p.error('--end must be later than --start')
    client = EnhancedSDSClient(args.sds_root)
    print('Client:', type(client).__module__, type(client).__name__)
    print('SDS root:', client.sds_root_path)
    print('\nRelevant callable methods (signature and implementation owner):')
    terms = ('nslc', 'trace_id', 'availability', 'waveform', 'latency', 'read', 'get_all')
    for name in sorted(n for n in dir(client) if any(t in n.lower() for t in terms)):
        try:
            method = getattr(client, name)
            if not callable(method):
                continue
            owner = next((cls.__name__ for cls in type(client).__mro__ if name in cls.__dict__), '?')
            print(f'  {name}{inspect.signature(method)}  [{owner}]')
        except Exception as exc:
            print(f'  {name}: {type(exc).__name__}: {exc}')
    print('\nDiscovery over requested time window:')
    try:
        nslcs = sorted(x for x in client.iter_nslc(start, end, skip_low_rate=False)
                       if fnmatchcase(x[1], args.station))
        print(f'  Found {len(nslcs)} matching NSLCs')
        for net, sta, loc, cha in nslcs[:args.max_channels]:
            print(f'  {net}.{sta}.{loc}.{cha}', end='')
            try:
                frac, gaps = client.get_availability_percentage(net, sta, loc, cha, start, end)
                print(f' | availability={frac:.3f} | gap_count={gaps}')
            except Exception as exc:
                print(f' | availability ERROR: {type(exc).__name__}: {exc}')
        if len(nslcs) > args.max_channels:
            print(f'  ... {len(nslcs)-args.max_channels} more channels omitted')
    except Exception as exc:
        print(f'  Discovery ERROR: {type(exc).__name__}: {exc}')
    print('\nThis script reads SDS metadata/availability; it does not write or modify the archive.')


if __name__ == '__main__':
    main()
