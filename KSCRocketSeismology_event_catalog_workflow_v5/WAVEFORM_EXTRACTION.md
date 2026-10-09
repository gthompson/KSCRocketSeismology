# Event-based SDS waveform extraction (v0.6.1)

Requires installed `flovopy.enhanced.sdsclient.EnhancedSDSClient` and ObsPy.

```bash
ksc-rockets extract --event-id EVENT_ID --sds-root /Volumes/classdata/remastered/SDS_KSC
ksc-rockets extract --all --sds-root /Volumes/classdata/remastered/SDS_KSC --station BCHH
ksc-rockets extract --all --sds-root /Volumes/classdata/remastered/SDS_KSC --dry-run
ksc-rockets extract --all --sds-root /Volumes/classdata/remastered/SDS_KSC --retry-missing
```

Without `--trace-id`, channel IDs are discovered from SDS day files for **every UTC day overlapping the extraction window**. Discovery is cached per day within a batch. `--trace-id` can be repeated to request explicit IDs (including missing ones). `--station` limits automatic discovery only. By default, all sample rates are considered. `--skip-low-rate` excludes channel codes beginning with L.

Availability is assessed with `get_availability_percentage()` for each channel across the event window, returning fraction 0–1 and gap count. `--no-availability` disables this extra I/O. The extraction manifest distinguishes found IDs, missing explicit IDs, channel availability, and raw waveform segments. A channel present in the SDS directory is not necessarily fully available during the event.

Output: `data/waveforms/raw/<event_id>/<request_hash>/raw.mseed` and `extraction.json`. Raw samples are not filtered, response-corrected, or gap-filled. Existing complete/partial/missing results are skipped unless `--overwrite`; `--retry-missing` revisits previously missing results. The request hash includes selected channels, window, event ID, and archive root. **Note:** auto-discovery is re-run on each invocation; adding new channels may generate a new request hash, and previously missing results require `--retry-missing` to be revisited.

Caveat: automatically discovered channels are only channels represented by SDS files. Expected-but-absent channels require explicit `--trace-id` or a future StationXML inventory integration. This implementation has not been exercised against the user's mounted SDS archive.
