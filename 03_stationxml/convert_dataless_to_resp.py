from obspy.io.xseed import Parser
import os

# Input Dataless SEED file
dataless_seed_path = "/data/KSC/EROSION/ispaq/KSC.dataless"

# Output directory for RESP files
resp_output_dir = "/data/KSC/EROSION/ispaq/RESP"
os.makedirs(resp_output_dir, exist_ok=True)

# Load the Dataless SEED file
print(f"[INFO] Reading Dataless SEED file: {dataless_seed_path}")
parser = Parser(dataless_seed_path)

# Write RESP files
print(f"[INFO] Writing RESP files to: {resp_output_dir}")
parser.write_resp(folder=resp_output_dir, zipped=False)

print("[SUCCESS] RESP file generation completed.")
