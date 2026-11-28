# KSC event catalog: operations guide

How to keep the launch catalog, the per-event waveform products, the website and the Zenodo archive
up to date. Written 2026-11-27. Each section lists the commands in order; run them on the Mac mini
unless noted.

* Catalog and site code: `event_catalog_workflow_v5/` (package `kscrockets`)
* Waveform processing code: `ksclib/` (package `ksclib`)
* Network eras, SDS archives and StationXML: `07_ensemble_paper/ensemble.yaml`
* All outputs live outside git, under `~/work/KSC_event_catalog/` (`~/work` is the Pulwtop NVMe drive).

## 0. Setup (every terminal session)

Work in the main checkout on branch `shared-ksclib`:

```bash
cd ~/Developer/KSCRocketSeismoHydrology/event_catalog_workflow_v5
git checkout shared-ksclib
ksc() { PYTHONPATH=$PWD/src:$PWD/../ksclib/src conda run --no-capture-output -n flovopy_plus python -m kscrockets.cli "$@"; }
ksc info
```

Every command below is `ksc <command>`. `ksc <command> --help` lists its options.

### Where things are

| What | Where | In git? |
|---|---|---|
| Reconciled catalog (915+ events) | `data/processed/ksc_rockets.sqlite` | yes |
| Stable event ids | `data/curated/reconciled_event_ids.csv` | yes |
| Detected origin times | `data/curated/detected_times.csv` | yes |
| Station availability per event | `data/availability/*.csv` and the sqlite | yes |
| Zenodo links and metadata | `data/curated/waveform_urls.csv`, `data/curated/zenodo_metadata.json` | yes |
| Per-event products (miniSEED, plots, metrics, manifest) | `~/work/KSC_event_catalog/<YYYY>/<event_id>/` | no |
| Run result tables (status, metrics, onsets, weather) | `~/work/KSC_event_catalog/tables/` | no |
| Local website (PNG plots, local miniSEED links) | `~/work/KSC_event_catalog/site/` | no |
| Public website (WebP plots, Zenodo links) | `~/work/KSC_event_catalog/site_web/` | its own repo (section 5) |
| Zenodo zips (one per year) and `files_index.csv` | `~/work/KSC_event_catalog/archive/` | no |
| Weather downloads (cache) | `~/work/KSC_event_catalog/weather/` | no |
| Run logs and event lists | `~/work/KSC_event_catalog/runs/` | no |

### SDS archives and StationXML (from `07_ensemble_paper/ensemble.yaml`)

| Era | Dates | SDS archive | Responses |
|---|---|---|---|
| `campaigns_2016_2022` | 2016-01-01 to 2023-01-01 | `/Volumes/classdata/remastered/SDS_KSC` (hal `/data/remastered/SDS_KSC`) | `03_stationxml/KSC.xml` |
| `network_2026` | 2026-01-01 to 2027-01-01 | `/Volumes/Pulwtop/SDS_KSC_2026` | `03_stationxml/KSC.xml` |

Since 2026-11-27 the 2026 era reads `/Volumes/Pulwtop/SDS_KSC_2026`: a copy of
`/Volumes/KSCGTdownld/SDS` with Centaur channels renamed to SEED C??/H?? and the B29/B20 records
restored from the tachyon backup. `/Volumes/KSCGTdownld/SDS` is still the ingest master (section 4),
so new 2026 data must also be added to `SDS_KSC_2026` (section 4, step 3b). ksclib reads either the
D or the C/H spelling of the Centaur channels, so pointing the `sds:` line of `network_2026` back
at `/Volumes/KSCGTdownld/SDS` also works.

**Events in a year that no era covers (2023–2025) get no waveforms.** Add an era to
`ensemble.yaml` when data from those years are archived.

### What a run writes

`ksc process` writes, for each event:
* `raw_counts.mseed`: raw counts for catalog time −900 s to +900 s, as read from the SDS archive.
* `corrected.mseed`: Pa and m/s.
* `stations.csv`, `metrics.csv`, `onsets.csv`.
* `plots/`.
* `manifest.json`: the StationXML used, the parameters, warnings and status.

It also updates the tables under `~/work/KSC_event_catalog/tables/`. Its detected origin times go
into `data/curated/detected_times.csv`, but the catalog only uses them after the next `ksc rebuild`.

If correction fails, the run still writes `raw_counts.mseed`, `stations.csv` and the manifest. The
manifest's `raw_extent` shows how much data was actually read. Rerunning an event replaces its earlier
rows, so the newest run wins.

