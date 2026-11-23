"""ksclib: shared seismo-acoustic tools for KSC launch and explosion studies.

    from ksclib import load_event, event_stream_raw, instrument_correct, station_table
    ev = load_event("09_artemis2_paper/artemis2.yaml")
    st = instrument_correct(event_stream_raw(ev), ev)

Each paper keeps an event YAML (see ksclib.event) and thin notebooks; launch-agnostic
signal processing lives in flovopy (e.g. flovopy.ingest.gem_overflow).
"""
from .event import Event, load_event
from .data import (SKIPPED_FILES, sds_client, get_group_stream, get_event_stream, read_restored,
                   event_stream_raw, read_sds_files)
from .responses import centaur_response_file, centaur_inventory, smartsolo_paz
from .correct import instrument_correct
from .geometry import station_table, source_geometry

__version__ = "0.1.0"
