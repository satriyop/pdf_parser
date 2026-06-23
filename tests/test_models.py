from pdf_parser.models import SiteData


class TestSiteData:
    def test_csv_headers(self):
        headers = SiteData.csv_headers()
        assert headers == [
            "NO", "Area", "Nama Site", "Site ID", "Site Type",
            "ID Pelanggan PLN", "Daya PLN (kVA)", "Jumlah Phase",
            "Koordinat", "Daya Actual (W)", "Area Space(m2)",
        ]

    def test_to_csv_row(self):
        site = SiteData(
            no=1,
            area="TEST",
            nama_site="SITE_X",
            site_id="SID001",
            site_type="Outdoor",
            id_pelanggan_pln="PLN123",
            daya_pln_kva="20",
            jumlah_phase="3",
            koordinat="lat= -7.8\nlng= 114.1",
            daya_actual_w="2000",
            area_space_m2="5.0",
        )
        row = site.to_csv_row()
        assert row[0] == "1"
        assert row[1] == "TEST"
        assert row[2] == "SITE_X"
        assert row[8] == "lat= -7.8\nlng= 114.1"

    def test_to_csv_row_defaults(self):
        site = SiteData()
        row = site.to_csv_row()
        assert row == [str(0), "", "", "", "", "", "", "", "", "", ""]

    def test_to_xlsx_row_converts_types(self):
        site = SiteData(
            no=1,
            jumlah_phase="3",
            daya_actual_w="1500",
            area_space_m2="3,2",
        )
        row = site.to_xlsx_row()
        assert row[0] == 1
        assert row[7] == 3
        assert row[9] == 1500
        assert row[10] == 3.2

    def test_to_xlsx_row_bad_values(self):
        site = SiteData(
            jumlah_phase="Tiga",
            daya_actual_w="N/A",
            area_space_m2="unknown",
        )
        row = site.to_xlsx_row()
        assert row[7] == "Tiga"
        assert row[9] == "N/A"
        assert row[10] == "unknown"

    def test_coordinat_with_newline(self):
        site = SiteData(koordinat="lat= -7.8\nlng= 114.1")
        row = site.to_csv_row()
        assert "\n" in row[8]
