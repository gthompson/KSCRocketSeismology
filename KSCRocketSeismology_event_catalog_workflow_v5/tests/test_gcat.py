from kscrockets.event_catalog import read_gcat_tsv_bytes, filter_gcat_ksc


def test_gcat_parser_and_filter_real_comment_header():
    data=(
        "#Launch_Tag\tLaunch_JD\tLaunch_Date\tLV_Type\tVariant\tFairing\tFlight_ID\tFlight\tMission\tFlightCode\tPlatform\tLaunch_Site\tLaunch_Pad\tAscent_Site\tAscent_Pad\tPerigee\tApogee\tApoflag\tInc\tAzimuth\tRange\tRangeFlag\tDest\tOrbMass\tOrbPay\tAgency\tLaunchCode\tFailCode\tGroup\tCategory\tLTCite\tCite\tNotes\n"
        "# Updated 2026 Sep 15 1940:00\n"
        "2016-001\t0\t2016 Jan 01 1234:56\tFalcon 9\tFT\t-\tX\t-\tDemo\t-\t-\tCC\tSLC-40\t-\t-\t-\t-\t\t-\t-\t-\t\t-\t0\t0\tSPX\tOS\tU\t-\tTest\t-\t-\t-\n"
    ).encode()
    df=read_gcat_tsv_bytes(data,"O")
    assert len(df)==1
    assert df.iloc[0].time_utc.startswith("2016-01-01T12:34:56")
    assert df.iloc[0].time_definition.endswith("first motion)")
    assert df.iloc[0].source_event_id == "2016-001"
    assert len(filter_gcat_ksc(df))==1


def test_gcat_filter_uses_site_not_pad_number():
    import pandas as pd
    df = pd.DataFrame([
        {"location": "CC", "pad": "SLC-40", "time_utc": "2020-01-01T00:00:00Z"},
        {"location": "KSC", "pad": "LC39A", "time_utc": "2020-01-02T00:00:00Z"},
        # A Cape-looking/potentially colliding pad at another GCAT site must not pass.
        {"location": "NIIP-5", "pad": "LC176/46", "time_utc": "2020-01-03T00:00:00Z"},
    ])
    out = filter_gcat_ksc(df)
    assert out["location"].tolist() == ["CC", "KSC"]
