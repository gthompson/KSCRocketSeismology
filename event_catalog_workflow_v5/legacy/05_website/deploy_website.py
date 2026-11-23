# deploy website
import os
import shutil
import pandas as pd
thisdir = os.path.dirname(os.path.abspath(__file__))
srcdir = os.path.join(thisdir, 'website')
destdir= '/var/www/html/usfseismiclab.org/html/rocketcat'
#if os.path.isdir(destdir):
#    shutil.rmtree(destdir)
shutil.copytree(srcdir, destdir, dirs_exist_ok=True)


src_directory = '/shares/hal9000/share/data/KSC/EROSION/DropboxFolder/2022_DATA/EVENTS'

def copy_png_files_with_structure(src_dir, dest_dir):
    # Walk through the source directory
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            # Check if the file is a .png file
            if file.lower().endswith('.png'):
                # Compute the relative path of the file
                rel_path = os.path.relpath(root, src_dir)
                
                # Construct the destination directory by joining the destination base path with the relative path
                dest_dir_path = os.path.join(dest_dir, rel_path)
                
                # Ensure the destination directory exists
                if not os.path.exists(dest_dir_path):
                    os.makedirs(dest_dir_path)
                
                # Construct the source and destination file paths
                src_file = os.path.join(root, file)
                dest_file = os.path.join(dest_dir_path, file)
                
                # Copy the file to the destination directory
                shutil.copy2(src_file, dest_file)
                print(f"Copied {src_file} to {dest_file}")

#copy_png_files_with_structure(src_directory, os.path.join(destdir, 'EVENTS'))
csvsrc = os.path.join(src_directory, 'launchesDF.csv')
#csvsrc = '/shares/hal9000/share/data/KSC/EROSION/DropboxFolder/2022_DATA/PilotStudy_KSC_Rocket_Launches.csv'
csvtrg = os.path.join(destdir, 'launches.csv')
df = pd.read_csv(csvsrc, index_col=None, parse_dates=['datetime'])
df['year'] = [x.year for x in df['datetime']]
df[['rocket','mission']] = df['Rocket_Payload'].str.split('|',expand=True)
df = df[['datetime', 'SLC', 'rocket', 'mission', 'year']]
df.dropna(how='all', inplace=True)
df.to_csv(csvtrg, index=False)    

# Group by SLC
grouped_by_slc = df.groupby('SLC')
for slc, group_df in grouped_by_slc:
    group_df.to_csv(csvtrg.replace('.csv', f'_{slc}.csv'), index=False)

# Group by year
grouped_by_slc = df.groupby('year')
for year, group_df in grouped_by_slc:
    group_df.to_csv(csvtrg.replace('.csv', f'_{year}.csv'), index=False)

# Group by rocket
atlas = df[df['rocket'].str.contains('Atlas')]
delta = df[df['rocket'].str.contains('Delta')]
falcon = df[df['rocket'].str.contains('Falcon')]
atlas.to_csv(csvtrg.replace('.csv', '_atlas.csv'), index=False)
delta.to_csv(csvtrg.replace('.csv', '_delta.csv'), index=False)
falcon.to_csv(csvtrg.replace('.csv', '_falcon.csv'), index=False)

# those with well data 
dfwell = df[df['datetime'].between('2022-07-21', '2022-12-05')]
dfwell.to_csv(csvtrg.replace('.csv', '_well.csv'), index=False)

import os
import json
os.chdir(destdir)


# Get a list of CSV files in the current directory
csv_files = [f for f in os.listdir(destdir) if f.endswith('.csv')]

# Save the list to a JSON file
with open('csv_list.json', 'w') as json_file:
    json.dump(csv_files, json_file)

print(f"CSV files saved to csv_list.json: {csv_files}")