### Finishing step after any change (referred to below as "finish")

```bash
ksc rebuild                          # detected times -> catalog; reattaches availability
ksc build-site                       # local site
ksc build-site --web                 # public site (WebP), then publish: section 5
git add data && git commit -m "..."  # sqlite, detected_times.csv, availability, ...
```

---

## 1. Re-run an event after finding more data for a past launch

1. **Put the data into the right SDS archive** (see the era table). Do this losslessly with
   `03_stationxml/archive_fix/add_records.py`. It adds only records the archive doesn't have, keeps
   a copy of every file it changes, and renames Centaur D?? channels to C??/H??. It is a dry run
   unless you pass `--apply`.

   ```bash
   python ../03_stationxml/archive_fix/add_records.py --sds /Volumes/Pulwtop/SDS_KSC_2026 --tag 20261201 \
       /path/to/found/files/*.mseed            # dry run: read the report
   python ../03_stationxml/archive_fix/add_records.py --sds /Volumes/Pulwtop/SDS_KSC_2026 --tag 20261201 \
       /path/to/found/files/*.mseed --apply
   ```

   * For raw minute files, add `--by-header`.
   * To fix wrong codes in the headers, add `--network/--station`.
   * The 2016–2022 archive is read-only from the Mac. Run add_records on hal, against
     `/data/remastered/SDS_KSC`.

2. **Make sure KSC.xml has an epoch for the new channels and dates.** Without one, a channel is read
   but dropped from the corrected data. See section 2.

3. **Update availability, so the catalog and the site count the new stations:**

   ```bash
   ksc availability --sds 2016-01-01:2023-01-01:/Volumes/classdata/remastered/SDS_KSC \
                    --sds 2026-01-01:2027-01-01:/Volumes/Pulwtop/SDS_KSC_2026
   ```

4. **Re-run the event** (or several: repeat `--event-id`, or use `--events-file list.txt`):

   ```bash
   ksc process --event-id ksc-ffc076382361 --run-id rerun-20261201 --notes "added BCHH data from backup"
   ```

5. **Weather, if the event never had it:**

   ```bash
   ksc fetch-weather --event-id ksc-ffc076382361
   ```

6. **Finish.** If the event's year is already on Zenodo, follow section 6 for that year.

To find an event id: use the site search, or

```bash
sqlite3 data/processed/ksc_rockets.sqlite \
  "select event_id,event_time_utc,event_type,name,pad from events where event_time_utc like '2016-06-15%'"
```

## 2. Re-run events after the StationXML is updated

KSC.xml is built in `03_stationxml/` (master sheet `ksc_stations_master_v3.xlsx`, script
`make_master_v3.py`, validator). The run reads whatever `03_stationxml/KSC.xml` is in the checkout, so
commit the new KSC.xml on `shared-ksclib` first.

1. **Decide which events are affected.** That's every event in the dates of the epochs you changed. To
   list them, from `~/work/KSC_event_catalog/runs/full-20261127/events.txt` (one line per event with
   data, `event_id   # date type pad`):

   ```bash
   grep " 2019-0[3-6]" ~/work/KSC_event_catalog/runs/full-20261127/events.txt > /tmp/affected.txt
   ```

   For all events with data, use `--all-with-data` in place of `--events-file`.

2. **Re-run them,** in the background if there are many. The 2016–2022 data come over SMB from
   classdata, so allow 2–8 minutes per event.

   ```bash
   caffeinate -i zsh -c 'ksc() { PYTHONPATH=$PWD/src:$PWD/../ksclib/src conda run --no-capture-output -n flovopy_plus python -m kscrockets.cli "$@"; }; \
     ksc process --events-file /tmp/affected.txt --run-id sxml-20261201 --notes "KSC.xml <commit>"' \
     > ~/work/KSC_event_catalog/runs/sxml-20261201.log 2>&1 &
   ```

   Long runs (more than about 50 events) are safer in batches. See
   `~/work/KSC_event_catalog/runs/full-20261127/run.sh`: it runs batches of 20 and writes a `.done`
   marker per batch, so a restart resumes where it stopped.

3. **Check for status other than ok:**

   ```bash
   python3 -c "import pandas as pd; p=pd.read_csv('$HOME/work/KSC_event_catalog/tables/event_processing.csv'); print(p.status.value_counts()); print(p[p.status!='ok'][['event_id','status','error']])"
   ```

