from flovopy.sds.merge_sds_archives_improved import merge_sds_archives

ROOT = "/Volumes/KSCGTdownld"
MASTER = f"{ROOT}/SDS"

source = f"{ROOT}/20260310_service/00_download/Centaur"

result = merge_sds_archives(
    "/Volumes/KSCGTdownld/20260310_service/00_download/Centaur",
    "/Volumes/KSCGTdownld/SDS",
    mode="fast",
    dry_run=False,
)

print(result)
