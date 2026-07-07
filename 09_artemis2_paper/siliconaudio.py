from pathlib import Path
from obspy import Stream, UTCDateTime, read
from flovopy.enhanced.sdsclient import EnhancedSDSClient

def merge_miniseed_to_sds(
    input_root,
    sds_root,
    pattern="*.ms",
    write_mode="merge",
    preprocess=False,
    verbose=True,
    merge_after_each_hour=False,
    **write_kwargs,
):
    """
    Read 1-minute MiniSEED files from a YYYY/MM/DD/HH directory structure,
    assemble them into day streams in strict chronological order, and write
    them into an SDS archive using EnhancedSDSClient.write_stream().

    Parameters
    ----------
    input_root : str or Path
        Root directory containing waveform files in YYYY/MM/DD/HH folders.
    sds_root : str or Path
        Root directory of the SDS archive to write into.
    pattern : str
        Glob pattern for waveform files inside each hour directory.
    write_mode : str
        SDS write mode passed to EnhancedSDSClient.write_stream():
        "fail", "overwrite", or "merge".
    preprocess : bool
        Passed through to EnhancedSDSClient.write_stream().
    verbose : bool
        If True, print progress information.
    merge_after_each_hour : bool
        If True, merge each hour stream before appending to the day stream.
        This can reduce memory pressure for very fragmented data.
    **write_kwargs
        Extra kwargs passed through to EnhancedSDSClient.write_stream().

    Returns
    -------
    list[Path]
        List of SDS files written.
    """
    input_root = Path(input_root)
    sds_root = Path(sds_root)

    sdsclient = EnhancedSDSClient(str(sds_root))
    written_all = []

    def log(msg):
        if verbose:
            print(msg)

    def sorted_numeric_dirs(parent):
        """
        Yield child directories whose names are digits, sorted numerically.
        """
        dirs = [p for p in parent.iterdir() if p.is_dir() and p.name.isdigit()]
        return sorted(dirs, key=lambda p: int(p.name))

    for year_dir in sorted_numeric_dirs(input_root):
        for month_dir in sorted_numeric_dirs(year_dir):
            for day_dir in sorted_numeric_dirs(month_dir):
                year = int(year_dir.name)
                month = int(month_dir.name)
                day = int(day_dir.name)

                day_start = UTCDateTime(year, month, day)
                day_end = day_start + 86400

                log(f"Processing {year:04d}-{month:02d}-{day:02d}")

                st_day = Stream()
                nfiles = 0

                for hour_dir in sorted_numeric_dirs(day_dir):
                    hour_files = sorted(hour_dir.glob(pattern), key=lambda p: p.name)

                    if not hour_files:
                        continue

                    if merge_after_each_hour:
                        st_hour = Stream()

                    for f in hour_files:
                        try:
                            st_file = read(str(f))
                            nfiles += 1

                            if merge_after_each_hour:
                                st_hour += st_file
                            else:
                                st_day += st_file

                        except Exception as e:
                            log(f"  Failed to read {f}: {e}")

                    if merge_after_each_hour and len(st_hour) > 0:
                        try:
                            st_hour.merge(method=0, fill_value=None)
                        except Exception as e:
                            log(f"  Hour-level merge failed in {hour_dir}: {e}")
                        st_day += st_hour

                if nfiles == 0:
                    log("  No files found")
                    continue

                if len(st_day) == 0:
                    log("  No valid traces")
                    continue

                # Merge only after the day has been assembled in chronological order.
                try:
                    st_day.merge(method=0, fill_value=None)
                except Exception as e:
                    log(f"  Day-level merge failed: {e}")
                    continue

                # Trim to exact UTC day bounds.
                st_day.trim(day_start, day_end, nearest_sample=False)

                if len(st_day) == 0:
                    log("  Nothing left after trimming to day bounds")
                    continue

                try:
                    written = sdsclient.write_stream(
                        st_day,
                        mode=write_mode,
                        preprocess=preprocess,
                        verbose=verbose,
                        **write_kwargs,
                    )
                    written_all.extend(written)
                    log(f"  Wrote {len(written)} SDS file(s)")
                except Exception as e:
                    log(f"  Failed to write SDS data for {year:04d}-{month:02d}-{day:02d}: {e}")

    return written_all