4. **Finish,** then repackage and upload the affected years (section 6).

Raw counts don't depend on StationXML. Amplitudes in `corrected.mseed` and `metrics.csv` do.

## 3. Update the event catalog periodically (new launches)

Monthly, or before a paper:

```bash
ksc fetch-ll2          # Launch Library 2: launches, landings, static fires (rate-limited, ~15 requests/hour)
ksc fetch-gcat         # GCAT launch list and pad explosions
ksc rebuild            # reconcile Excel + LL2 + GCAT + manual events -> sqlite
ksc completeness       # data/availability/catalog_completeness.csv: months where the catalog != GCAT
```

`ksc rebuild --refresh-external` does the two fetches and the rebuild in one step.

* **Check:**
  * `catalog_completeness.csv` flags months where the counts disagree.
  * New event ids are added to `data/curated/reconciled_event_ids.csv`. Existing ids never change.
* **Events no catalog lists** (a test you saw in the data, a sonic boom):

  ```bash
  ksc add-event static_fire 2026-12-03T18:22:10Z "Starship static fire" --pad LC39A --notes "seen on B20"
  ```

  then run `ksc rebuild`.
* **Commit:** `data/raw/external/`, `data/curated/`, `data/availability/` and `data/processed/ksc_rockets.sqlite`.

Then process the new events that have data:

```bash
ksc availability --sds 2016-01-01:2023-01-01:/Volumes/classdata/remastered/SDS_KSC \
                 --sds 2026-01-01:2027-01-01:/Volumes/Pulwtop/SDS_KSC_2026
ksc process --all-with-data --only-new --run-id update-20261201
```

`--only-new` skips events whose latest status is ok. Next, fetch weather for the new events. List the
ids processed in this run, then pass them:

```bash
python3 -c "import pandas as pd; p=pd.read_csv('$HOME/work/KSC_event_catalog/tables/event_processing.csv'); print('\n'.join(p[p.run_id=='update-20261201'].event_id))" > /tmp/new.txt
ksc fetch-weather --events-file /tmp/new.txt
```

Then **finish**.

## 4. After a maintenance trip: new data -> SDS archive -> more events with waveforms

Ingest tooling is in `2026_ingest_service_runs/`. Read `docs/DATA_ORGANIZATION.md` and
`docs/GEM_INGESTION.md` there.

1. **Copy the downloads unchanged** to `/Volumes/KSCGTdownld/<YYYYMMDD>_service/00_download/`:
   `Centaur/`, `Gem/raw`, `SmartSolo/`, `Guralp/`, `SiliconAudio/`. Keep a second copy on hal.

2. **Create the run config:**
   `2026_ingest_service_runs/config/<YYYYMMDD>_service/service_run.yaml`, from
   `config/service_run_template.yaml`.

3. **Merge the Centaur SDS into the master archive.** It's a dry run first. flovopy renames D?? to
   C??/H?? as it ingests.

   ```bash
   cd ../2026_ingest_service_runs
   python ingest_centaur_services.py --runs 20261201_service              # dry run
   python ingest_centaur_services.py --runs 20261201_service --execute
   ```

   * Gems: convert and run the GPS QC (`docs/GEM_INGESTION.md`).
   * SmartSolo: follow `config/smartsolo_mapping_*.csv`.
   * Both then go into the same master SDS.

   **3b. Copy the new days into the archive the catalog reads** (`/Volumes/Pulwtop/SDS_KSC_2026`).
   add_records.py adds only missing records, renames D?? to C??/H??, and keeps backups. Example for
   days 300-365 (all channels: Centaur, Gem, SmartSolo):

   ```bash
   cd ../03_stationxml/archive_fix
   find /Volumes/KSCGTdownld/SDS/2026 -type f -name '*.2026.3[0-6][0-9]' > /tmp/new_days.txt
   python add_records.py --sds /Volumes/Pulwtop/SDS_KSC_2026 --tag 20261201 $(cat /tmp/new_days.txt)          # dry run
   python add_records.py --sds /Volumes/Pulwtop/SDS_KSC_2026 --tag 20261201 $(cat /tmp/new_days.txt) --apply
   ```

4. **Add the new epochs to KSC.xml**, in `03_stationxml/`. For each station, record what changed at
   the service: instruments, gains, sample rate, new or removed stations, and the start/end times. Then
   rebuild and validate KSC.xml and commit it. Without new epochs, new channels have no response and
   are dropped.

