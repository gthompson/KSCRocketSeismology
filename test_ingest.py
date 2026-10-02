from flovopy.sds.merge_sds_archives_improved import merge_sds_archives

ROOT = "/Volumes/KSCGTdownld"
MASTER = f"{ROOT}/SDS"

source = f"{ROOT}/20260107_huddle/00_download/Centaur"

result = merge_sds_archives(
    source,
    MASTER,
    mode="fast",
    dry_run=False,
)

print(result)
