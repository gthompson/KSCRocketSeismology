from kscrockets.event_catalog import read_gcat_tsv_bytes, filter_gcat_ksc

def test_gcat_parser_and_filter():
    data=("Launch_Tag\tLaunch_JD\tLaunch_Date\tLV_Type\tLV_Variant\tFlight_ID\tFlight\tMission\tFlightCode\tPlatform\tLaunch_Site\tLaunch_Pad\tLaunchCode\tNotes\n"
          "2016-001\t0\t2016 Jan 01 12:34:56\tFalcon 9\tFT\tX\t\tDemo\t\t\tCC\tSLC-40\tOS\t\n").encode()
    df=read_gcat_tsv_bytes(data,"O")
    assert len(df)==1
    assert df.iloc[0].time_utc.startswith("2016-01-01T12:34:56")
    assert df.iloc[0].time_definition.endswith("first motion)")
    assert len(filter_gcat_ksc(df))==1