5. **Update availability.** Past events that gained data then show more stations. New events in the
   new date range become eligible.

   ```bash
   cd ../event_catalog_workflow_v5
   ksc availability --sds 2016-01-01:2023-01-01:/Volumes/classdata/remastered/SDS_KSC \
                    --sds 2026-01-01:2027-01-01:/Volumes/Pulwtop/SDS_KSC_2026
   ```

6. **Update the catalog for launches since the last update:** section 3 (`fetch-ll2`, `fetch-gcat`,
   `rebuild`).

7. **Process:**
   * New events: `ksc process --all-with-data --only-new --run-id service-20261201`.
   * Events whose window the new data now covers (they ran before with fewer stations): re-run them as
     in section 1, step 4. For example, every 2026 event since the previous service:

     ```bash
     grep " 2026-\(0[9]\|1[0-2]\)" ~/work/KSC_event_catalog/runs/full-20261127/events.txt > /tmp/since.txt
     ```

8. **Weather for the new events** (section 3), then **finish**. Repackage the year (section 6).

**A new year (2027)** needs a new era in `07_ensemble_paper/ensemble.yaml`: copy `network_2026` and
change the name, dates and `sds`. Also extend the `--sds` arguments of `availability`.

## 5. The website on GitHub

**Status (2026-11-27): the site is not on GitHub yet.** `build-site --web` writes it to
`~/work/KSC_event_catalog/site_web/` (341 MB for 361 events). The repository is created once, as below.

What makes it fit on GitHub Pages:
* Plots are WebP at 1100 px, quality 80.
* miniSEED is not in the site: each event page links to its year zip on Zenodo, from
  `data/curated/waveform_urls.csv`.
* `.nojekyll` is written, so Pages serves the files as they are.
* GitHub Pages allows 1 GB per site.

The site is static HTML. The maps load Leaflet and the map tiles from the internet.

### One-time setup

1. On github.com, create a new **public** repository, for example `gthompson/rocketcat`, with no
   README. Public is required for Pages on a free account. Only plots and metrics go into it.
2. Turn the site folder into that repository:

   ```bash
   cd ~/work/KSC_event_catalog/site_web
   git init -b main
   git add -A && git commit -m "KSC event catalog site"
   git remote add origin https://github.com/gthompson/rocketcat.git
   git push -u origin main
   ```

3. On github.com: repository **Settings → Pages → Build and deployment → Deploy from a branch →
   `main`, `/ (root)` → Save**. A minute later the site is at `https://gthompson.github.io/rocketcat/`.

   For a custom domain, put the name in Settings → Pages → Custom domain, and add a DNS CNAME
   pointing to `gthompson.github.io`.

### Updating it

```bash
cd ~/Developer/KSCRocketSeismoHydrology/event_catalog_workflow_v5
ksc build-site --web                         # rewrites site_web/; never deletes its .git
cd ~/work/KSC_event_catalog/site_web
git add -A && git commit -m "Update $(date +%F)" && git push
```

Each full rebuild rewrites the WebP files, so the repository history grows by about the size of the
changed plots. When it gets near 1 GB, replace the history with a single commit:

```bash
cd ~/work/KSC_event_catalog/site_web
git checkout --orphan fresh && git add -A && git commit -m "KSC event catalog site $(date +%F)"
git branch -D main && git branch -m main && git push -f origin main
```

A `.git` folder in `site_web` is never part of the site. Old event pages and plots that no longer
exist are not deleted automatically; remove them by hand if an event is dropped.

The local site (`~/work/KSC_event_catalog/site/index.html`) is for the Mac only: it links the
miniSEED files on disk. To browse it, run `python3 -m http.server 8765` in `~/work/KSC_event_catalog`
and open `http://localhost:8765/site/`.

## 6. Add or update waveform data in the Zenodo archive

A published Zenodo record cannot change its files. Updates go into a **new version** of the record.
The concept DOI, which always resolves to the newest version, stays the same.

1. **Repackage** the years that changed (or all of them, with no `--year`):

   ```bash
   ksc package-waveforms --year 2016 --year 2026
   ```

   This writes `~/work/KSC_event_catalog/archive/ksc_event_waveforms_<YYYY>.zip` and rewrites
   `files_index.csv`. To check the zips:

   ```bash
   python3 -c "import zipfile,glob; [print(z, zipfile.ZipFile(z).testzip()) for z in sorted(glob.glob('$HOME/work/KSC_event_catalog/archive/*.zip'))]"
   ```

   `None` means the zip is OK.

2. **Open a new version:** on zenodo.org open the record, click **New version**, and in the draft
   delete the files you are replacing (the changed year zips and `files_index.csv`). The draft's number
   is in its URL: `https://zenodo.org/uploads/<ID>`.

3. **Upload into that draft:**

   ```bash
   export ZENODO_TOKEN=...       # your token; keep it out of git and out of shell history files
   ksc zenodo-upload --deposition <ID>
   ```

   Files already in the draft with the same size are skipped.

4. **On the web page:** update the version string (e.g. `0.3`) and the description, then **Publish**.
   The new version gets a new record number.

5. **Point the site at the new record:**

   ```bash
   ksc zenodo-links --record <NEW_RECORD_NUMBER>        # add --access open once the files are public
   git add data/curated/waveform_urls.csv && git commit -m "Zenodo record <n>"
   ksc build-site --web          # then push the site (section 5)
   ```

Zenodo limits: 50 GB and 100 files per record. That's why there is one zip per year; the current total
is 11 GB in 8 zips plus the index.

## 7. Create the Zenodo record (first time)

1. **Account:** sign in at https://zenodo.org with ORCID or GitHub.
2. **Token:** go to Account → Applications → Personal access tokens → New token, with scopes
   `deposit:write` and `deposit:actions`. Store it in your password manager, never in the repository.
3. **Metadata:** edit `data/curated/zenodo_metadata.json`. It currently has:
   * title, description, CC-BY-4.0, creator Thompson, Glenn (USF), version `0.2-provisional`;
   * `access_right: restricted`, with `access_conditions` (who may request access).

   Add co-authors (with ORCID ids), grants and keywords, and commit the file.
4. **Optional trial on the sandbox.** The sandbox needs its own account and token, at
   https://sandbox.zenodo.org.

   ```bash
   export ZENODO_TOKEN=<sandbox token>
   ksc zenodo-upload --sandbox
   ```

5. **Real upload.** This creates a draft and uploads the 8 year zips plus `files_index.csv`; with
   11 GB it takes a while. It never publishes.

   ```bash
   export ZENODO_TOKEN=<zenodo.org token>
   ksc zenodo-upload
   ```

6. **Review the draft** at the URL it prints: creators, description, license, resource type (Dataset),
   and **Access: restricted**. Then press **Publish**. That mints the DOI and can't be undone. The files
   can only change through new versions (section 6).
7. **Link the site:** run `ksc zenodo-links --record <record number>`, then `ksc build-site --web`,
   and push the site.

### Who can download (restricted access)

* The record page, DOI, description and file list are public; the files are not.
* A collaborator clicks **Request access** on the record page. You get an email and approve the request
  under the record's **Share** menu.
* You can also add people directly, or create a secret link: **Share → Links**. Anyone with the link
  can download, so send it privately.
* When the data may be public: on the record page, Edit → Access → Public → Publish. Then run
  `ksc zenodo-links --record <n> --access open`, then `ksc build-site --web`, and push.

Logging in to the GitHub site does not control Zenodo access. GitHub Pages sites are public.

---

## Branches (as of 2026-11-27)

Repository: `github.com/gthompson/KSCRocketSeismology`. On GitHub, `main` is 88 commits behind the
local `main` (last pushed 2026-11-23), and `shared-ksclib` is 18 behind.

| Branch | Contents |
|---|---|
| `main` | Everything below, merged. **Use this, or `shared-ksclib`.** |
| `shared-ksclib` | The integration branch for all sessions (catalog, ksclib, StationXML, papers). Same as `main`. Checked out in the main folder. |
| `claude/ksc-event-site` | Catalog processing, site, weather, publishing. Merged into `shared-ksclib`/`main` after each step. |
| `claude/ksc-web` | Site publishing and Zenodo work. Fully merged; can be deleted. |
| `claude/newglenn-paper-7faf3d` | New Glenn paper. Merged up to 0d8b91e; ongoing. |
| `claude/wizardly-faraday-01d6b3` | StationXML / SDS archive fixes. Merged up to b4c6161. |
| `origin/laptop-work` | One commit not in `main`: `b2533be Create main_v3_1.tex` (2026-11-21, from the laptop). |
| `origin/artemis2-paper-figures` | Fully contained in `main`. |

To push: `git push origin main shared-ksclib`. Nothing has been pushed by Claude.
